import json
import sqlite3

DB_PATH = "db/air_quality.db"


def one(con, sql):
    row = con.execute(sql).fetchone()
    return None if row is None else row[0]


QUESTIONS = [
    {"q": "How many monitoring locations are in the database?",
     "sql": "SELECT COUNT(*) FROM locations", "check": "number"},
    {"q": "How many daily measurements are there in total?",
     "sql": "SELECT COUNT(*) FROM measurements", "check": "number"},
    {"q": "Which city has the highest average PM2.5? Give the city name.",
     "sql": "SELECT l.city FROM measurements m JOIN sensors s ON m.sensor_id=s.sensor_id "
            "JOIN locations l ON s.location_id=l.location_id WHERE s.parameter='pm25' "
            "GROUP BY l.city ORDER BY AVG(m.value) DESC LIMIT 1", "check": "label"},
    {"q": "Which city has the lowest average PM2.5? Give the city name.",
     "sql": "SELECT l.city FROM measurements m JOIN sensors s ON m.sensor_id=s.sensor_id "
            "JOIN locations l ON s.location_id=l.location_id WHERE s.parameter='pm25' "
            "GROUP BY l.city ORDER BY AVG(m.value) ASC LIMIT 1", "check": "label"},
    {"q": "What is the overall average PM2.5 across all cities?",
     "sql": "SELECT AVG(m.value) FROM measurements m JOIN sensors s ON m.sensor_id=s.sensor_id "
            "WHERE s.parameter='pm25'", "check": "number"},
    {"q": "What is the average PM2.5 in Delhi?",
     "sql": "SELECT AVG(m.value) FROM measurements m JOIN sensors s ON m.sensor_id=s.sensor_id "
            "JOIN locations l ON s.location_id=l.location_id "
            "WHERE s.parameter='pm25' AND l.city='Delhi'", "check": "number"},
    {"q": "Which month has the highest average PM2.5 across all cities? Give the month number.",
     "sql": "SELECT CAST(strftime('%m', m.date) AS INTEGER) mo FROM measurements m "
            "JOIN sensors s ON m.sensor_id=s.sensor_id WHERE s.parameter='pm25' "
            "GROUP BY mo ORDER BY AVG(m.value) DESC LIMIT 1", "check": "number"},
    {"q": "How many cities have an average PM2.5 above 100?",
     "sql": "SELECT COUNT(*) FROM (SELECT l.city FROM measurements m "
            "JOIN sensors s ON m.sensor_id=s.sensor_id JOIN locations l ON s.location_id=l.location_id "
            "WHERE s.parameter='pm25' GROUP BY l.city HAVING AVG(m.value) > 100)", "check": "number"},
    {"q": "What is the highest single daily PM2.5 value recorded?",
     "sql": "SELECT MAX(m.value) FROM measurements m JOIN sensors s ON m.sensor_id=s.sensor_id "
            "WHERE s.parameter='pm25'", "check": "number"},
    {"q": "What is the average PM10 across all cities?",
     "sql": "SELECT AVG(m.value) FROM measurements m JOIN sensors s ON m.sensor_id=s.sensor_id "
            "WHERE s.parameter='pm10'", "check": "number"},
    {"q": "Which city has the highest average PM10? Give the city name.",
     "sql": "SELECT l.city FROM measurements m JOIN sensors s ON m.sensor_id=s.sensor_id "
            "JOIN locations l ON s.location_id=l.location_id WHERE s.parameter='pm10' "
            "GROUP BY l.city ORDER BY AVG(m.value) DESC LIMIT 1", "check": "label"},
    {"q": "What is the average PM2.5 during winter months (Nov, Dec, Jan)?",
     "sql": "SELECT AVG(m.value) FROM measurements m JOIN sensors s ON m.sensor_id=s.sensor_id "
            "WHERE s.parameter='pm25' AND CAST(strftime('%m', m.date) AS INTEGER) IN (11,12,1)",
     "check": "number"},
    {"q": "How many distinct parameters are measured?",
     "sql": "SELECT COUNT(DISTINCT parameter) FROM sensors", "check": "number"},
    {"q": "What is the average PM2.5 in Amritsar?",
     "sql": "SELECT AVG(m.value) FROM measurements m JOIN sensors s ON m.sensor_id=s.sensor_id "
            "JOIN locations l ON s.location_id=l.location_id "
            "WHERE s.parameter='pm25' AND l.city='Amritsar'", "check": "number"},
]


def build():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    out = []
    for item in QUESTIONS:
        ans = one(con, item["sql"])
        if item["check"] == "number" and ans is not None:
            ans = round(float(ans), 2)
        out.append({"q": item["q"], "sql": item["sql"], "check": item["check"], "answer": ans})
    con.close()
    with open("eval/ground_truth.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"Computed ground truth for {len(out)} questions:\n")
    for i, item in enumerate(out, 1):
        print(f"{i:2d}. {item['q']}\n    expected ({item['check']}): {item['answer']}")


if __name__ == "__main__":
    build()
