"""DISCLOSED CROSS-CHECK — not an input to segmentation.

Dataset B's screen text (context.extracted_text) contains the test harness console for a few sessions:
run ID, schedule and the ordered task IDs.  That is effectively partial ground truth leaking through the
recording (and a governance finding: the agent captures terminal contents verbatim).  segments.jsonl is
produced without it; this script only compares our case sequence with the console for sessions where a
complete run is visible.  Writes outputs/crosscheck_b_console.md.
"""
import difflib
import os
import re
from datetime import datetime, timedelta

from _common import B, CFG, load_events, sessions, write_text
from procmine import pipeline as PL

RUN = re.compile(r"Run ID\s*:\s*theme_m2_(\d{8})_(\d{6})")
TASK = re.compile(r"task (P\d+)-\d{8}-\d{3}")
LOCAL_OFFSET = timedelta(hours=5, minutes=30)   # console clock (IST) vs UTC session names


def console_runs():
    runs = {}
    for s in sessions(B):
        for e in load_events(os.path.join(B, s)):
            app = ((e.get("context") or {}).get("active_app") or {}).get("app_name")
            et = e.get("context", {}).get("extracted_text")
            if app != "WindowsTerminal" or not et:
                continue
            text = et.get("text") if isinstance(et, dict) else str(et)
            parts = re.split(r"(?=Theme M2 Orchestrator)", text)
            for p in parts:
                m = RUN.search(p)
                if not m:
                    continue
                complete = "Session complete" in p or "Theme M2 done" in p
                tasks = TASK.findall(p.split("Session complete")[0])
                key = m.group(1) + m.group(2)
                if complete and len(tasks) > len(runs.get(key, [])):
                    runs[key] = tasks
    return runs


def main():
    runs = console_runs()
    cb, _, _ = PL.segment_dataset(B, CFG)
    lines = ["# Cross-check of B segmentation against the harness console visible in B's own screen text\n\n",
             "Validation only (see module docstring). Complete runs found: %d\n\n" % len(runs),
             "| session | console tasks | our cases | same type, aligned |\n|---|---|---|---|\n"]
    tot = [0, 0, 0]
    for key, tasks in sorted(runs.items()):
        local = datetime.strptime(key, "%Y%m%d%H%M%S")
        utc = local - LOCAL_OFFSET
        match = [s for s in cb if abs((datetime.strptime(s[4:19], "%Y%m%d-%H%M%S") - utc).total_seconds()) < 120]
        if not match:
            continue
        s = match[0]
        pred = [c["type"] for c in cb[s]]
        sm = difflib.SequenceMatcher(a=tasks, b=pred, autojunk=False)
        eq = sum(b.size for b in sm.get_matching_blocks())
        tot[0] += len(tasks); tot[1] += len(pred); tot[2] += eq
        lines.append(f"| {s} | {len(tasks)} | {len(pred)} | {eq} |\n")
    if tot[0]:
        lines.append(f"\nTotal: {tot[2]}/{tot[0]} console tasks matched (recall {tot[2] / tot[0]:.3f}), "
                     f"{tot[2]}/{tot[1]} predicted cases matched (precision {tot[2] / tot[1]:.3f}).\n")
    write_text("crosscheck_b_console.md", "".join(lines))
    print("".join(lines))


if __name__ == "__main__":
    main()
