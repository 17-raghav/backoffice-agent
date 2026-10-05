"""Step 1 deliverable: segment dataset B -> segments.jsonl (repo root) + outputs/cases_b.csv.

Labels: one label per case type.  The grouping is automatic (case-number prefix); the human-readable
name comes from config/process_names_b.json (written once, LLM-assisted, from the on-screen page name and
the note template workers paste; see outputs/process_catalog_b.json for the raw evidence).
"""
import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from _common import B, CFG, OUT, ROOT, load_events, sessions, write_json
from procmine import pipeline as PL
from procmine.evidence import Rx

NAMES = os.path.join(ROOT, "config", "process_names_b.json")


def iso_s(ms):
    return datetime.fromtimestamp(round(ms / 1000), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def note_heads(cb, evds, rx):
    """Most common first clause of the note text visible while each case is open -> process wording."""
    heads = defaultdict(Counter)
    for s, cs in cb.items():
        evd = evds[s]
        for k, c in enumerate(cs):
            hi = cs[k + 1]["open_t"] if k + 1 < len(cs) else c["open_t"] + 60000
            for x in evd:
                if x["t"] < c["open_t"]:
                    continue
                if x["t"] >= hi:
                    break
                if x["kind"] == "ocr" and x.get("src") == "text_pattern" and rx.is_browser(x.get("app")):
                    t = re.sub(r"\s+", " ", x["text"]).strip()
                    if len(t) < 160 and "。" in t:
                        heads[c["type"]][t.split("。")[0]] += 1
                        c.setdefault("note_text", t)
    return heads


def main():
    rx = Rx(CFG)
    evds = PL.load_evidence(B, CFG)
    cb, cat, meta = PL.segment_dataset(B, CFG, evds=evds)
    heads = note_heads(cb, evds, rx)
    users = {}
    for s in sessions(B):
        evs = load_events(os.path.join(B, s))
        users[s] = Counter((e.get("source") or {}).get("username_hash") for e in evs).most_common(1)[0][0]
    # catalogue of case types found in B
    slots = defaultdict(Counter)
    for cs in cb.values():
        for c in cs:
            slots[c["type"]][c.get("slot")] += 1
    catalog = {}
    for t, sc in slots.items():
        slot = sc.most_common(1)[0][0]
        page = cat.page_names.get(slot, Counter()).most_common(1)
        catalog[t] = {"cases": sum(sc.values()), "screen": "|".join(map(str, slot)),
                      "page_name": page[0][0] if page else None,
                      "note_head": heads[t].most_common(1)[0][0] if heads[t] else None}
    write_json("process_catalog_b.json", catalog)
    names = json.load(open(NAMES, encoding="utf-8")) if os.path.exists(NAMES) else {}
    label = lambda c: names.get(c["type"], {}).get("label", c["type"])

    n = 0
    with open(os.path.join(ROOT, "segments.jsonl"), "w", encoding="utf-8") as fh:
        for s in sorted(cb):
            prev_end = None
            for c in cb[s]:
                st, en = round(c["start"] / 1000) * 1000, round(c["end"] / 1000) * 1000
                if prev_end is not None:
                    st = max(st, prev_end)
                if en <= st:
                    en = st + 1000
                prev_end = en
                fh.write(json.dumps({"session_id": s, "start": iso_s(st), "end": iso_s(en), "label": label(c)},
                                    ensure_ascii=False) + "\n")
                n += 1
    cols = ["session_id", "user", "case_no", "type", "label", "type_evidence", "screen", "start", "end", "duration_s",
            "open", "active_s", "commits", "evidence_layer", "note_text"]
    with open(os.path.join(OUT, "cases_b.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for s in sorted(cb):
            for c in cb[s]:
                w.writerow({"session_id": s, "user": users[s], "case_no": (c.get("case_ids") or [""])[0], "type": c["type"],
                            "label": label(c), "type_evidence": c["type_src"], "screen": "|".join(map(str, c.get("slot", ("", "")))),
                            "start": iso_s(c["start"]), "end": iso_s(c["end"]), "duration_s": round((c["end"] - c["start"]) / 1000, 1),
                            "open": iso_s(c["open_t"]), "active_s": round((c["last_productive"] - c["open_t"]) / 1000, 1),
                            "commits": len(c["commit_t"]), "evidence_layer": c.get("src"), "note_text": c.get("note_text", "")})
    print(f"segments.jsonl: {n} segments in {len(cb)} sessions; tempo={meta['tempo']:.3f}; l2={meta['l2_profile']}")
    print("case types:", {k: v["cases"] for k, v in sorted(catalog.items())})
    print("type evidence:", Counter(c["type_src"] for cs in cb.values() for c in cs))
    for k, v in sorted(catalog.items(), key=lambda kv: (len(kv[0]), kv[0])):
        print(f"  {k:5} {v}")


if __name__ == "__main__":
    main()
