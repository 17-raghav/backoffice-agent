import os
import re
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent.agent import ask


def extract_numbers(text: str):
    return [float(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*\.?\d*", text)]


def grade(item, answer_text: str) -> bool:
    if item["answer"] is None:
        return False
    if item["check"] == "number":
        expected = float(item["answer"])
        got = extract_numbers(answer_text)
        tol = max(abs(expected) * 0.01, 0.5)
        return any(abs(g - expected) <= tol for g in got)
    return str(item["answer"]).lower() in answer_text.lower()


def main():
    with open("eval/ground_truth.json") as f:
        questions = json.load(f)

    passed = 0
    for i, item in enumerate(questions, 1):
        try:
            answer = ask(item["q"])
        except Exception as e:
            answer = f"(agent error: {e})"
        ok = grade(item, answer)
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  Q{i}: {item['q']}")
        print(f"      expected: {item['answer']}")
        print(f"      agent:    {answer.strip()[:120]}")

    total = len(questions)
    print(f"\n{'='*50}")
    print(f"ACCURACY: {passed}/{total} = {100*passed/total:.1f}%")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
