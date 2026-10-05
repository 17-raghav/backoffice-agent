"""Loading sessions, events and ground truth.  Paths come from PROCMINE_DATA or ../data."""
import json
import os
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))


def data_root():
    return os.environ.get("PROCMINE_DATA") or os.path.normpath(os.path.join(_HERE, "..", "..", "data"))


def dataset_dir(name):
    return os.path.join(data_root(), f"dataset_{name.lower()}")


def sessions(ds_dir):
    return sorted(d for d in os.listdir(ds_dir)
                  if d.startswith("ses_") and os.path.isdir(os.path.join(ds_dir, d)))


def load_events(ses_dir):
    """All chunks of a session merged into one time-ordered stream (chunks are recording buckets only)."""
    evs, seen = [], set()
    for ch in sorted(os.listdir(ses_dir)):
        path = os.path.join(ses_dir, ch, "events.jsonl")
        if not (ch.startswith("chunk_") and os.path.isfile(path)):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                if e.get("event_id") in seen or e.get("timestamp_ms") is None:
                    continue
                seen.add(e.get("event_id"))
                evs.append(e)
    evs.sort(key=lambda e: (e["timestamp_ms"], (e.get("correlation") or {}).get("sequence_number") or 0))
    return evs


def load_gt(ses_dir):
    path = os.path.join(ses_dir, "gt.jsonl")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def load_manifest(ses_dir):
    path = os.path.join(ses_dir, "gt_manifest.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def ts_ms(x):
    if x is None:
        return None
    return datetime.fromisoformat(str(x).replace("Z", "+00:00")).timestamp() * 1000


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def text_of(et):
    if isinstance(et, dict):
        return et.get("text") or ""
    if isinstance(et, list):
        return " ".join(map(str, et))
    return str(et or "")
