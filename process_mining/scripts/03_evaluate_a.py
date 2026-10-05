"""Evaluate baselines, the full method and ablations on dataset A (the only data with ground truth).

Scoring window: GT is clipped to what was recorded; sessions failing the GT/recording alignment check are
excluded (both are reported in outputs/data_audit.md).  Writes outputs/eval_a.md, eval_a.json, eval_a_sessions.csv.
"""
import copy
import csv
import os
import time

from _common import A, CFG, OUT, load_events, md_table, sessions, write_json, write_text
from procmine import evaluate as EVL
from procmine import pipeline as PL
from procmine.evidence import Rx


def baseline_gap(evds, gap_ms):
    out = {}
    for s, evd in evds.items():
        ts = sorted(x["t"] for x in evd if x["kind"] not in ("ocr",))
        segs, st, prev = [], ts[0], ts[0]
        for t in ts[1:]:
            if t - prev > gap_ms:
                segs.append({"start": st, "end": prev, "label": "work"})
                st = t
            prev = t
        segs.append({"start": st, "end": prev, "label": "work"})
        out[s] = [x for x in segs if x["end"] - x["start"] >= 1000]
    return out


def baseline_slot_runs(evds, cfg):
    npr = set(cfg["non_process_routes"])
    out = {}
    for s, evd in evds.items():
        segs, cur = [], None
        for x in evd:
            if x.get("port") and x.get("route") and x["route"] not in npr:
                slot = (x["port"], x["route"])
                if cur is None or cur["slot"] != slot:
                    if cur:
                        segs.append(cur)
                    cur = {"slot": slot, "start": x["t"], "end": x["t"]}
                cur["end"] = x["t"]
        if cur:
            segs.append(cur)
        out[s] = [{"start": g["start"], "end": max(g["end"], g["start"] + 1000), "label": "|".join(g["slot"])} for g in segs]
    return out


def strip_l2(evds):
    return {s: [x for x in evd if not (x["kind"] == "click" and x.get("layer") == "L2")] for s, evd in evds.items()}


def main():
    t0 = time.time()
    evds = PL.load_evidence(A, CFG)
    gt_cache, include, excluded = {}, set(), []
    for s in sessions(A):
        sd = os.path.join(A, s)
        al = EVL.gt_alignment_check(sd)
        if al is not None and al < 0.5:
            excluded.append(s)
            continue
        lo, hi = evds[s][0]["t"], evds[s][-1]["t"]
        gt_cache[s] = EVL.clip(EVL.gt_executions(sd), lo, hi)
        include.add(s)
    no_ext = {s for s in include if not any(x["kind"] == "click" and x.get("layer") == "L3" for x in evds[s])}
    runs = {}

    def score(name, pred, subset=None):
        res = EVL.evaluate(pred, A, include=subset or include, gt_cache=gt_cache)
        runs[name] = res
        print(EVL.summary_line(name, res), flush=True)
        return res

    score("baseline: idle gap > 5 s", baseline_gap(evds, 5000))
    score("baseline: idle gap > 2 s", baseline_gap(evds, 2000))
    score("baseline: screen-slot runs", baseline_slot_runs(evds, CFG))
    cb, cat, meta = PL.segment_dataset(A, CFG, evds=evds)
    full = PL.to_segments(cb)
    res_full = score("procmine (full)", full)
    score("  subset: sessions with extension", full, include - no_ext)
    score("  subset: sessions without extension", full, no_ext)
    # ablations
    cfg2 = copy.deepcopy(CFG); cfg2["lags_ms"]["nav_max_before_open"] = -1
    cb2, _, _ = PL.segment_dataset(A, cfg2, evds=evds)
    score("ablation: no navigation anchor", PL.to_segments(cb2))
    cb3, _, _ = PL.segment_dataset(A, CFG, evds=strip_l2(evds))
    score("ablation: extension (L3) clicks only", PL.to_segments(cb3))
    cb4, _, _ = PL.segment_dataset(A, CFG, evds=evds, gap_cut_ms=12000)
    score("ablation: cut idle gaps > 12 s", PL.to_segments(cb4))
    score("ablation: label = screen slot only", PL.to_segments(cb, lambda c: "|".join(map(str, c.get("slot", ("?", "?"))))))
    cfg5 = copy.deepcopy(CFG)
    for k in ("nav", "open_same", "open_change", "tail", "final_after_dashboard_nav", "final_after_last_commit"):
        cfg5["lags_ms"][k] = 0
    cb5, _, _ = PL.segment_dataset(A, cfg5, evds=evds)
    score("ablation: no lag calibration (cut at click)", PL.to_segments(cb5))

    rows = []
    for name, r in runs.items():
        rows.append({"method": name, "bF1@1s": r["boundary@1s"]["F1"], "bF1@2s": r["boundary@2s"]["F1"],
                     "bF1@5s": r["boundary@5s"]["F1"], "startF1@2s": r["start@2s"]["F1"],
                     "segF1(IoU≥.5)": r["segment_iou0.5"]["F1"], "segP": r["segment_iou0.5"]["P"],
                     "segR": r["segment_iou0.5"]["R"], "labelV": r["labels"].get("v_measure", ""),
                     "purity": r["labels"].get("purity", ""), "#labels": r["labels"].get("labels", "")})
    with open(os.path.join(OUT, "eval_a_sessions.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["session", "gt", "pred", "boundary_F1@2s", "segment_F1"])
        w.writeheader()
        w.writerows(res_full["per_session"])
    srcs = {}
    for cs in cb.values():
        for c in cs:
            srcs[c["type_src"]] = srcs.get(c["type_src"], 0) + 1
    write_json("eval_a.json", {"runs": {k: {kk: vv for kk, vv in v.items() if kk != "per_session"} for k, v in runs.items()},
                               "excluded_sessions": excluded, "scored_sessions": len(include),
                               "sessions_without_extension": sorted(no_ext), "type_sources": srcs, "meta": meta})
    md = ["# Evaluation on dataset A\n\n",
          f"Scored sessions: {len(include)} (excluded, GT does not match recording: {', '.join(excluded) or 'none'}). ",
          "GT clipped to the recorded window. Boundary F1: all segment starts+ends vs GT starts+ends, one-to-one within τ. ",
          "Segment F1: one-to-one matches with IoU ≥ 0.5. Labels: frame-level V-measure / purity vs GT process code.\n\n",
          md_table(rows, list(rows[0].keys())),
          f"\nCase-type evidence used (full method): {srcs}\n",
          f"\nRuntime: {time.time() - t0:.0f} s\n"]
    write_text("eval_a.md", "".join(md))


if __name__ == "__main__":
    main()
