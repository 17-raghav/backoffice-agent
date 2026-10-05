import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "outputs")
os.makedirs(OUT, exist_ok=True)

from procmine import load_config  # noqa: E402
from procmine.io import dataset_dir, sessions, load_events  # noqa: E402

CFG = load_config()
A = dataset_dir("a")
B = dataset_dir("b")


def write_json(name, obj):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, default=str)


def write_text(name, text):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        fh.write(text)


def md_table(rows, cols):
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    return head + "".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |\n" for r in rows)
