"""Step 2: what work is done in B, how often, how long, by how many people, with which handling patterns.

Reads the Step-1 segmentation, recomputes per-case features from the raw evidence and writes
outputs/analysis_b.md, analysis_b.json, cases_b_features.csv.
Timings are from a test environment with compressed waits: compare processes with each other only.
"""
import csv
import json
import os
import re
import statistics
from collections import Counter, defaultdict

from _common import B, CFG, OUT, ROOT, load_events, md_table, sessions, write_json, write_text
from procmine import pipeline as PL
from procmine.evidence import Rx

NAMES = json.load(open(os.path.join(ROOT, "config", "process_names_b.json"), encoding="utf-8"))
DOC_APPS = ("Microsoft Word", "Microsoft Excel")
EXCEPTION_RX = re.compile(r"要確認|差異あり|緊急|保留|差戻|却下|超過|不備|エラー")


def doc_name(title):
    """Reference documents are saved under romanised file names (e.g. kazoku_teate_kitei, expense_calc)."""
    m = re.match(r"^\*?([A-Za-z0-9]+(?:_[A-Za-z0-9]+)+)\b", (title or "").strip())
    return m.group(1) if m else None


def main():
    rx = Rx(CFG)
    evds = PL.load_evidence(B, CFG)
    cb, cat, meta = PL.segment_dataset(B, CFG, evds=evds)
    user_of, portal_accounts = {}, defaultdict(set)
    for s in sessions(B):
        evs = load_events(os.path.join(B, s))
        user_of[s] = Counter((e.get("source") or {}).get("username_hash") for e in evs).most_common(1)[0][0]
    rows = []
    for s, cs in cb.items():
        evd = evds[s]
        for k, c in enumerate(cs):
            win = [x for x in evd if c["start"] <= x["t"] < c["end"]]
            docs = {doc_name(x.get("title")) for x in win if x.get("app") in DOC_APPS} - {None}
            memo = {re.sub(r"^\*|\s+-\s+Notepad$", "", x.get("title") or "") for x in win if x.get("app") == "Notepad" and x["kind"] == "edit"} - {"", "Notepad", "Untitled"}
            excel_edit = any(x["kind"] == "edit" and x.get("app") == "Microsoft Excel" for x in win)
            note = ""
            for x in win:
                if x["kind"] == "ocr" and x.get("src") == "text_pattern" and rx.is_browser(x.get("app")):
                    t = re.sub(r"\s+", " ", x["text"]).strip()
                    if len(t) < 160 and "。" in t:
                        note = t
                        break
                if x["kind"] == "ocr" and rx.is_browser(x.get("app")):
                    for m in re.finditer(r"(田中 麻里|佐藤 直樹|高橋 健司)\s*·\s*(\S+)", x["text"]):
                        portal_accounts[m.group(1) + " · " + m.group(2)].add(user_of[s])
            rows.append({
                "session": s, "user": user_of[s], "type": c["type"], "label": NAMES.get(c["type"], {}).get("label", c["type"]),
                "duration_s": (c["end"] - c["start"]) / 1000, "handle_s": (c["last_productive"] - c["open_t"]) / 1000,
                "clicks": sum(1 for x in win if x["kind"] == "click" and not x.get("dup")),
                "keys": sum(1 for x in win if x["kind"] == "edit"),
                "switches": sum(1 for x in win if x["kind"] == "focus"),
                "docs": "|".join(sorted(docs)), "n_docs": len(docs), "memo": "|".join(sorted(memo)), "excel_logged": excel_edit,
                "note": note, "note_template": re.sub(r"[0-9０-９][0-9０-９,，.\-]*", "#", note.split("。")[0] + "。" + (note.split("。")[-2] if note.count("。") > 1 else "")) if note else "",
                "exception": bool(EXCEPTION_RX.search(note)),
            })
    with open(os.path.join(OUT, "cases_b_features.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    by = defaultdict(list)
    for r in rows:
        by[r["type"]].append(r)
    total_time = sum(r["duration_s"] for r in rows)
    table = []
    for t, rs in by.items():
        docs = Counter(d for r in rs for d in r["docs"].split("|") if d)
        notes = [r for r in rs if r["note"]]
        outcomes = Counter(r["note"].split("。")[-2] if r["note"].count("。") > 1 else r["note"] for r in notes)
        table.append({
            "type": t, "process": NAMES.get(t, {}).get("ja", t), "label": NAMES.get(t, {}).get("label", t),
            "dept": NAMES.get(t, {}).get("dept", ""), "cases": len(rs), "case_share": round(len(rs) / len(rows), 3),
            "total_min": round(sum(r["duration_s"] for r in rs) / 60, 1),
            "time_share": round(sum(r["duration_s"] for r in rs) / total_time, 3),
            "median_case_s": round(statistics.median(r["duration_s"] for r in rs), 1),
            "median_handle_s": round(statistics.median(r["handle_s"] for r in rs), 1),
            "users": len({r["user"] for r in rs}), "sessions": len({r["session"] for r in rs}),
            "clicks_per_case": round(statistics.mean(r["clicks"] for r in rs), 1),
            "keys_per_case": round(statistics.mean(r["keys"] for r in rs), 1),
            "switches_per_case": round(statistics.mean(r["switches"] for r in rs), 1),
            "doc_lookup_rate": round(sum(1 for r in rs if r["n_docs"]) / len(rs), 2),
            "distinct_docs": len(docs), "top_docs": ", ".join(d for d, _ in docs.most_common(3)),
            "excel_logging_rate": round(sum(1 for r in rs if r["excel_logged"]) / len(rs), 2),
            "memo_logging_rate": round(sum(1 for r in rs if r["memo"]) / len(rs), 2),
            "notes_seen": len(notes), "exception_rate": round(sum(1 for r in notes if r["exception"]) / len(notes), 2) if notes else None,
            "distinct_note_templates": len({r["note_template"] for r in notes}),
            "outcomes": "; ".join(f"{o[:28]}×{n}" for o, n in outcomes.most_common(3)),
        })
    table.sort(key=lambda r: -r["total_min"])
    people = {"machines_users": len(set(user_of.values())), "sessions": len(user_of),
              "sessions_per_user": dict(Counter(user_of.values())),
              "portal_accounts_seen_by_users": {k: len(v) for k, v in portal_accounts.items()}}
    write_json("analysis_b.json", {"processes": table, "people": people, "total_case_minutes": round(total_time / 60, 1),
                                   "cases": len(rows), "meta": meta})
    cols1 = ["type", "process", "dept", "cases", "case_share", "total_min", "time_share", "median_case_s", "median_handle_s", "users", "sessions"]
    cols2 = ["type", "clicks_per_case", "keys_per_case", "switches_per_case", "doc_lookup_rate", "distinct_docs", "top_docs",
             "excel_logging_rate", "memo_logging_rate", "exception_rate", "distinct_note_templates", "outcomes"]
    md = ["# Dataset B — what the work is (Step 2)\n\n",
          f"{len(rows)} cases in {len(user_of)} sessions, {round(total_time / 60, 1)} case-minutes. "
          f"{people['machines_users']} distinct Windows users. Timings are from a compressed test environment — relative only.\n\n",
          "## Volume and time\n\n", md_table(table, cols1), "\n## Handling patterns\n\n", md_table(table, cols2),
          "\n## People\n\n", json.dumps(people, ensure_ascii=False, indent=1), "\n"]
    write_text("analysis_b.md", "".join(md))
    print("".join(md))


if __name__ == "__main__":
    main()
