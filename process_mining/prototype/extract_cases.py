"""Rebuild real case records from the dataset B logs: case number, list-row fields as shown on screen,
and the note the worker actually submitted (as captured by the agent's screen text).

Output: prototype/data/b_cases.jsonl  (input for replay.py and the demo portal).
"""
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
from procmine import load_config  # noqa: E402
from procmine import pipeline as PL  # noqa: E402
from procmine.evidence import Rx  # noqa: E402
from procmine.identity import parse_table  # noqa: E402
from procmine.io import dataset_dir  # noqa: E402


def main():
    cfg = load_config()
    rx = Rx(cfg)
    evds = PL.load_evidence(dataset_dir("b"), cfg)
    cb, cat, meta = PL.segment_dataset(dataset_dir("b"), cfg, evds=evds)
    out = []
    for s, cs in cb.items():
        evd = evds[s]
        tables, row_text = [], {}
        for x in evd:
            if x["kind"] == "ocr" and rx.is_browser(x.get("app")):
                rows = parse_table(re.sub(r"\s+", " ", x["text"]), rx)
                if rows:
                    tables.append((x["t"], rows))
                    for cid, p, chunk in rows:
                        row_text.setdefault(cid, chunk.strip())
        for k, c in enumerate(cs):
            o = c["opens"][0] if c["opens"] else {}
            case_no = None
            if not c.get("toast"):
                case_no = next((i for i in c.get("case_ids", []) if i.startswith(c["type"] + "-")), None)
            if not case_no and o.get("row"):
                best = None
                for t, rows in tables:
                    if len(rows) >= o["row"] and rows[o["row"] - 1][1] == c["type"]:
                        if best is None or abs(t - c["open_t"]) < abs(best[0] - c["open_t"]):
                            best = (t, rows[o["row"] - 1][0])
                case_no = best[1] if best else None
            if not case_no and c.get("toast"):
                case_no = c["case_ids"][0]
            hi = cs[k + 1]["open_t"] if k + 1 < len(cs) else c["open_t"] + 60000
            note = ""
            for x in evd:
                if c["open_t"] <= x["t"] < hi and x["kind"] == "ocr" and x.get("src") == "text_pattern" \
                        and rx.is_browser(x.get("app")) and "。" in x["text"] and len(x["text"]) < 200:
                    note = re.sub(r"\s+", " ", x["text"]).strip()
                    break
            out.append({"session": s, "type": c["type"], "case_no": case_no, "row_text": row_text.get(case_no, "") if case_no else "",
                        "human_note": note, "open": c["open_t"], "start": c["start"], "end": c["end"]})
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "b_cases.jsonl"), "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_row = sum(1 for r in out if r["row_text"]); n_note = sum(1 for r in out if r["human_note"])
    print(f"{len(out)} cases, {n_row} with list-row fields, {n_note} with the submitted note visible")


if __name__ == "__main__":
    main()
