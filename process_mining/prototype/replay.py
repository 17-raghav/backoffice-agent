"""Replay real dataset-B cases through the assistant and compare with what the worker actually submitted.

Metrics per process: parse rate of the list row, exact match of the drafted note vs the submitted note,
and (P6) decision agreement.  Also lists P6 cases where the practised rule and the written procedure disagree.
Writes ../outputs/prototype_replay.md and .json
"""
import json
import os
import re
from collections import Counter, defaultdict

from assistant import Assistant

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "outputs"))


def norm(s):
    return re.sub(r"\s+", "", s or "")


def main():
    a = Assistant()
    cases = [json.loads(l) for l in open(os.path.join(HERE, "data", "b_cases.jsonl"), encoding="utf-8")]
    stats = defaultdict(Counter)
    conflicts, misses = [], []
    for c in cases:
        t = c["type"]
        if not a.supports(t):
            stats[t]["unsupported"] += 1
            continue
        st = stats[t]
        st["cases"] += 1
        f = a.parse_row(t, c["row_text"]) if c["row_text"] else None
        if not f:
            st["no_row"] += 1
            continue
        st["parsed"] += 1
        d = a.draft(t, f, c["case_no"] or "")
        st[f"outcome_{d['outcome']}"] += 1
        if d["rule_conflict"]:
            conflicts.append({"case": c["case_no"], "vendor": f.get("vendor"), "amount": f.get("amount"), "kind": f.get("kind"),
                              "check": d["reference_check"]["finding"]})
        if c["human_note"]:
            st["with_human_note"] += 1
            if norm(d["note"]) == norm(c["human_note"]):
                st["note_exact"] += 1
            else:
                misses.append({"type": t, "case": c["case_no"], "draft": d["note"], "human": c["human_note"]})
            if t == "P6":
                human_hold = "要確認" in c["human_note"]
                st["decision_checked"] += 1
                st["decision_agree"] += int(human_hold == (d["outcome"] == "hold"))
    rows = []
    for t, st in sorted(stats.items(), key=lambda kv: int(kv[0][1:])):
        rows.append({"type": t, "status": a.defs[t]["status"] if a.supports(t) else "deferred", **dict(st)})
    res = {"per_process": rows, "p6_rule_conflicts": conflicts, "note_mismatches": misses[:40]}
    json.dump(res, open(os.path.join(OUT, "prototype_replay.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lines = ["# Prototype replay on real dataset-B cases\n\n",
             "Each case's list row (as captured on screen) is fed to the assistant; the drafted note is compared with the note "
             "the worker actually submitted (where the agent captured it).\n\n",
             "| type | status | cases | row parsed | human note visible | note exact match | P6 decisions agree | approve | hold | human |\n|---|---|---|---|---|---|---|---|---|---|\n"]
    for r in rows:
        if r["status"] == "deferred":
            lines.append(f"| {r['type']} | deferred | {r.get('unsupported', 0)} | | | | | | | |\n")
            continue
        dec = f"{r.get('decision_agree', 0)}/{r.get('decision_checked', 0)}" if r["type"] == "P6" else ""
        lines.append(f"| {r['type']} | {r['status']} | {r.get('cases', 0)} | {r.get('parsed', 0)} | {r.get('with_human_note', 0)} | "
                     f"{r.get('note_exact', 0)}/{r.get('with_human_note', 0)} | {dec} | {r.get('outcome_approve', 0)} | "
                     f"{r.get('outcome_hold', 0)} | {r.get('outcome_human', 0)} |\n")
    lines.append(f"\nP6 cases the practised rule approves but the written procedure (fixed-amount list, ±10%) cannot confirm: "
                 f"{len(conflicts)} of {stats['P6'].get('outcome_approve', 0)} approvals\n")
    vend = Counter(c["vendor"] for c in conflicts)
    lines.append("\n" + "".join(f"- {v}: {n}\n" for v, n in vend.most_common()))
    if misses:
        lines.append("\nNote mismatches (first 10):\n\n" + "".join(f"- {m['type']} {m['case']}: draft `{m['draft']}` vs human `{m['human']}`\n" for m in misses[:10]))
    open(os.path.join(OUT, "prototype_replay.md"), "w", encoding="utf-8").write("".join(lines))
    print("".join(lines))


if __name__ == "__main__":
    main()
