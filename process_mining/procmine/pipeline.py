"""End-to-end: dataset directory -> cases with boundaries and case-type labels."""
import os

from . import boundaries as BD
from . import cases as CS
from . import evidence as EV
from . import identity as ID
from .io import load_events, sessions


def load_evidence(ds_dir, cfg, only=None):
    out = {}
    for s in sessions(ds_dir):
        if only and s not in only:
            continue
        out[s] = EV.build(load_events(os.path.join(ds_dir, s)), cfg)
    return out


def segment_dataset(ds_dir, cfg, evds=None, gap_cut_ms=None, nav_fallback=True, tempo=None):
    evds = evds if evds is not None else load_evidence(ds_dir, cfg)
    rx = EV.Rx(cfg)
    prof = CS.learn_l2_profile(evds.values())
    tempo = BD.tempo_ratio(evds.values(), cfg) if tempo is None else tempo
    cases_by = {}
    for s, evd in evds.items():
        cs = CS.assemble(evd, prof, cfg, tempo)
        if nav_fallback:
            cs = CS.add_nav_fallback(cs, evd, cfg, tempo)
        ID.attach_case_ids(cs, evd, rx)
        cases_by[s] = CS.merge_same_case(cs)
    cat = ID.Catalog(cfg)
    for s, evd in evds.items():
        cat.learn(evd, cases_by[s])
    cat.finalize()
    for s, cs in cases_by.items():
        for c in cs:
            c["type"], c["type_src"] = cat.resolve(c)
        smooth_ambiguous(cs, cat)
        BD.place(cs, evds[s], cfg, tempo, gap_cut_ms, rx)
        if evds[s]:                                   # never extend beyond the recording
            lo, hi = evds[s][0]["t"], evds[s][-1]["t"]
            for c in cs:
                c["start"], c["end"] = max(c["start"], lo), min(c["end"], hi)
        cases_by[s] = [c for c in cs if c["end"] - c["start"] >= 1000]
    meta = {"tempo": tempo, "l2_profile": prof}
    return cases_by, cat, meta


STRONG = {"case_id", "table_row", "toast", "cell_text"}


def smooth_ambiguous(cs, cat):
    """A case typed only by its screen, on a screen that hosts several case types (or not typed at all),
    takes the type of an adjacent strongly-typed case on the same screen (work is done in batches)."""
    for i, c in enumerate(cs):
        if c["type_src"] in STRONG:
            continue
        votes = cat.slot_votes.get(c.get("slot"), {})
        if c["type_src"] == "slot" and len([p for p, v in votes.items() if v / max(1, sum(votes.values())) >= 0.1]) <= 1:
            continue
        for j in (i + 1, i - 1, i + 2, i - 2):
            if 0 <= j < len(cs) and cs[j]["type_src"] in STRONG and cs[j].get("slot") == c.get("slot"):
                c["type"], c["type_src"] = cs[j]["type"], "neighbour"
                break


def to_segments(cases_by, label_fn=None):
    label_fn = label_fn or (lambda c: c["type"])
    return {s: [{"start": c["start"], "end": c["end"], "label": label_fn(c)} for c in cs] for s, cs in cases_by.items()}
