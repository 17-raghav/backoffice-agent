"""Raw events -> compact, typed evidence stream.

The desktop agent records two overlapping views of a click:
  * L3 browser_click (extension): DOM css selector, e.g. `#pi-row-EXP-181750-001 > td` or `#btn-pi-ok`
  * L2 mouse_click (UI Automation): control type + automation id + accessible name
L3 is preferred; L2 is kept as a fallback because the extension is missing or dies in some sessions
(8 A sessions and 1 B session have no L3 at all).  A duplicate L2 click only contributes its accessible name.
"""
import bisect
import re

from .io import text_of


class Rx:
    def __init__(self, cfg):
        d = cfg["dom"]
        self.row_css = re.compile(d["row_css"])
        self.commit_css = re.compile(d["commit_css"])
        self.note_id = re.compile(d["note_id"])
        self.row_focus = re.compile(d["row_focus_id"])
        self.case_id = re.compile(cfg["case_id_regex"])
        self.toast = re.compile(cfg["toast_regex"])
        self.url = re.compile(cfg["portal_url_regex"])
        self.browsers = [b.lower() for b in cfg["browser_apps"]]
        self.edit_types = set(cfg["edit_event_types"])
        self.non_process_routes = set(cfg["non_process_routes"])

    def is_browser(self, app):
        a = str(app or "").lower()
        return any(b in a for b in self.browsers)

    def parse_url(self, u):
        if not u:
            return None, None
        m = self.url.match(u)
        if not m:
            return None, None
        route = m.group("route")
        if route is None:          # hash-less URL (old agent): route unknown
            path = (m.group("path") or "").strip("/")
            route = path if path else None
        return m.group("port"), route


def system_name(title):
    """'財務会計システム - Google Chrome' / 'HR人事給与システム and 1 more page - ...' -> '財務会計システム'."""
    if not title:
        return None
    t = re.split(r" and \d+ more page| - ", title)[0].strip()
    return t or None


def build(evs, cfg):
    rx = Rx(cfg)
    dup_win = cfg["l2_dup_window_ms"]
    l3_click_t = [e["timestamp_ms"] for e in evs if e["event_type"] == "browser_click"]
    out = []
    port = route = None
    app = title = None
    for e in evs:
        t, et = e["timestamp_ms"], e["event_type"]
        c = e.get("context") or {}
        p = e.get("payload") or {}
        aa = c.get("active_app") or {}
        app = aa.get("app_name") or aa.get("process_name") or app
        title = aa.get("window_title") or title
        # portal location: explicit event url first, then the active tab
        for u in ((p.get("url") if et in ("browser_navigation", "browser_click", "browser_form_input") else None),
                  (c.get("active_browser_tab") or {}).get("url")):
            pp, rr = rx.parse_url(u)
            if pp:
                port = pp
                if rr is not None:
                    route = rr
                break
        base = {"t": t, "app": app, "port": port, "route": route, "title": title,
                "system": system_name(title) if rx.is_browser(app) else None}
        ocr = c.get("extracted_text")
        if ocr:
            txt = text_of(ocr)
            out.append({**base, "kind": "ocr", "text": txt, "src": ocr.get("source") if isinstance(ocr, dict) else None})
            for m in rx.toast.finditer(txt):
                out.append({**base, "kind": "toast", "case_id": m.group("id"), "msg": m.group("msg")})
        if et == "browser_navigation":
            pp, rr = rx.parse_url(p.get("url"))
            out.append({**base, "kind": "nav", "port": pp, "route": rr, "nav_type": p.get("navigation_type")})
        elif et == "browser_click":
            el = p.get("element") or {}
            css = el.get("css_selector") or ""
            aid = (el.get("attributes") or {}).get("id") or ""
            m, b, n = rx.row_css.search(css), rx.commit_css.search(css), rx.note_id.match(aid)
            if m:
                out.append({**base, "kind": "click", "ctype": "row", "layer": "L3",
                            "pfx": m.group("pfx") or m.group("pfx2"), "case_id": m.group("case_id"),
                            "row": int(m.group("row")) if m.group("row") else None})
            elif b:
                out.append({**base, "kind": "click", "ctype": "commit", "layer": "L3", "pfx": b.group("pfx"), "action": b.group("action")})
            elif n or css.endswith("-note"):
                out.append({**base, "kind": "click", "ctype": "note", "layer": "L3", "pfx": (aid or css.lstrip("#"))[:2]})
            else:
                out.append({**base, "kind": "click", "ctype": "other", "layer": "L3", "css": css})
        elif et == "mouse_click":
            te = p.get("target_element") or {}
            i = bisect.bisect_left(l3_click_t, t - dup_win)
            dup = i < len(l3_click_t) and abs(l3_click_t[i] - t) <= dup_win
            ctl, aid, name = te.get("control_type"), te.get("automation_id") or "", te.get("name")
            if rx.is_browser(app):
                n = rx.note_id.match(aid)
                if ctl == "DataItem":
                    ct = "cell"
                elif n:
                    ct = "note"
                elif aid == "main" or ctl == "Button":
                    ct = "button"
                else:
                    ct = "other"
                out.append({**base, "kind": "click", "ctype": ct, "layer": "L2", "dup": dup, "name": name,
                            "pfx": n.group("pfx") if n else None})
            else:
                out.append({**base, "kind": "click", "ctype": "desktop", "layer": "L2", "dup": dup, "name": name})
        elif et == "app_switch":
            na = p.get("new_app")
            na = na.get("app_name") if isinstance(na, dict) else na
            out.append({**base, "kind": "focus", "new": na})
        elif et in rx.edit_types:
            tf = p.get("target_field") or {}
            aid = (tf.get("automation_id") or "") if isinstance(tf, dict) else ""
            m = rx.row_focus.match(aid) if aid else None
            if m:
                out.append({**base, "kind": "rowfocus", "pfx": m.group("pfx"), "case_id": m.group("case_id")})
            out.append({**base, "kind": "edit", "et": et, "key": p.get("key"), "keys": p.get("keys")})
        elif et in ("mouse_scroll",):
            out.append({**base, "kind": "scroll"})
    # attach the accessible name of a duplicate L2 click to its L3 twin
    l3 = [x for x in out if x["kind"] == "click" and x.get("layer") == "L3"]
    lt = [x["t"] for x in l3]
    for x in out:
        if x["kind"] == "click" and x.get("layer") == "L2" and x.get("dup") and x.get("name"):
            i = bisect.bisect_left(lt, x["t"] - dup_win)
            if i < len(lt) and abs(lt[i] - x["t"]) <= dup_win:
                l3[i].setdefault("name", x["name"])
    return out
