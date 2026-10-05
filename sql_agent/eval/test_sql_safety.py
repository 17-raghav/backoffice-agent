import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.sql_tool import run_sql, DB_PATH

BLOCK = [
    ("write: DELETE", "DELETE FROM measurements"),
    ("write: UPDATE", "UPDATE locations SET city='x'"),
    ("write: INSERT", "INSERT INTO locations VALUES (1,'n','c','I',0,0,'t')"),
    ("write: REPLACE", "REPLACE INTO locations VALUES (1,'n','c','I',0,0,'t')"),
    ("ddl: DROP", "DROP TABLE locations"),
    ("ddl: ALTER", "ALTER TABLE locations ADD COLUMN hacked TEXT"),
    ("ddl: CREATE", "CREATE TABLE hack(a INTEGER)"),
    ("ddl: TRUNCATE", "TRUNCATE measurements"),
    ("ddl: REINDEX", "REINDEX locations"),
    ("db: ATTACH", "ATTACH DATABASE 'evil.db' AS evil"),
    ("db: DETACH", "DETACH DATABASE evil"),
    ("db: PRAGMA", "PRAGMA table_info(locations)"),
    ("db: VACUUM", "VACUUM"),
    ("perm: GRANT", "GRANT ALL ON locations TO x"),
    ("perm: REVOKE", "REVOKE ALL ON locations FROM x"),
    ("stack: select then drop", "SELECT 1; DROP TABLE locations"),
    ("stack: select then delete", "SELECT 1; DELETE FROM measurements"),
    ("stack: trailing write", "SELECT 1; UPDATE locations SET city='x'"),
    ("case: mixed-case delete", "dElEtE FROM measurements"),
    ("case: lower drop", "drop table locations"),
    ("evasion: CTE hiding DELETE", "WITH t AS (SELECT 1) DELETE FROM measurements"),
    ("evasion: comment then stack", "SELECT 1 -- comment\n; DROP TABLE locations"),
    ("evasion: leading whitespace drop", "   \n  DROP TABLE locations"),
    ("evasion: trailing semicolon drop", "DROP TABLE locations;"),
    ("shape: not a select (EXPLAIN)", "EXPLAIN SELECT * FROM locations"),
    ("shape: empty", ""),
    ("shape: whitespace only", "    "),
]

ALLOW = [
    ("read: simple count", "SELECT COUNT(*) FROM locations"),
    ("read: lowercase select", "select city from locations limit 5"),
    ("read: join aggregate",
     "SELECT l.city, AVG(m.value) FROM measurements m "
     "JOIN sensors s ON m.sensor_id=s.sensor_id "
     "JOIN locations l ON s.location_id=l.location_id "
     "WHERE s.parameter='pm25' GROUP BY l.city"),
    ("read: legit CTE",
     "WITH t AS (SELECT city FROM locations) SELECT * FROM t LIMIT 3"),
    ("read: classic-injection string is harmless on read",
     "SELECT city FROM locations WHERE city='' OR 1=1"),
]


def is_blocked(sql):
    return run_sql(sql).startswith("ERROR:")


def driver_refuses_write():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        con.execute("CREATE TABLE should_not_exist(a INTEGER)")
        return False
    except sqlite3.OperationalError:
        return True
    finally:
        con.close()


def main():
    passed = 0
    total = len(BLOCK) + len(ALLOW)

    print("Adversarial (must be BLOCKED):")
    for label, sql in BLOCK:
        ok = is_blocked(sql)
        passed += ok
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")

    print("\nLegitimate reads (must be ALLOWED):")
    for label, sql in ALLOW:
        ok = not is_blocked(sql)
        passed += ok
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")

    ro = driver_refuses_write()
    print(f"\nRead-only driver refuses writes (backstop): {'PASS' if ro else 'FAIL'}")

    n_block = len(BLOCK)
    blocked = sum(is_blocked(s) for _, s in BLOCK)
    print(f"\n{'='*50}")
    print(f"Blocked {blocked}/{n_block} adversarial write/injection attempts")
    print(f"Overall {passed}/{total} classification cases + driver backstop {'ok' if ro else 'FAILED'}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
