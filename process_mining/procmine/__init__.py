"""procmine: recover units of work (business-case executions) from desktop operation logs."""
import json
import os
import sys

# Reports and screen text are Japanese; force UTF-8 stdout/stderr so the scripts
# print correctly on a stock Windows console (default cp1252 raises UnicodeEncodeError).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

_HERE = os.path.dirname(os.path.abspath(__file__))


def load_config(path=None):
    path = path or os.path.join(_HERE, "..", "config", "default.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
