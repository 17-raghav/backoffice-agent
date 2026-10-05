"""Scoring a segmentation of dataset A against ground truth.

Ground truth is rebuilt from gt.jsonl (not gt_manifest.json): every process_started / process_resumed opens an
execution that closes at the next boundary event.  The manifest leaves end_ts null for 257 executions; they are
back-to-back cases of the same process (the "duplicate process_started" quirk), so dropping them would delete
exactly the hardest boundaries.

Metrics
  * boundary P/R/F1 at tolerance τ: all segment starts+ends vs all GT starts+ends, one-to-one matching
  * start P/R/F1 at τ
  * segment P/R/F1 at IoU >= 0.5 (one-to-one), mean IoU of matches
  * label consistency over 0.5 s frames inside GT executions: homogeneity, completeness, V-measure, purity
"""
import bisect
import math
import os
import re
from collections import Counter, defaultdict

from .io import load_events, load_gt, sessions, ts_ms

OPEN = ("process_started", "process_resumed")
CLOSE = ("process_switched_out", "process_suspended", "session_ended")


def gt_executions(ses_dir):
    g = sorted(load_gt(ses_dir), key=lambda x: ts_ms(x["ts_utc"]))
    ex, cur = [], None
    for x in g:
        ev, t = x["event"], ts_ms(x["ts_utc"])
        if (ev in OPEN or ev in CLOSE) and cur is not None:
            cur["end"] = t
            ex.append(cur)
            cur = None
        if ev in OPEN:
            cur = {"start": t, "code": x.get("process_code"), "case": x.get("case_id") or x.get("split_id"),
                   "phase": x.get("phase", 1), "variant": x.get("process_variant")}
    return [e for e in ex if e["end"] > e["start"]]


def observed_window(evs):
    ts = [e["timestamp_ms"] for e in evs if e.get("layer") != "SYSTEM"]
    return (min(ts), max(ts)) if ts else (0, 0)


def clip(gt, lo, hi):
    out = []
    for g in gt:
        s, e = max(g["start"], lo), min(g["end"], hi)
        if e - s > 1000:
            out.append({**g, "start": s, "end": e})
    return out


def gt_alignment_check(ses_dir, evs=None):
    """Fraction of GT cases whose case number is first seen on screen 0-30 s after the GT start.
    A healthy session scores ~1.0; a GT file that belongs to a different run scores low."""
    evs = evs or load_events(ses_dir)
    rid = re.compile(r"[a-z]{2}-row-([A-Z]+-\d{6}-\d{3})")
    first = {}
    for e in evs:
        p = e.get("payload") or {}
        blob = ""
        if e["event_type"] == "browser_click":
            blob = str((p.get("element") or {}).get("css_selector"))
        elif e["event_type"] in ("keystroke", "shortcut"):
            blob = str((p.get("target_field") or {}).get("automation_id"))
        m = rid.search(blob)
        if m:
            first.setdefault(m.group(1), e["timestamp_ms"])
    gt = gt_executions(ses_dir)
    seen = [first[g["case"]] - g["start"] for g in gt if g["case"] in first]
    if not seen:
        return None
    return sum(1 for d in seen if 0 <= d <= 30000) / len(seen)


def _merge_points(ts, eps=500):
    out = []
    for t in sorted(ts):
        if not out or t - out[-1] > eps:
            out.append(t)
    return out


def _match_points(gt_b, pr_b, tol):
    pairs = []
    pr_b = sorted(pr_b)
    for i, g in enumerate(gt_b):
        lo = bisect.bisect_left(pr_b, g - tol)
        j = lo
        while j < len(pr_b) and pr_b[j] <= g + tol:
            pairs.append((abs(g - pr_b[j]), i, j))
            j += 1
    pairs.sort()
    ug, up, tp = set(), set(), 0
    for d, i, j in pairs:
        if i not in ug and j not in up:
            ug.add(i); up.add(j); tp += 1
    return tp, len(gt_b), len(pr_b)


def _iou(a, b):
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    uni = max(a[1], b[1]) - min(a[0], b[0])
    return inter / uni if uni > 0 else 0


def _seg_match(gt, pr, thr=0.5):
    cands = []
    for i, g in enumerate(gt):
        for j, p in enumerate(pr):
            if p["end"] > g["start"] and p["start"] < g["end"]:
                v = _iou((g["start"], g["end"]), (p["start"], p["end"]))
                if v >= thr:
                    cands.append((v, i, j))
    cands.sort(reverse=True)
    ug, up, m = set(), set(), []
    for v, i, j in cands:
        if i not in ug and j not in up:
            ug.add(i); up.add(j); m.append((i, j, v))
    return m


def _frames(gt, pr, step=500):
    cont = Counter()
    pr = sorted(pr, key=lambda p: p["start"])
    ps = [p["start"] for p in pr]
    for g in gt:
        t = g["start"] + step / 2
        while t < g["end"]:
            k = bisect.bisect_right(ps, t) - 1
            lab = pr[k]["label"] if k >= 0 and pr[k]["end"] > t else None
            cont[(g["code"], lab)] += 1
            t += step
    return cont


def _H(c):
    n = sum(c.values())
    return -sum(v / n * math.log(v / n) for v in c.values() if v) if n else 0.0


def label_scores(cont):
    lab = Counter({k: v for k, v in cont.items() if k[1] is not None})
    n, tot = sum(lab.values()), sum(cont.values())
    if not n:
        return {"frame_coverage": 0.0}
    C, K = Counter(), Counter()
    for (c, k), v in lab.items():
        C[c] += v; K[k] += v
    HCK = sum(nk / n * _H(Counter({c: v for (c, kk), v in lab.items() if kk == k})) for k, nk in K.items())
    HKC = sum(nc / n * _H(Counter({k: v for (cc, k), v in lab.items() if cc == c})) for c, nc in C.items())
    h = 1 - HCK / _H(C) if _H(C) else 1.0
    comp = 1 - HKC / _H(K) if _H(K) else 1.0
    pur = sum(max(v for (c, kk), v in lab.items() if kk == k) for k in K) / n
    return {"frame_coverage": n / tot, "homogeneity": h, "completeness": comp,
            "v_measure": 2 * h * comp / (h + comp) if h + comp else 0.0, "purity": pur,
            "labels": len(K), "gt_processes": len(C)}


def _prf(tp, a, b):
    p = tp / b if b else 0.0
    r = tp / a if a else 0.0
    return {"P": round(p, 3), "R": round(r, 3), "F1": round(2 * p * r / (p + r), 3) if p + r else 0.0}


def evaluate(pred_by_session, ds_dir, include=None, tols=(1000, 2000, 3000, 5000, 10000), gt_cache=None):
    agg, agg_s = defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0, 0])
    nm = ng = npred = 0
    ious, cont, per = [], Counter(), []
    for s in sessions(ds_dir):
        if include is not None and s not in include:
            continue
        gt = gt_cache[s] if gt_cache else gt_executions(os.path.join(ds_dir, s))
        pr = sorted(pred_by_session.get(s, []), key=lambda p: p["start"])
        gb = _merge_points([g["start"] for g in gt] + [g["end"] for g in gt])
        pb = _merge_points([p["start"] for p in pr] + [p["end"] for p in pr])
        row = {"session": s, "gt": len(gt), "pred": len(pr)}
        for t in tols:
            tp, a, b = _match_points(gb, pb, t)
            agg[t][0] += tp; agg[t][1] += a; agg[t][2] += b
            tp2, a2, b2 = _match_points([g["start"] for g in gt], [p["start"] for p in pr], t)
            agg_s[t][0] += tp2; agg_s[t][1] += a2; agg_s[t][2] += b2
            if t == 2000:
                row["boundary_F1@2s"] = round(2 * tp / (a + b), 3) if a + b else 0.0
        m = _seg_match(gt, pr)
        nm += len(m); ng += len(gt); npred += len(pr)
        ious += [v for _, _, v in m]
        row["segment_F1"] = round(2 * len(m) / (len(gt) + len(pr)), 3) if gt or pr else 1.0
        cont.update(_frames(gt, pr))
        per.append(row)
    res = {}
    for t in tols:
        res[f"boundary@{t / 1000:g}s"] = _prf(*agg[t])
        res[f"start@{t / 1000:g}s"] = _prf(*agg_s[t])
    res["segment_iou0.5"] = {**_prf(nm, ng, npred), "mean_iou": round(sum(ious) / len(ious), 3) if ious else 0.0,
                             "n_gt": ng, "n_pred": npred}
    res["labels"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in label_scores(cont).items()}
    res["per_session"] = per
    return res


def summary_line(name, res):
    b = {k: v["F1"] for k, v in res.items() if k.startswith("boundary@")}
    s = res["segment_iou0.5"]; l = res["labels"]
    return (f"{name:34} bF1@1s={b['boundary@1s']:.3f} @2s={b['boundary@2s']:.3f} @5s={b['boundary@5s']:.3f} "
            f"segF1={s['F1']:.3f} (P {s['P']:.3f} R {s['R']:.3f}) V={l.get('v_measure', 0):.3f} "
            f"purity={l.get('purity', 0):.3f} labels={l.get('labels', 0)}")
