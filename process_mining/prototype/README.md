# Prototype: case-queue assistant (invoice matching end-to-end)

What it is: an assistant that sits on the portal's list screen. When a case is opened it drafts the decision
(approve / hold for review), writes the note in the exact wording the team already uses, runs the reference
check against the fixed-amount vendor list, and appends the audit line when the person clicks OK.
It never submits on its own.

| file | |
|---|---|
| `definitions.json` | one entry per process: row fields, decision rules, note template, reference check. Adding a process = adding an entry |
| `assistant.py` | the engine that interprets the definitions |
| `extract_cases.py` | rebuilds real cases from the dataset-B logs (list row as shown on screen + the note the worker submitted) |
| `replay.py` | runs every real case through the assistant and compares with what the worker actually did |
| `server.py`, `static/` | local demo of the invoice screen with the assistant panel and an audit log |

```bash
python extract_cases.py   # -> data/b_cases.jsonl (704 cases, 596 with list fields, 272 with the submitted note)
python replay.py          # -> ../outputs/prototype_replay.md
python server.py          # -> http://127.0.0.1:8765/
```

Replay on real B cases (see `../outputs/prototype_replay.md`):

| process | status | submitted notes reproduced exactly | decisions agree |
|---|---|---|---|
| P6 請求書照合・承認 | decision + note + audit | 25/25 | 25/25 |
| P1 経費精算確認 | note draft, human decides | 33/34 | - |
| P2 勤怠・休暇申請確認 | note draft, human decides | 14/15 | - |
| P8 予算差異分析 | note draft, human decides | 5/5 | - |
| P12 契約管理 | note draft, human decides | 11/11 | - |
| P13 IT申請処理 | note draft, human decides | 20/20 | - |

The two misses are capture artefacts (one OCR read of the amount, one capture holding two notes).

Why the demo is a reconstructed screen: the real portals are internal test systems we cannot reach. The page
reuses the DOM grammar seen in the logs (`#pi-table` rows, `#pi-note`, `#btn-pi-ok`) and the real invoice rows
captured in dataset B, so `static/assistant.js` is written against the same structure it would meet in the
real portal (packaged as a browser extension, like the recording agent's own extension).
