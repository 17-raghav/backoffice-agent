# Claims

Status: **verified now** = run on 2026-10-05, log in `results/`; **existing file** = in the original
project folders only; **unverified** = do not use.

| Claim | Value | Source | Status |
|---|---|---|---|
| Segment F1 on dataset A | 0.972 | `results/process_mining/03_evaluate_a.log` line 6 | verified now |
| Boundary F1 at +-1 / 2 / 5 s | 0.925 / 0.949 / 0.960 | same line | verified now |
| Baselines (idle gap 5 s / screen runs), segment F1 | 0.192 / 0.773 | same log, lines 3 and 5 | verified now |
| 704 segments, 15 sessions, 13 case types on dataset B | | `results/process_mining/05_analyze_b.log`; regenerated `segments.jsonl` identical to the original | verified now |
| Notes reproduced from the row alone | 108 / 110 | `results/process_mining/prototype_replay.log` (sum of the "note exact match" column) | verified now |
| Invoice decisions reproduced | 25 / 25 | same | verified now |
| Rule conflict: approvals for vendors not on the written list | 25 of 48 | same | verified now |
| Invoice matching = largest share of case time | 13.9% | `results/process_mining/analysis_b.md` | verified now |
| Lag calibration medians (nav 1.57 s, same-process click 3.44 s, process change 5.16 s) | | `results/process_mining/calibration_a.json`; `02_calibrate_a.log` | verified now |
| Cross-check vs harness console on B: 148/148 (+54/54 by hand) | | `process_mining/report.md` section 2.4 | existing file (script 06 not re-run; the 54/54 was manual) |
| Pipeline runtime | ~80 s for scripts 01-05 | `results/process_mining/0*.log` "elapsed" lines | verified now |
| SQL safety: adversarial queries blocked | 27 / 27 | `results/sql_agent/test_sql_safety.log` | verified now |
| SQL safety: all cases incl. legitimate reads | 32 / 32 + read-only backstop | same | verified now |
| Router exact / paraphrase accuracy | 14/14 / 11/14 | `results/sql_agent/run_routing.log` | verified now |
| Runaway query aborted by timeout | 5.00 s | `results/sql_agent/probe_safety_gaps.log` | verified now |
| Row-cap bypass exists | caller LIMIT returns 10,959 rows | same | verified now (a limitation, not a selling point) |
| End-to-end agent accuracy | 14/14 in `D:\Tech mix\Projects\aqi_agent\PROJECT_SUMMARY.md` | not re-run | **unverified** until the Groq run |
| Dataset size for the SQL agent: 60 locations, 10,959 measurements | | `sql_agent/eval/ground_truth.json` rebuilt from the DB (`ground_truth_rebuild.log`) | verified now |
| "Saves X hours" | - | never measured | **unverified - do not claim** |
