"""Measure, on dataset A, how ground-truth boundaries sit relative to observable actions.

These medians become cfg["lags_ms"].  They are properties of how the recording relates to the work
(e.g. the harness logs a case start ~1.6 s before the portal navigation), not of any process.
Writes outputs/calibration_a.json.
"""
import bisect
import os
import statistics

from _common import A, CFG, load_events, sessions, write_json
from procmine import evidence as EV
from procmine.evaluate import gt_alignment_check, gt_executions
from procmine.io import load_gt, ts_ms


def q(xs):
    xs = sorted(xs)
    if not xs:
        return {}
    f = lambda p: round(xs[min(len(xs) - 1, int(p * (len(xs) - 1)))])
    return {"p10": f(.1), "p25": f(.25), "median": f(.5), "p75": f(.75), "p90": f(.9), "n": len(xs)}


def main():
    npr = set(CFG["non_process_routes"])
    m = {k: [] for k in ("nav", "open_same", "open_change", "tail", "final_after_dashboard_nav",
                         "final_after_last_commit", "nav_to_open")}
    for s in sessions(A):
        sd = os.path.join(A, s)
        evs = load_events(sd)
        if gt_alignment_check(sd, evs) is not None and gt_alignment_check(sd, evs) < 0.5:
            continue
        evd = EV.build(evs, CFG)
        navs = [x["t"] for x in evd if x["kind"] == "nav" and x.get("nav_type") == "spa_popstate" and x.get("route") not in npr]
        roots = [x["t"] for x in evd if x["kind"] == "nav" and x.get("route") in npr]
        opens = [x["t"] for x in evd if x["kind"] == "click" and x["ctype"] == "row" and x["layer"] == "L3"]
        commits = [x["t"] for x in evd if x["kind"] == "click" and x["ctype"] == "commit" and x["layer"] == "L3"]
        if not opens:
            continue
        gt = gt_executions(sd)
        for i, g in enumerate(gt):
            j = bisect.bisect_left(opens, g["start"])
            if j >= len(opens) or opens[j] >= g["end"]:
                continue
            k = bisect.bisect_left(navs, g["start"])
            nav_in = k < len(navs) and navs[k] <= opens[j]
            same = i > 0 and gt[i - 1]["code"] == g["code"] and abs(gt[i - 1]["end"] - g["start"]) < 50
            if nav_in:
                m["nav"].append(navs[k] - g["start"])
                m["nav_to_open"].append(opens[j] - navs[k])
            elif same:
                m["open_same"].append(opens[j] - g["start"])
            else:
                m["open_change"].append(opens[j] - g["start"])
            c = bisect.bisect_right(commits, g["end"]) - 1
            if c >= 0 and commits[c] >= g["start"] and i + 1 < len(gt) and abs(gt[i + 1]["start"] - g["end"]) < 50:
                m["tail"].append(g["end"] - commits[c])
        ended = [ts_ms(x["ts_utc"]) for x in load_gt(sd) if x["event"] == "session_ended"]
        if ended and commits and ended[0] <= evs[-1]["timestamp_ms"]:
            lc = max([c for c in commits if c < ended[0]] or [0])
            if lc:
                m["final_after_last_commit"].append(ended[0] - lc)
                r = bisect.bisect_right(roots, lc)
                if r < len(roots) and roots[r] < ended[0]:
                    m["final_after_dashboard_nav"].append(ended[0] - roots[r])
    res = {k: q(v) for k, v in m.items()}
    res["config_in_use"] = CFG["lags_ms"]
    write_json("calibration_a.json", res)
    for k, v in res.items():
        print(f"{k:28} {v}")


if __name__ == "__main__":
    main()
