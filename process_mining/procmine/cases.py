"""Assemble cases (one business case = one execution) from click evidence with a small state machine.

    idle/committed --row--> open --note--> noted --commit--> committed
    open/noted --row of another object--> open (new case; the previous one had no commit)

L2-only sessions need to know which UI-Automation control type the portal's row and commit clicks
resolve to.  That differs between deployments (A: commit = 'main' group; B: commit hit-tests onto the
last table row, a DataItem), so it is *learned* from sessions where L3 and L2 both saw the same click.
"""
import bisect
from collections import Counter


def learn_l2_profile(evidences):
    twin = {"row": Counter(), "commit": Counter(), "note": Counter()}
    for evd in evidences:
        l2 = [x for x in evd if x["kind"] == "click" and x.get("layer") == "L2" and x.get("dup")]
        l3 = [x for x in evd if x["kind"] == "click" and x.get("layer") == "L3"]
        lt = [x["t"] for x in l3]
        for x in l2:
            i = bisect.bisect_left(lt, x["t"] - 400)
            if i < len(lt) and abs(lt[i] - x["t"]) <= 400 and l3[i]["ctype"] in twin:
                twin[l3[i]["ctype"]][x["ctype"]] += 1
    prof = {k: (v.most_common(1)[0][0] if v else None) for k, v in twin.items()}
    prof.setdefault("row", "cell")
    if prof["row"] is None:
        prof["row"] = "cell"
    if prof["commit"] is None:
        prof["commit"] = "button"
    return prof


def _obj_key(x):
    return (x.get("port"), x.get("route"), x.get("case_id"), x.get("row"), x.get("name") if x.get("layer") == "L2" else None)


def assemble(evd, prof, cfg, tempo=1.0):
    reopen = cfg["reopen_window_ms"]
    nav_max = cfg["lags_ms"]["nav_max_before_open"] * tempo
    nav_ev = [x for x in evd if x["kind"] == "nav" and x.get("nav_type") == "spa_popstate"
              and x.get("route") not in set(cfg["non_process_routes"])]
    navs = [x["t"] for x in nav_ev]
    clicks = [x for x in evd if x["kind"] == "click" and not x.get("dup")]
    cases, cur, state = [], None, "idle"

    def new_case(x):
        c = {"open_t": x["t"], "last_open_t": x["t"], "opens": [x], "note_t": None, "notes": [], "commit_t": [],
             "src": x.get("layer")}
        cases.append(c)
        return c

    for x in clicks:
        ct = x["ctype"]
        if x.get("layer") == "L2":
            if ct == prof["commit"] and state == "noted":
                ct = "commit"
            elif ct == prof["row"]:
                ct = "row"
            elif ct == "note":
                ct = "note"
            elif ct == prof["commit"]:
                ct = "commit"
            else:
                continue
        elif ct == "other" and x.get("css") == "#main" and state in ("idle", "committed"):
            # extension resolved a row click on a still-loading list as the page container
            i = bisect.bisect_right(navs, x["t"]) - 1
            if i >= 0 and x["t"] - navs[i] <= nav_max:
                ct = "row"
                x = {**x, "port": nav_ev[i].get("port"), "route": nav_ev[i].get("route"), "main_fallback": True}
        if ct == "row":
            if cur is not None and state in ("open", "noted") and _obj_key(x) == _obj_key(cur["opens"][-1]) \
                    and x["t"] - cur["last_open_t"] < reopen:
                cur["last_open_t"] = x["t"]; cur["opens"].append(x)
                continue
            cur = new_case(x); state = "open"
        elif ct == "note" and cur is not None:
            cur["note_t"] = cur["note_t"] or x["t"]
            cur["notes"].append(x["t"])
            cur.setdefault("note_pfx", x.get("pfx"))
            state = "noted"
        elif ct == "commit" and cur is not None:
            cur["commit_t"].append(x["t"])
            if x.get("pfx"):
                cur.setdefault("commit_pfx", x.get("pfx"))
            state = "committed"
    return split_missed_opens(cases)


def split_missed_opens(cases):
    """A note typed after the case was already committed means the next case's row click was not recorded:
    split there, back-dating the new open by the dataset's median row-click -> note interval."""
    gaps = sorted(c["notes"][0] - c["open_t"] for c in cases if c["notes"] and c["commit_t"] and c["notes"][0] < c["commit_t"][0])
    if not gaps:
        return cases
    med = gaps[len(gaps) // 2]
    out = []
    for c in cases:
        while c["commit_t"] and any(n > c["commit_t"][0] for n in c["notes"]):
            n2 = min(n for n in c["notes"] if n > c["commit_t"][0])
            first = {**c, "notes": [n for n in c["notes"] if n < n2], "commit_t": [t for t in c["commit_t"] if t < n2]}
            open_t = max(n2 - med, first["commit_t"][-1] + 200)
            o = c["opens"][0] if c["opens"] else {}
            rest = {**c, "open_t": open_t, "last_open_t": open_t, "opens": [], "note_t": n2, "src": "split",
                    "notes": [n for n in c["notes"] if n >= n2], "commit_t": [t for t in c["commit_t"] if t >= n2],
                    "port": o.get("port") or c.get("port"), "route": o.get("route") or c.get("route")}
            out.append(first)
            c = rest
        out.append(c)
    return out


def add_nav_fallback(cases, evd, cfg, tempo=1.0, quiet_ms=30000):
    """Degraded telemetry (mouse hook / extension died mid-session): portal navigations still arrive.
    Only inside such telemetry gaps (no click of any layer within ±quiet_ms), a navigation to a process
    screen that is not followed by an opened case becomes a synthetic case."""
    lags = cfg["lags_ms"]
    navs = [x for x in evd if x["kind"] == "nav" and x.get("nav_type") == "spa_popstate"
            and x.get("route") not in set(cfg["non_process_routes"])]
    clicks = sorted(x["t"] for x in evd if x["kind"] == "click")
    opens = sorted(c["open_t"] for c in cases)
    extra = []
    for k, n in enumerate(navs):
        j = bisect.bisect_left(clicks, n["t"] - quiet_ms)
        if j < len(clicks) and clicks[j] <= n["t"] + quiet_ms:
            continue                     # telemetry healthy around this navigation
        nxt = navs[k + 1]["t"] if k + 1 < len(navs) else float("inf")
        i = bisect.bisect_left(opens, n["t"])
        if i < len(opens) and opens[i] < nxt:
            continue
        est_open = n["t"] + (lags["open_change"] - lags["nav"]) * tempo
        extra.append({"open_t": est_open, "last_open_t": est_open, "opens": [], "note_t": None, "commit_t": [],
                      "src": "nav", "nav_t": n["t"], "port": n.get("port"), "route": n.get("route")})
    return sorted(cases + extra, key=lambda c: c["open_t"])


def merge_same_case(cases):
    """The same case number opened again right after itself is still one case (re-click after commit)."""
    out = []
    for c in cases:
        if out and c.get("case_ids") and out[-1].get("case_ids") and c["case_ids"][0] == out[-1]["case_ids"][0]:
            p = out[-1]
            p["opens"] += c["opens"]; p["commit_t"] += c["commit_t"]; p["last_open_t"] = c["last_open_t"]
            p["note_t"] = p["note_t"] or c["note_t"]
            continue
        out.append(c)
    return out
