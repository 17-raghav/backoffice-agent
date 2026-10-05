import sqlite3
import random
from datetime import date, timedelta

random.seed(7)
DB_PATH = "db/air_quality.db"

CITIES = {
    "Delhi": (110, 2.6), "Ghaziabad": (120, 2.7), "Noida": (105, 2.5),
    "Gurugram": (100, 2.4), "Faridabad": (108, 2.5), "Kanpur": (115, 2.4),
    "Lucknow": (95, 2.3), "Patna": (105, 2.3), "Ludhiana": (88, 2.2),
    "Amritsar": (82, 2.2), "Varanasi": (98, 2.2), "Muzaffarpur": (100, 2.3),
    "Jaipur": (75, 1.9), "Ahmedabad": (70, 1.7), "Mumbai": (55, 1.5),
    "Pune": (50, 1.5), "Kolkata": (72, 1.9), "Chennai": (42, 1.3),
    "Bengaluru": (40, 1.3), "Hyderabad": (48, 1.4),
}

con = sqlite3.connect(DB_PATH)
cur = con.cursor()
cur.executescript("""
    DROP TABLE IF EXISTS measurements;
    DROP TABLE IF EXISTS sensors;
    DROP TABLE IF EXISTS locations;
    CREATE TABLE locations(location_id INTEGER PRIMARY KEY, name TEXT, city TEXT,
        country TEXT, latitude REAL, longitude REAL, timezone TEXT);
    CREATE TABLE sensors(sensor_id INTEGER PRIMARY KEY, location_id INTEGER,
        parameter TEXT, units TEXT);
    CREATE TABLE measurements(id INTEGER PRIMARY KEY AUTOINCREMENT,
        sensor_id INTEGER, date TEXT, value REAL);
""")

loc_id = sensor_id = 0
sensor_meta = []
for city, (base, wmult) in CITIES.items():
    loc_id += 1
    cur.execute("INSERT INTO locations VALUES (?,?,?,?,?,?,?)",
                (loc_id, f"{city} Monitoring Station", city, "India",
                 round(random.uniform(8, 32), 4), round(random.uniform(72, 88), 4),
                 "Asia/Kolkata"))
    for param, units in [("pm25", "µg/m³"), ("pm10", "µg/m³")]:
        sensor_id += 1
        cur.execute("INSERT INTO sensors VALUES (?,?,?,?)",
                    (sensor_id, loc_id, param, units))
        sensor_meta.append((sensor_id, param, base, wmult))

end = date.today()
days = [end - timedelta(days=i) for i in range(365)]
rows = []
for sid, param, base, wmult in sensor_meta:
    scale = 1.0 if param == "pm25" else 1.7
    for d in days:
        winter = d.month in (11, 12, 1)
        shoulder = d.month in (10, 2)
        season = wmult if winter else (1 + (wmult - 1) * 0.4 if shoulder else 1.0)
        val = base * scale * season * random.uniform(0.7, 1.3)
        rows.append((sid, d.isoformat(), round(val, 1)))
cur.executemany("INSERT INTO measurements(sensor_id,date,value) VALUES (?,?,?)", rows)

cur.executescript("""
    CREATE INDEX idx_m_sensor ON measurements(sensor_id);
    CREATE INDEX idx_m_date ON measurements(date);
    CREATE INDEX idx_s_loc ON sensors(location_id);
""")
con.commit()
for t in ["locations", "sensors", "measurements"]:
    n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"{t:14s} {n:>7,} rows")
print(f"\nWrote {DB_PATH}")
con.close()
