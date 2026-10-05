import re
import sqlite3
from difflib import SequenceMatcher

DB_PATH = "db/air_quality.db"
SIMILARITY_FLAG_THRESHOLD = 0.70

_AFFIXES = {"new", "greater", "navi", "old", "north", "south",
            "east", "west", "central", "upper", "lower"}


def canonical_form(name: str) -> str:
    tokens = [t for t in re.split(r"\s+", name.lower().strip()) if t]
    while len(tokens) > 1 and tokens[0] in _AFFIXES:
        tokens = tokens[1:]
    return " ".join(tokens)


def main():
    con = sqlite3.connect(DB_PATH)
    cities = [r[0] for r in con.execute(
        "SELECT DISTINCT city FROM locations WHERE city != '' AND city IS NOT NULL"
    ).fetchall()]

    groups = {}
    for c in cities:
        groups.setdefault(canonical_form(c), []).append(c)

    canonical_map = {}
    merges = []
    for variants in groups.values():
        display = min(variants, key=len)
        for v in variants:
            canonical_map[v] = display
        if len(variants) > 1:
            merges.append((variants, display))

    print("=== TIER 1: safe auto-merges ===")
    if merges:
        for variants, display in merges:
            print(f"  {variants} -> '{display}'")
    else:
        print("  (none found)")

    updated = 0
    for variant, display in canonical_map.items():
        if variant != display:
            cur = con.execute("UPDATE locations SET city=? WHERE city=?", (display, variant))
            updated += cur.rowcount
    con.commit()
    print(f"  applied: {updated} rows updated")

    print(f"\n=== TIER 2: flagged for review (similarity >= {SIMILARITY_FLAG_THRESHOLD}, NOT merged) ===")
    canon_names = sorted(set(canonical_map.values()))
    flagged = 0
    for i in range(len(canon_names)):
        for j in range(i + 1, len(canon_names)):
            a, b = canon_names[i], canon_names[j]
            ratio = SequenceMatcher(None, a.lower(), b.lower()).ratio()
            if ratio >= SIMILARITY_FLAG_THRESHOLD:
                print(f"  POSSIBLE DUP: '{a}' ~ '{b}'  (similarity {ratio:.2f}) -- review manually")
                flagged += 1
    if flagged == 0:
        print("  (no ambiguous pairs)")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
