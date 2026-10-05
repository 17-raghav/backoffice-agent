import os
import sys
import time
import argparse
import sqlite3
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()
BASE = "https://api.openaq.org/v3"
API_KEY = os.getenv("OPENAQ_API_KEY", "")
DB_PATH = "db/air_quality.db"
HEADERS = {"X-API-Key": API_KEY}


def _extract_city(name: str) -> str:
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


def _get(path, params, max_retries=5):
    url = f"{BASE}{path}"
    for attempt in range(max_retries):
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code == 429:
            wait = 2 ** attempt
            print(f"  rate limited; backing off {wait}s")
            time.sleep(wait)
            continue
        if resp.status_code == 408:
            raise TimeoutError("OpenAQ 408: shrink the date window")
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("exceeded retries (still rate limited)")


def fetch_india_locations(max_locations):
    wanted = {"pm25", "pm10"}
    locations, page = [], 1
    while len(locations) < max_locations:
        data = _get("/locations", {"iso": "IN", "limit": 100, "page": page})
        results = data.get("results", [])
        if not results:
            break
        for loc in results:
            sensors = [
                {"sensor_id": s["id"], "parameter": s["parameter"]["name"],
                 "units": s["parameter"].get("units", "")}
                for s in loc.get("sensors", [])
                if s.get("parameter", {}).get("name") in wanted
            ]
            if not sensors:
                continue
            coords = loc.get("coordinates") or {}
            locations.append({
                "location_id": loc["id"], "name": loc.get("name", ""),
                "city": loc.get("locality") or "",
                "country": (loc.get("country") or {}).get("name", "India"),
                "latitude": coords.get("latitude"), "longitude": coords.get("longitude"),
                "timezone": loc.get("timezone", ""), "sensors": sensors,
            })
            if len(locations) >= max_locations:
                break
        page += 1
    return locations


def fetch_daily(sensor_id, date_from, date_to):
    rows, page = [], 1
    while True:
        try:
            data = _get(f"/sensors/{sensor_id}/days",
                        {"date_from": date_from, "date_to": date_to,
                         "limit": 1000, "page": page})
        except TimeoutError:
            print(f"  sensor {sensor_id}: 408, skipping window")
            break
        results = data.get("results", [])
        if not results:
            break
        for r in results:
            period = r.get("period", {}) or {}
            dt = (period.get("datetimeFrom") or {}).get("local") or \
                 (period.get("datetimeFrom") or {}).get("utc")
            day = (dt or "")[:10]
            val = r.get("value")
            if day and val is not None:
                rows.append((sensor_id, day, val))
        if len(results) < 1000:
            break
        page += 1
        time.sleep(0.2)
    return rows


def build_schema(con):
    con.executescript("""
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
    con.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--max-locations", type=int, default=60)
    args = ap.parse_args()
    if not API_KEY:
        sys.exit("ERROR: set OPENAQ_API_KEY in .env (free at explore.openaq.org/register)")

    date_to = date.today()
    date_from = date_to - timedelta(days=args.days)
    os.makedirs("db", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    build_schema(con)
    cur = con.cursor()

    print(f"Fetching up to {args.max_locations} India locations...")
    locations = fetch_india_locations(args.max_locations)
    print(f"  got {len(locations)} locations with PM sensors")
    for loc in locations:
        cur.execute("INSERT OR REPLACE INTO locations VALUES (?,?,?,?,?,?,?)",
                    (loc["location_id"], loc["name"], loc["city"], loc["country"],
                     loc["latitude"], loc["longitude"], loc["timezone"]))
        for s in loc["sensors"]:
            cur.execute("INSERT OR REPLACE INTO sensors VALUES (?,?,?,?)",
                        (s["sensor_id"], loc["location_id"], s["parameter"], s["units"]))
    con.commit()

    sensors = cur.execute("SELECT sensor_id FROM sensors").fetchall()
    print(f"Fetching daily data for {len(sensors)} sensors ({date_from} to {date_to})...")
    total = 0
    for i, (sid,) in enumerate(sensors, 1):
        rows = fetch_daily(sid, str(date_from), str(date_to))
        cur.executemany("INSERT INTO measurements(sensor_id,date,value) VALUES (?,?,?)", rows)
        con.commit()
        total += len(rows)
        if i % 10 == 0:
            print(f"  {i}/{len(sensors)} sensors, {total} measurements so far")
    print(f"\nDone. {total} daily measurements written to {DB_PATH}")
    con.close()


if __name__ == "__main__":
    main()
