"""Probes beyond test_sql_safety.py: cases where the safety layer's behaviour is not obvious.
Prints what happens; it does not assert, because some rows document known gaps.

  python eval/probe_safety_gaps.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.sql_tool import run_sql  # noqa: E402

PROBES = [
    ("runaway recursive CTE (timeout defence)",
     "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT COUNT(*) FROM c"),
    ("large cross join (timeout defence)",
     "SELECT COUNT(*) FROM measurements a, measurements b"),
    ("row cap: no LIMIT given", "SELECT id FROM measurements"),
    ("row cap: caller's own large LIMIT", "SELECT id FROM measurements LIMIT 100000"),
    ("row cap: LIMIT only in a subquery",
     "SELECT id FROM measurements WHERE id IN (SELECT id FROM measurements LIMIT 5) OR 1=1"),
    ("false positive: forbidden word inside a string literal",
     "SELECT COUNT(*) FROM locations WHERE name LIKE '%Replace%'"),
    ("table-valued pragma function (schema read)",
     "SELECT name FROM pragma_table_info('locations')"),
    ("load_extension call", "SELECT load_extension('evil')"),
    ("schema read via sqlite_master", "SELECT name FROM sqlite_master"),
]


def main():
    for label, sql in PROBES:
        t = time.time()
        out = run_sql(sql)
        dt = time.time() - t
        lines = out.splitlines()
        if out.startswith("ERROR:"):
            summary = lines[0][:110]
        else:
            n = len(lines) - 1 - (1 if lines and lines[-1].startswith("[truncated") else 0)
            summary = f"allowed, {n} data rows" + (" (truncated note)" if lines[-1].startswith("[truncated") else "")
        print(f"- {label}: {summary}  [{dt:.2f}s]")


if __name__ == "__main__":
    main()
