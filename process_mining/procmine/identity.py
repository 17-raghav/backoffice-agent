"""Case identity = business case type.

Primary key: the prefix of the portal's case number (INV-…, EXP-…, P1-…, P4-…).  Evidence, strongest first:
  1. the case number itself: DOM row id (A), keyboard focus on a row element (A without extension),
     or the confirmation toast "<case no>: 登録確定しました" (B)
  2. the portal table as captured on screen: rows are listed in order, so row k -> k-th case number (B)
  3. the text of the clicked cell (UI-Automation name), looked up in captured table rows (B without extension)
  4. the screen slot (system, route) -> dominant prefix seen on that slot
Everything is learned from the same dataset; nothing is hard-coded per dataset.
"""
import re
from collections import Counter, defaultdict

from .evidence import Rx


def _maj(counter, min_share=0.0):
    if not counter:
        return None, 0.0
    k, v = counter.most_common(1)[0]
    share = v / sum(counter.values())
    return (k, share) if share >= min_share else (None, share)


def parse_table(text, rx):
    """Ordered rows [(case_id, prefix, row_text)] from a captured portal list, or None."""
    ids = list(rx.case_id.finditer(text))
    rows = []
    for i, m in enumerate(ids):
        end = ids[i + 1].start() if i + 1 < len(ids) else len(text)
        chunk = text[m.end():end]
        if chunk.lstrip().startswith(":"):      # confirmation toast, not a row
            continue
        rows.append((m.group(0), m.group("prefix"), chunk))
    seen, uniq = set(), []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0]); uniq.append(r)
    return uniq if len(uniq) >= 3 else None


class Catalog:
    """What each screen/row/cell of the portal means, learned from one dataset."""

    def __init__(self, cfg):
        self.rx = Rx(cfg)
        self.row_votes = defaultdict(Counter)     # (port, route, k) -> prefix
        self.slot_votes = defaultdict(Counter)    # (port, route) -> prefix
        self.pslot_votes = defaultdict(Counter)   # (port, dom prefix) -> prefix
        self.chunks = defaultdict(list)           # port -> [(row text, prefix)]
        self.system_port = defaultdict(Counter)   # window-title system -> port
        self.pfx_route = defaultdict(Counter)     # dom prefix ('pi') -> route ('payroll-items')
        self.page_names = defaultdict(Counter)    # (port, route) -> on-screen page name

    # ---------------------------------------------------------------- learning
    def learn(self, evd, cases):
        rx = self.rx
        for k, c in enumerate(cases):
            o = c["opens"][0] if c["opens"] else None
            if o is None or o.get("layer") != "L3":
                continue
            port, route, pfx = o.get("port"), o.get("route"), o.get("pfx")
            if o.get("system") and port:
                self.system_port[o["system"]][port] += 1
            if pfx and route:
                self.pfx_route[pfx][route] += 1
            if o.get("case_id"):
                m = rx.case_id.match(o["case_id"])
                if m:
                    self.slot_votes[(port, route)][m.group("prefix")] += 3
                    self.pslot_votes[(port, pfx)][m.group("prefix")] += 3
            hi = cases[k + 1]["open_t"] if k + 1 < len(cases) else c["open_t"] + 120000
            for x in evd:
                if x["kind"] != "ocr" or not (c["open_t"] <= x["t"] < hi) or not rx.is_browser(x.get("app")):
                    continue
                rows = parse_table(x["text"], rx)
                m = re.search(r"ダッシュボード\s*/\s*(\S+)", x["text"])
                if m and route not in (None, "", "dashboard"):
                    self.page_names[(port, route)][m.group(1)] += 1
                if not rows:
                    continue
                for i, (cid, p, chunk) in enumerate(rows, start=1):
                    self.row_votes[(port, route, i)][p] += 1
                    self.slot_votes[(port, route)][p] += 1
                    self.pslot_votes[(port, pfx)][p] += 1
                    self.chunks[port].append((chunk, p))

    def finalize(self):
        self.pfx_route_map = {k: _maj(v)[0] for k, v in self.pfx_route.items()}
        self.system_port_map = {k: _maj(v)[0] for k, v in self.system_port.items()}

    # ---------------------------------------------------------------- resolving
    def slot_of(self, c):
        o = c["opens"][0] if c["opens"] else {}
        port = o.get("port") or c.get("port")
        if o.get("layer") == "L2" or not port:
            port = self.system_port_map.get(o.get("system")) or port
        route = o.get("route") if o.get("layer") == "L3" else None
        dom = o.get("pfx") or c.get("note_pfx") or c.get("commit_pfx")
        if not route:
            route = self.pfx_route_map.get(dom) or c.get("route") or o.get("route")
        return port, route, dom

    def resolve(self, c, evd_idx=None):
        rx = self.rx
        port, route, dom = self.slot_of(c)
        c["slot"] = (port, route)
        slot_prefixes = self.slot_votes.get((port, route), Counter())
        # 1. case number seen on the element itself (DOM row id / keyboard focus)
        if not c.get("toast"):
            for cid in c.get("case_ids", []):
                m = rx.case_id.match(cid)
                if m:
                    return m.group("prefix"), "case_id"
        o = c["opens"][0] if c["opens"] else {}
        # 2. row index on a captured table
        if o.get("row") and port and route:
            p, share = _maj(self.row_votes.get((port, route, o["row"]), Counter()), 0.6)
            if p:
                return p, "table_row"
        # 2b. confirmation toast, only if that case type is known to live on this screen
        if c.get("toast"):
            m = rx.case_id.match(c["case_ids"][0])
            if m and (not slot_prefixes or slot_prefixes[m.group("prefix")] / sum(slot_prefixes.values()) >= 0.1):
                return m.group("prefix"), "toast"
        # 3. clicked cell text looked up in captured rows (same system)
        name = o.get("name")
        if name and port and len(name) >= 2 and not rx.case_id.fullmatch(name):
            votes = Counter(p for chunk, p in self.chunks.get(port, []) if name in chunk)
            p, share = _maj(votes, 0.7)
            if p:
                return p, "cell_text"
        # 4. slot
        p, share = _maj(self.slot_votes.get((port, route), Counter()), 0.5)
        if p:
            return p, "slot"
        p, share = _maj(self.pslot_votes.get((port, dom), Counter()), 0.5)
        if p:
            return p, "slot_dom"
        return f"{port}|{route or dom}", "unresolved"


def attach_case_ids(cases, evd, rx):
    """Case numbers observed inside each case window: DOM row id, keyboard focus on a row, toast after commit."""
    for k, c in enumerate(cases):
        hi = cases[k + 1]["open_t"] if k + 1 < len(cases) else float("inf")
        ids = []
        for o in c["opens"]:
            if o.get("case_id"):
                ids.append(o["case_id"])
        for x in evd:
            if x["t"] < c["open_t"]:
                continue
            if x["t"] >= hi:
                break
            if x["kind"] == "rowfocus" and x.get("case_id"):
                ids.append(x["case_id"])
        c["case_ids"] = ids
    # toasts: first unused toast after a case's commit and before the next case's commit
    toasts = [x for x in evd if x["kind"] == "toast"]
    used = set()
    for k, c in enumerate(cases):
        if not c["commit_t"] or c["case_ids"]:
            continue
        lo = c["commit_t"][0]
        nxt = next((cc["commit_t"][0] for cc in cases[k + 1:] if cc["commit_t"]), lo + 60000)
        for x in toasts:
            if lo <= x["t"] < nxt and x["case_id"] not in used:
                used.add(x["case_id"]); c["case_ids"] = [x["case_id"]]; c["toast"] = True
                break
