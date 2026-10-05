from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

REFERENCES = [
    ("How many monitoring locations are in the database?",
     "Count rows in locations."),
    ("How many daily measurements are there in total?",
     "Count rows in measurements."),
    ("Which city has the highest average PM2.5? Give the city name.",
     "Join measurements->sensors->locations, filter parameter='pm25', GROUP BY city, ORDER BY AVG(value) DESC."),
    ("Which city has the lowest average PM2.5? Give the city name.",
     "Join measurements->sensors->locations, filter parameter='pm25', GROUP BY city, ORDER BY AVG(value) ASC."),
    ("What is the overall average PM2.5 across all cities?",
     "AVG(value) over measurements joined to sensors where parameter='pm25'."),
    ("What is the average PM2.5 in Delhi?",
     "AVG(value) joined through locations where city='Delhi' and parameter='pm25'."),
    ("Which month has the highest average PM2.5 across all cities? Give the month number.",
     "GROUP BY strftime('%m', date) for parameter='pm25', ORDER BY AVG(value) DESC."),
    ("How many cities have an average PM2.5 above 100?",
     "GROUP BY city with HAVING AVG(value) > 100 for parameter='pm25', then COUNT the groups."),
    ("What is the highest single daily PM2.5 value recorded?",
     "MAX(value) over measurements joined to sensors where parameter='pm25'."),
    ("What is the average PM10 across all cities?",
     "AVG(value) over measurements joined to sensors where parameter='pm10'."),
    ("Which city has the highest average PM10? Give the city name.",
     "Join measurements->sensors->locations, filter parameter='pm10', GROUP BY city, ORDER BY AVG(value) DESC."),
    ("What is the average PM2.5 during winter months (Nov, Dec, Jan)?",
     "AVG(value) for parameter='pm25' filtered to strftime('%m', date) in (11,12,1)."),
    ("How many distinct parameters are measured?",
     "COUNT(DISTINCT parameter) from sensors."),
    ("What is the average PM2.5 in Amritsar?",
     "AVG(value) joined through locations where city='Amritsar' and parameter='pm25'."),
]

REFERENCE_QUESTIONS = [q for q, _ in REFERENCES]
REFERENCE_HINTS = [h for _, h in REFERENCES]


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def _reference_matrix() -> np.ndarray:
    vecs = _model().encode(REFERENCE_QUESTIONS, normalize_embeddings=True)
    return np.asarray(vecs, dtype=np.float32)


def route(question: str) -> dict:
    q_vec = _model().encode([question], normalize_embeddings=True)[0]
    sims = _reference_matrix() @ np.asarray(q_vec, dtype=np.float32)
    best = int(np.argmax(sims))
    return {
        "index": best,
        "question": REFERENCE_QUESTIONS[best],
        "hint": REFERENCE_HINTS[best],
        "score": float(sims[best]),
    }


def warmup() -> None:
    _reference_matrix()


if __name__ == "__main__":
    warmup()
    for probe in ["worst air quality city", "average pollution in the capital"]:
        r = route(probe)
        print(f"{probe!r} -> [{r['score']:.2f}] {r['question']}")
