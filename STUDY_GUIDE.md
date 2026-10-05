# Study guide: backoffice-agent

Numbers below are in `CLAIMS.md` with sources.

---

## 1. Concepts from zero

### 1.1 Process mining from interaction logs
Classic process mining starts from an event log where every event already has a case id. Here there
is no case id: only a stream of low-level events per recording session. So the first job is
**segmentation**: cut the stream into units of work (cases) and label each with its process.

Event layers in the data:
- **L3**: browser-extension clicks with DOM selectors (`#pi-row-INV-...`, `#btn-pi-ok`). Best evidence.
- **L2**: OS-level Windows UI Automation clicks (control type, accessible name, automation id). Present
  even when the extension is missing.
- Navigations (URL route changes), window focus changes, keystrokes, clipboard, and screen text (OCR).

### 1.2 Measuring a segmentation
- **Boundary F1 at tolerance tau**: collect all predicted starts/ends and all true starts/ends; match
  them one to one if within tau seconds; precision = matched / predicted, recall = matched / true.
  Strict tau (1-5 s) exposes late or early cuts that a lenient tau (20-30 s) hides.
- **Segment F1 at IoU >= 0.5**: a predicted segment counts if it overlaps a true one by at least half
  of their union (one-to-one).
- **V-measure / purity** over 0.5 s frames: do the labels group frames the same way the truth does?

### 1.3 The case state machine
Every case in every portal follows: open a row in the queue -> (look up a document) -> type/paste a
note -> click the commit button -> (log a line in Excel/Notepad). A state machine walks the events:
idle -> open (row click) -> noted (note field edited) -> committed (commit click). A new row click
after a commit starts a new case.

### 1.4 Why boundaries need calibration
The ground-truth start of a case is when the generator *started* the process, which is earlier than
the first visible click. On A, the median offset from GT start to the observable anchor was 1.57 s for
a navigation, 3.44 s for a row click in the same process, 5.16 s after a process change. Without these
lags, boundary F1 at +-1 s collapses from 0.925 to 0.131 (ablation). B runs faster, so the lags are
scaled by B's own measured tempo (navigation-to-row-click 2.21 s vs 3.05 s on A, ratio 0.73).

### 1.5 Identity: why the case number, not the screen
One HR screen hosts two processes (expenses P1 and payroll changes P4). A screen label merges them and
puts that screen first in the ranking; the case-number prefix separates them and invoice matching
comes first. Sources in order of strength: DOM row id / keyboard focus, captured table row, toast,
clicked cell text, screen.

### 1.6 From analysis to an automation form
For each process: time share, median case time, document lookups, keystrokes, recorded outcomes.
Invoice matching (P6) had the largest time share (13.9%), lookups in 70% of cases, and the only real
observed decision (approve vs hold), which turned out to follow one column (定常 regular -> approve,
調整 adjustment -> hold; 25/25). The written procedure disagrees for 25 of 48 approvals, so automating
the approval itself would encode an unagreed rule.

### 1.7 Tool-using LLM agents
An agent = an LLM in a loop that can call tools. It writes a tool call (here: an SQL string), the
runtime executes it and returns text, the model reads it and either answers or calls again. Risks:
destructive calls, runaway calls, prompt injection, wrong answers stated confidently. Mitigations go
in the tool, not the prompt: the tool must be safe whatever the model sends.

### 1.8 Embedding router
Sentence embeddings map a question to a 384-dimensional vector (`all-MiniLM-L6-v2`). Cosine similarity
to 14 reference questions picks the nearest; its hand-written SQL hint is added to the prompt. It is a
cheap retrieval step that steers the model to the right joins. Weakness: embeddings handle negation
and antonyms poorly ("cleanest" matched "highest PM2.5").

---

## 2. Code walkthrough in execution order

### Part A (`process_mining/`)
1. `procmine/io.py` - finds `dataset_a/`, `dataset_b/` (env `PROCMINE_DATA`); merges a session's chunks
   into one time-ordered event list, de-duplicating by event id.
2. `process_mining/scripts/01_audit_data.py` - per-session counts, layers present (L3/L2), GT checks, harness console
   detection in screen text -> `data_audit.md`.
3. `procmine/evaluate.py` - rebuilds GT executions from `gt.jsonl` (each `process_started` /
   `process_resumed` opens one, the next boundary event closes it), computes the metrics above.
4. `procmine/evidence.py` - raw events -> typed evidence (row / note / commit clicks, navigation,
   edit, screen text) using regexes from `config/default.json` that key on the DOM id grammar.
5. `procmine/cases.py` - learns the L2 click profile from sessions where L2 and L3 saw the same click;
   runs the state machine; adds navigation fallbacks only inside telemetry gaps; merges re-opened cases.
6. `procmine/identity.py` - attaches case numbers and builds a catalogue of which case types live on
   which screen.
7. `procmine/boundaries.py` - places start/end with calibrated lags scaled by tempo; idle time stays
   with the preceding case.
8. `procmine/pipeline.py` - glue: evidence -> cases -> identity -> type resolution -> boundaries;
   drops segments shorter than 1 s; clips to the recording.
9. `process_mining/scripts/02_calibrate_a.py` - measures the lag medians on A.
10. `process_mining/scripts/03_evaluate_a.py` - baselines, full method, subsets, ablations on A.
11. `process_mining/scripts/04_segment_b.py` - runs the same pipeline on B -> `segments.jsonl`, `cases_b.csv`.
12. `process_mining/scripts/05_analyze_b.py` - per-process tables and the handling patterns.
13. `prototype/extract_cases.py` -> `prototype/data/b_cases.jsonl` (rows and visible notes);
    `prototype/assistant.py` + `definitions.json` (row regex, ordered decision rules, note template,
    reference check); `prototype/replay.py` compares drafts with what workers actually submitted;
    `prototype/server.py` serves a demo portal page plus the assistant, writing an audit log.

### Part B (`sql_agent/`)
1. `tools/sql_tool.py` - `_validate` (empty, `;`, SELECT/WITH allowlist, keyword denylist),
   `_enforce_limit`, `run_sql` (read-only connection, progress-handler timeout, result as text),
   `get_schema`.
2. `agent/router.py` - loads the embedding model once, caches the reference matrix, `route()` returns
   the best match and score.
3. `agent/agent.py` - wraps `run_sql` as a LangChain tool, builds the system prompt with the live
   schema, creates the agent with Llama 3.3 70B on Groq, `ask()` adds the router hint.
4. `api.py` - FastAPI `POST /ask`, `GET /health`.
5. `eval/ground_truth.py` (answer key from reference SQL), `eval/run_eval.py` (end to end, numeric
   answers within 1% or 0.5, labels by substring), `eval/run_routing.py`, `eval/test_sql_safety.py`,
   `eval/probe_safety_gaps.py` (added for this repo).

---

## 3. Why this, not that

| Choice | Why | Alternative |
|---|---|---|
| Scorer before segmenter | every later change is measured, not guessed | eyeballing segments |
| Strict boundary tolerances | a lenient +-20 s scorer had flattered a weaker method (0.86) | +-20-30 s |
| State machine over the work loop | the loop is the same in all portals; explainable | clustering / HMM on event features: harder to debug, needs more data |
| Do not cut idle gaps | noise blocks lie inside cases (97/102); cutting lowered segment F1 to 0.892 | idle-gap cut |
| Key on DOM id grammar, not literals | literals changed between A and B (`btn-la-approve` -> `btn-la-ok`) | per-dataset rules |
| Not using the leaked harness console | it is partial ground truth; using it would be cheating | used once as a disclosed cross-check |
| Templates, not an LLM, for notes | 108/110 notes are fixed templates; LLM adds cost and nondeterminism | LLM drafting |
| Human confirms every case | shared manager accounts, unobserved exception branches, rule conflict | unattended RPA |
| One SQL tool, read-only connection | smallest attack surface; the DB enforces read-only even if regexes fail | many narrow tools or an ORM API: safer but less flexible |
| Router hint, not hard templates | keeps the model flexible while steering joins | template-only answers: brittle for new questions |
| temperature 0 | reproducible SQL | sampling |

---

## 4. What failed or was dropped (from `process_mining/work_log.md` and today's probes)

- Idle-gap segmentation: segment F1 0.19 at 5 s; consecutive cases are butt-joined.
- A first method scored with a lenient start-only metric looked like 0.86; under the strict scorer its
  boundary F1 at +-1 s was 0.35.
- Cutting idle gaps as noise: segment F1 0.93 -> 0.90.
- "Last navigation before the row click" and "first navigation after the previous case" anchors both
  lowered +-1 s F1; final rule: first navigation after the previous case within 6 s of the row click.
- Unrestricted navigation fallback created phantom 0.3 s cases; restricted to telemetry gaps.
- One A session's GT belonged to another run (excluded); one lost its second chunk (GT clipped).
- Rejected forms: unattended RPA, API integration, LLM agent, workflow tools (reasons in report §4).
- SQL agent: today's probes found a row-cap bypass and a keyword false positive (section "Known gaps"
  in README).

---

## 5. Likely interview questions

1. **What was the input?** Desktop/browser interaction logs from recorded work sessions in mock
   portals: clicks, keystrokes, navigations, focus, screen text. Dataset A with ground truth, B without.
2. **What is a "unit of work" here and why?** One business case (open row -> note -> commit). That is
   how A's ground truth splits back-to-back cases, and it is what the business counts.
3. **How did you evaluate?** Rebuilt executions from `gt.jsonl`; boundary F1 at +-1/2/5 s, segment F1
   at IoU 0.5, frame-level V-measure.
4. **Your numbers?** Segment F1 0.972; boundary F1 0.925 / 0.949 / 0.960 at +-1/2/5 s on A. Baselines
   0.19 (idle gaps) and 0.77 (screen runs).
5. **Why not a learned model?** 63 labelled sessions, a very regular work loop, and a need to transfer
   to a different UI (B). A transparent state machine with calibrated lags transferred; ablations show
   which part matters.
6. **How do you know it transfers to B without labels?** Same code, lags scaled by B's measured tempo;
   a disclosed one-off cross-check against a leaked harness console matched 148/148 tasks in type and
   order (original work, not re-run). Boundary timing on B is not validated.
7. **What does the calibration ablation show?** Cutting at the click instead of applying lags gives
   +-1 s boundary F1 0.131 vs 0.925; units are right, timing is wrong.
8. **What did the analysis find?** Invoice matching takes the largest time share (13.9%), needs lookups
   in 70% of cases, and is the only process with an observable decision; the decision follows the
   invoice kind column 25/25.
9. **Why not automate the approval?** The written rule disagrees with practice for 25 of 48 approvals,
   approvals run under shared accounts, and exception paths are unobserved. A human confirms.
10. **What does the prototype do?** Parses the case row, drafts the note in the team's exact wording,
    proposes approve/hold with the reason, checks the reference list, flags conflicts, logs to an audit
    file. Replay: 108/110 notes, 25/25 decisions.
11. **Why no LLM in Part A?** Notes are templates; deterministic fill-in reproduces 108/110. An LLM
    adds cost, nondeterminism and audit burden.
12. **Then why Part B?** Open-ended analytical questions cannot be templated; that is where an LLM with
    a tool helps, and the engineering problem becomes safety.
13. **List the SQL defences.** Read-only connection; single statement; SELECT/WITH allowlist; keyword
    denylist; auto LIMIT; 5 s timeout; errors as text; one tool only; API input checks.
14. **Which defence matters most?** `mode=ro`. The regexes are a first filter with known gaps; the
    read-only connection makes a write impossible even if they fail.
15. **How did you test the defences?** 27 adversarial queries (writes, DDL, stacking, case tricks,
    CTE-hidden DELETE, comment evasion) all blocked; 5 legitimate reads allowed; plus probes for
    timeouts and row caps.
16. **What gaps did you find?** A caller-supplied LIMIT or a LIMIT inside a subquery bypasses the row
    cap; the denylist rejects legitimate strings containing words like "Replace".
17. **How would you fix the row cap?** Always wrap: `SELECT * FROM (<query>) LIMIT 100`, and tokenize
    SQL instead of regex matching.
18. **What does the router do and how good is it?** Nearest reference question by embedding cosine;
    14/14 on the references, 11/14 on paraphrases. Misses: negation ("cleanest"), "overall" vs a
    city-specific template, "pollutants" vs "parameters".
19. **Is the end-to-end eval fair?** It is in-distribution (the 14 eval questions are the router's
    references). A fair eval needs held-out questions.
20. **How do you grade free-text answers?** Extract numbers and accept within 1% (min 0.5); labels by
    case-insensitive substring. Simple and can be fooled by an answer listing many numbers.
21. **Prompt injection?** Data values could contain instructions; the model only has a read-only SQL
    tool, so the worst case is a wrong answer, not damage.
22. **How did you handle personal data?** The logs captured employee names and console text; the
    report recommends allow-listing captured apps and masking. In this repo, per-session outputs that
    contain machine/user names are not committed; hostnames are redacted in copied logs.
23. **Hard follow-up: B's volumes are fixed at 12 per queue. Does your ranking still hold?** Volume is a
    harness artefact, so the ranking leans on per-case effort and decision structure; it must be
    re-measured on production queues.
24. **Hard follow-up: what would a pilot measure?** Handling time with/without the assistant,
    override rate, hold rate, post-approval corrections over two weeks on one team.
25. **Hard follow-up: you used AI tools heavily in Part A. What did you do yourself?** Chose the
    unit of work, the strict scorer, what to exclude (the leaked console), when to stop, and the
    automation form; verified the numbers by re-running. (Answer this in your own words.)
