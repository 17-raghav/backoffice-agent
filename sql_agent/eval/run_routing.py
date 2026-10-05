import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent.router import route, REFERENCE_QUESTIONS, warmup

PARAPHRASES = [
    "How many stations are tracked in the dataset?",
    "What's the total count of daily readings?",
    "Which city is the most polluted by PM2.5?",
    "Which city has the cleanest air by PM2.5?",
    "What's the mean PM2.5 over everything?",
    "How polluted is Delhi on average for PM2.5?",
    "In which month is PM2.5 the worst?",
    "How many cities average over 100 for PM2.5?",
    "What's the worst single-day PM2.5 reading?",
    "What's the mean PM10 across the board?",
    "Which city tops the PM10 average?",
    "What's the typical PM2.5 in Nov-Jan?",
    "How many different pollutants are tracked?",
    "What's the average PM2.5 in Amritsar city?",
]


def main():
    warmup()
    n = len(REFERENCE_QUESTIONS)

    exact_ok = 0
    for i, q in enumerate(REFERENCE_QUESTIONS):
        r = route(q)
        exact_ok += r["index"] == i

    para_ok = 0
    print("Paraphrase routing:")
    for i, q in enumerate(PARAPHRASES):
        r = route(q)
        ok = r["index"] == i
        para_ok += ok
        print(f"  {'OK ' if ok else 'MISS'} [{r['score']:.2f}] {q!r} -> {r['question']!r}")

    print(f"\nExact reference routing:     {exact_ok}/{n}")
    print(f"Paraphrased question routing: {para_ok}/{n}")


if __name__ == "__main__":
    main()
