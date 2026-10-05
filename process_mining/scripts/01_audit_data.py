"""Data audit for both datasets: what is really there before any modelling.

Writes outputs/data_audit.md and outputs/data_audit.json.
"""
import os
import re
from collections import Counter

from _common import A, B, CFG, OUT, load_events, md_table, sessions, write_json, write_text
from procmine.evaluate import gt_alignment_check, gt_executions
from procmine.io import load_gt, load_manifest, ts_ms

TERMINALS = ("WindowsTerminal", "powershell", "Windows PowerShell")


def dataset_rows(ds):
    rows = []
    for s in sessions(ds):
        evs = load_events(os.path.join(ds, s))
        lay = Counter(e.get("layer") for e in evs)
        ver = sorted({(e.get("source") or {}).get("agent_version") for e in evs} - {None})
        users = {(e.get("source") or {}).get("username_hash") for e in evs} - {None}
        apps = Counter(((e.get("context") or {}).get("active_app") or {}).get("app_name") for e in evs)
        leak = any(re.search(r"GT log|orchestrator_m\d|Schedule:", str((e.get("context") or {}).get("extracted_text")))
                   for e in evs if ((e.get("context") or {}).get("active_app") or {}).get("app_name") in TERMINALS)
        span = (evs[-1]["timestamp_ms"] - evs[0]["timestamp_ms"]) / 60000 if evs else 0
        rows.append({"session": s, "events": len(evs), "minutes": round(span, 1), "L3_events": lay.get("L3", 0),
                     "agent": ",".join(ver), "users": len(users), "top_apps": ", ".join(a for a, _ in apps.most_common(4) if a),
                     "harness_console_in_ocr": leak})
    return rows


def gt_audit():
    n_exec = n_null_end = back_to_back = inside_noise = outside_noise = 0
    themes = Counter()
    rows = []
    for s in sessions(A):
        sd = os.path.join(A, s)
        m = load_manifest(sd)
        themes[m.get("theme")] += 1
        man = [e for p in m["processes"] for e in p["executions"]]
        n_exec += len(man)
        n_null_end += sum(1 for e in man if e.get("end_ts") is None)
        g = [x for x in load_gt(sd) if x["event"] in ("process_started", "process_resumed")]
        back_to_back += sum(1 for a, b in zip(g, g[1:]) if a.get("process_code") == b.get("process_code"))
        ex = gt_executions(sd)
        for nb in m.get("noise_blocks") or []:
            t = ts_ms(nb["ts"])
            if any(e["start"] <= t < e["end"] for e in ex):
                inside_noise += 1
            else:
                outside_noise += 1
        evs = load_events(sd)
        last = max(e["timestamp_ms"] for e in evs)
        al = gt_alignment_check(sd, evs)
        beyond = sum(1 for e in ex if e["start"] > last)
        if (al is not None and al < 0.5) or beyond:
            rows.append({"session": s, "alignment": None if al is None else round(al, 2),
                         "gt_executions_after_recording_end": beyond})
    return {"themes": dict(themes), "manifest_executions": n_exec, "null_end_ts": n_null_end,
            "back_to_back_same_process_starts": back_to_back,
            "noise_blocks_inside_executions": inside_noise, "noise_blocks_between_executions": outside_noise,
            "suspicious_sessions": rows}


def main():
    ra, rb = dataset_rows(A), dataset_rows(B)
    ga = gt_audit()
    summ = {}
    for name, rows in (("A", ra), ("B", rb)):
        summ[name] = {"sessions": len(rows), "empty_sessions": sum(1 for r in rows if r["events"] == 0),
                      "events": sum(r["events"] for r in rows), "recorded_minutes": round(sum(r["minutes"] for r in rows), 1),
                      "sessions_without_browser_extension": sum(1 for r in rows if r["L3_events"] == 0),
                      "sessions_with_harness_console_in_ocr": sum(1 for r in rows if r["harness_console_in_ocr"])}
    write_json("data_audit.json", {"summary": summ, "gt_A": ga, "sessions_A": ra, "sessions_B": rb})
    cols = ["session", "events", "minutes", "L3_events", "agent", "users", "top_apps", "harness_console_in_ocr"]
    text = ["# Data audit\n",
            "## Summary\n", md_table([{"dataset": k, **v} for k, v in summ.items()],
                                      ["dataset", "sessions", "empty_sessions", "events", "recorded_minutes",
                                       "sessions_without_browser_extension", "sessions_with_harness_console_in_ocr"]),
            "\n## Ground truth (A)\n",
            f"- themes: {ga['themes']}\n",
            f"- manifest executions: {ga['manifest_executions']}; with null end_ts: {ga['null_end_ts']}\n",
            f"- process_started/resumed immediately followed by another start of the SAME process: "
            f"{ga['back_to_back_same_process_starts']} -> the null end_ts rows are back-to-back cases, their end is the "
            f"next start (recovered, not dropped)\n",
            f"- injected noise blocks inside an execution: {ga['noise_blocks_inside_executions']}, between executions: "
            f"{ga['noise_blocks_between_executions']}\n",
            "\nSessions whose GT cannot be scored as-is:\n\n",
            md_table(ga["suspicious_sessions"], ["session", "alignment", "gt_executions_after_recording_end"]) if ga["suspicious_sessions"] else "none\n",
            "\n## Sessions A\n", md_table(ra, cols), "\n## Sessions B\n", md_table(rb, cols)]
    write_text("data_audit.md", "".join(text))
    print("".join(text[:9]))


if __name__ == "__main__":
    main()
