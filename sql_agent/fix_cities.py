import sqlite3


def extract_city(name: str) -> str:
    parts = [p.strip() for p in name.split(" - ")]
    core_parts = parts[:-1] if len(parts) > 1 else parts
    core = " - ".join(core_parts)
    if "," in core:
        city = core.rsplit(",", 1)[-1].strip()
    elif len(core_parts) > 1:
        city = core_parts[-1].strip()
    else:
        return ""
    return city


con = sqlite3.connect("db/air_quality.db")
rows = con.execute(
    "SELECT location_id, name FROM locations WHERE city='' OR city IS NULL"
).fetchall()
updated = 0
for loc_id, name in rows:
    city = extract_city(name)
    if city:
        con.execute("UPDATE locations SET city=? WHERE location_id=?", (city, loc_id))
        updated += 1
con.commit()
print(f"Backfilled city for {updated} of {len(rows)} previously-blank locations")
remaining = con.execute(
    "SELECT COUNT(*) FROM locations WHERE city='' OR city IS NULL"
).fetchone()[0]
print(f"{remaining} locations still have no recoverable city name")
con.close()
