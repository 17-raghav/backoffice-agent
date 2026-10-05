import re
import time
import sqlite3

DB_PATH = "db/air_quality.db"
ROW_LIMIT = 100
TIMEOUT_SECONDS = 5.0

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|"
    r"ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def _validate(sql: str) -> str | None:
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        return "Empty query."
    if ";" in stripped:
        return "Multiple SQL statements are not allowed; submit a single SELECT."
    if not re.match(r"^(SELECT|WITH)\b", stripped, re.IGNORECASE):
        return "Only SELECT queries are allowed."
    if _FORBIDDEN.search(stripped):
        return "Query contains a forbidden (write/DDL) keyword; only reads are allowed."
    return None


def _enforce_limit(sql: str) -> str:
    stripped = sql.strip().rstrip(";").strip()
    if re.search(r"\bLIMIT\b", stripped, re.IGNORECASE):
        return stripped
    return f"{stripped} LIMIT {ROW_LIMIT}"


def run_sql(sql: str) -> str:
    err = _validate(sql)
    if err:
        return f"ERROR: {err}"

    query = _enforce_limit(sql)
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    except sqlite3.OperationalError as e:
        return f"ERROR: could not open database read-only: {e}"

    deadline = time.time() + TIMEOUT_SECONDS
    con.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 1000)

    try:
        cur = con.execute(query)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
    except sqlite3.OperationalError as e:
        msg = str(e)
        if "interrupted" in msg.lower():
            return f"ERROR: query took longer than {TIMEOUT_SECONDS}s and was aborted."
        return f"ERROR: {msg}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"
    finally:
        con.close()

    if not rows:
        return "Query ran successfully but returned no rows."

    header = " | ".join(cols)
    body = "\n".join(" | ".join("" if v is None else str(v) for v in r) for r in rows)
    note = "" if len(rows) < ROW_LIMIT else f"\n[truncated to {ROW_LIMIT} rows]"
    return f"{header}\n{body}{note}"


def get_schema() -> str:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    out = []
    for (name,) in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall():
        cols = con.execute(f"PRAGMA table_info({name})").fetchall()
        col_str = ", ".join(f"{c[1]} {c[2]}" for c in cols)
        out.append(f"{name}({col_str})")
    con.close()
    return "\n".join(out)


if __name__ == "__main__":
    print("=== SCHEMA ===")
    print(get_schema())
    tests = [
        ("valid join", "SELECT l.city, ROUND(AVG(m.value),1) avg_pm25 "
         "FROM measurements m JOIN sensors s ON m.sensor_id=s.sensor_id "
         "JOIN locations l ON s.location_id=l.location_id "
         "WHERE s.parameter='pm25' GROUP BY l.city ORDER BY avg_pm25 DESC LIMIT 5"),
        ("block delete", "DELETE FROM measurements"),
        ("block stacking", "SELECT 1; DROP TABLE locations"),
        ("clean error", "SELECT bad_col FROM measurements"),
    ]
    for label, q in tests:
        print(f"\n--- {label} ---")
        print(run_sql(q))
