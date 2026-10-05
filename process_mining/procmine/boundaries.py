"""Place segment boundaries around assembled cases.

Lags between a ground-truth boundary and the first observable action were measured on dataset A
(scripts/02_calibrate_a.py).  B runs a faster harness, so the lags are scaled by the dataset's own tempo,
measured without ground truth as median(navigation -> first row click) relative to A.

Rules (all validated on A):
  start  = last portal navigation shortly before the row click - lag_nav      (a new screen was opened)
         = row click - lag_open                                              (screen was already open)
  end    = next case's start (idle/noise between cases stays with the preceding case)
  final  = first dashboard navigation after the last commit + lag_final       (harness wrap-up)
"""
import bisect
import statistics


def tempo_ratio(evds, cfg):
    """Median navigation->row-open interval of this dataset relative to the A reference."""
    gaps = []
    for evd in evds:
        navs = [x["t"] for x in evd if x["kind"] == "nav" and x.get("nav_type") == "spa_popstate"]
        opens = [x["t"] for x in evd if x["kind"] == "click" and x.get("ctype") == "row" and x.get("layer") == "L3"]
        for o in opens:
            i = bisect.bisect_left(navs, o) - 1
            if i >= 0 and 0 < o - navs[i] < 10000:
                gaps.append(o - navs[i])
    if len(gaps) < 20:
        return 1.0
    return statistics.median(gaps) / cfg["tempo_reference_nav_to_open_ms"]


def _last_productive(c, nxt_open, edits, chain):
    """Commit (or open) plus any keyboard/clipboard wrap-up chained right after it (B logs results to a memo
    after committing).  Chain breaks on a pause longer than `chain` or at the next case."""
    last = max([c["open_t"], c.get("note_t") or 0] + c["commit_t"])
    if not c["commit_t"]:
        return last
    i = bisect.bisect_right(edits, last)
    while i < len(edits) and edits[i] < nxt_open and edits[i] - last <= chain:
        last = edits[i]
        i += 1
    return last


def place(cases, evd, cfg, tempo=1.0, gap_cut_ms=None, rx=None):
    L = {k: v * tempo for k, v in cfg["lags_ms"].items() if not k.startswith("_")}
    gap_cut = cfg["gap_cut_ms"] if gap_cut_ms is None else gap_cut_ms
    min_gap = cfg["min_gap_ms"]
    npr = set(cfg["non_process_routes"])
    navs = [x["t"] for x in evd if x["kind"] == "nav" and x.get("nav_type") == "spa_popstate" and x.get("route") not in npr]
    root_navs = [x["t"] for x in evd if x["kind"] == "nav" and x.get("route") in npr]
    edits = [x["t"] for x in evd if x["kind"] == "edit" and not (rx and rx.is_browser(x.get("app")))]
    chain = 4000 * tempo
    n = len(cases)
    opens = [c["open_t"] for c in cases]
    last = [_last_productive(c, opens[i + 1] if i + 1 < n else float("inf"), edits, chain) for i, c in enumerate(cases)]
    for i, c in enumerate(cases):
        prev_last = last[i - 1] if i else float("-inf")
        if c.get("src") == "nav":
            st = c["nav_t"] - L["nav"]
        else:
            # first navigation after the previous case that is close enough to this row click to belong to it
            j = bisect.bisect_right(navs, prev_last)
            nav_t = None
            while j < len(navs) and navs[j] <= c["open_t"]:
                if c["open_t"] - navs[j] <= L["nav_max_before_open"]:
                    nav_t = navs[j]
                    break
                j += 1
            if nav_t is not None:
                st = nav_t - L["nav"]
            else:               # screen already showing (portals live in separate windows): lag by case type
                same = i > 0 and cases[i - 1].get("type") == c.get("type")
                st = c["open_t"] - (L["open_same"] if same else L["open_change"])
        st = max(st, prev_last + min_gap)
        c["start"] = min(st, c["open_t"] - 50) if c.get("src") != "nav" else st
    for i, c in enumerate(cases):
        if i + 1 < n:
            nxt = cases[i + 1]["start"]
            c["end"] = last[i] + L["tail"] if nxt - last[i] > gap_cut else nxt
            c["end"] = min(c["end"], nxt)
        else:
            k = bisect.bisect_right(root_navs, last[i])
            if k < len(root_navs) and root_navs[k] - last[i] < 60000:
                c["end"] = root_navs[k] + L["final_after_dashboard_nav"]
            else:
                c["end"] = last[i] + L["final_after_last_commit"]
        c["last_productive"] = last[i]
        c["end"] = max(c["end"], c["start"] + 1000)
    return cases
