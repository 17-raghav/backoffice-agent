# From operation logs to an automation proposal: final report

## Summary

- **What the logs contain.** Back-office staff work case queues in three portals (HR, Finance, Logistics). Every case follows the same loop: open a row, look something up in a Word/Excel reference, paste a note in the team's standard wording, click OK, and often copy a line into a Notepad or Excel log.
- **Step 1.** A case is recovered from the row click → note → commit sequence. On dataset A, scored against ground truth rebuilt from `gt.jsonl`, the segmenter gets **segment F1 0.972** and **boundary F1 0.949 at ±2 s** with 15 labels for 15 processes. An idle-gap baseline gets 0.19 and screen-change runs get 0.77. On dataset B it produces **704 case segments in 15 sessions**, covering 13 case types.
- **Step 2.** **Invoice matching (P6, Finance) takes the largest share of case time (13.9%).** Its staff consult a reference document in 70% of cases. It is also the only process where the logs show a real decision: 42% of invoices are put on hold.
- **Step 3.** I built a **case-queue assistant**: one engine plus a definition per process. Invoice matching is covered end to end. Replayed on real B cases, it reproduces **25/25** logged decisions and notes. The same engine drafts notes for five more processes, matching **108/110** submitted notes overall. People still decide, and every action goes to an audit log.
- **Main risk found in the logs.** The rule staff follow for invoices differs from the written procedure. **25 of 48 approved invoices come from vendors that are not on the reference list**, and one vendor's name differs between the list and the portal. The business owner has to decide which rule is authoritative before any approval is automated.

---

## 1. What the data actually is

Before modelling I audited both datasets (`scripts/01_audit_data.py`, output in `outputs/data_audit.md`). Several findings overturn assumptions that a quick look would make.

| Finding | Evidence | Consequence |
|---|---|---|
| All 15 B sessions contain data (20,477 events). `ses_...191537` looks empty (only `desktop.ini`) on an unsynced Drive mount but really holds a 5.5 MB `events.jsonl` (1,562 events); a copy that skips it drops a whole session | `outputs/data_audit.md` | All 15 are segmented (704 segments); regenerating `segments.jsonl` on the fully downloaded data reproduces the committed file exactly |
| The 257 A executions with a null `end_ts` are **back-to-back cases of the same process** (`process_started` followed directly by `process_started`, same code, next case ID) | 257 of 257 | Their end is the next start. Dropping them, as the schema warning suggests, would delete the hardest boundaries. The evaluator rebuilds executions from `gt.jsonl` instead |
| Ground truth treats **each case as one execution**, even when the same process continues | Same 257 | Unit of work = one case (see §2.1) |
| In A, injected noise sits **inside** executions | 97 of 102 manifest `noise_blocks` | Idle or noise time between cases is not cut out (validated in §2.3) |
| One A session's GT belongs to a different run than its recording | Case numbers appear −787 s…+115 s from their GT start (alignment 0.14; healthy sessions ≈1.0) | Excluded from scoring (`054901`) |
| One A session lost its second recording chunk | 21 GT executions after the last event | GT clipped to the recorded window (`152030`) |
| The browser extension (L3) is missing in 7 A sessions and 1 B session. In one A session the mouse hook dies mid-session | `L3_events = 0`; no clicks after 04:48 in `043922` | Fallback to OS-level UI Automation clicks (L2) and to navigations |
| The screen-text capture (OCR) contains the **test harness console** (run IDs, schedules, file paths, GT log paths) in 46 A and 8 B sessions | `harness_console_in_ocr` column | Not used as input. Used once as a disclosed cross-check (§2.4). Also a privacy finding (§5) |
| All four B users work across **all three departments** and operate the portals under **three shared manager accounts** (田中 麻里 · 人事マネージャー, 佐藤 直樹 · 経理マネージャー, 高橋 健司 · 物流マネージャー) | Portal headers in OCR, per user | Portal approvals are not attributable to a person (§5) |

Everything below uses only the event logs themselves: clicks, DOM ids, UI Automation names, window titles and screen text. The harness console was never used as input.

## 2. Step 1: recovering units of work

### 2.1 Unit of work

The unit is **one business case**: open a row in a portal queue, then lookups and note, then commit, then wrap-up logging. A's ground truth defines executions this way, including consecutive cases of the same process, and it is the unit the business can count and cost. One caveat: the harness processes B's queues in short same-process runs. If B were scored per run instead of per case, per-case segments would over-split. `outputs/cases_b.csv` keeps every case with its type, so the segments can be re-aggregated if needed.

### 2.2 Method (`procmine/`)

1. **Evidence** (`evidence.py`). Each event becomes a typed item: a row click, note click or commit click; a navigation; a focus change; typing; or screen text. L3 browser clicks carry DOM selectors. Duplicate L2 UI Automation clicks only add the clicked cell's accessible name. The patterns key on the **DOM id grammar** (`{pfx}-row-…`, `{pfx}-table … tr:nth-of-type(k)`, `{pfx}-note`, `btn-{pfx}-…`), never on literal ids. A and B differ in literals (A: `#btn-la-approve`, rows keyed by case number; B: `#btn-la-ok`, rows keyed by index), and the grammar survives that change.
2. **Cases** (`cases.py`). A state machine runs idle → open → noted → committed. It also has:
   - an **L2 profile learned from the data**: which UI Automation control a row or commit click resolves to. A's commit resolves to the `main` group; B's hit-tests onto the last table row. The profile is learned from sessions where L3 and L2 saw the same click, so nothing is hard-coded;
   - **telemetry-gap fallbacks**: a navigation with no click telemetry within ±30 s becomes a case; a note typed after a commit means a row click was missed, so the case is split; a click the extension resolved as `#main` just after a navigation counts as a row open.
3. **Identity** (`identity.py`). The case type is the **prefix of the portal case number** (`INV-…`, `EXP-…`, `P1-…`, `P4-…`). The prefix is read from, in order of strength:
   1. the DOM row id, or keyboard focus on a row element;
   2. the captured list table (row *k* is the *k*-th case number);
   3. a commit toast, but only if that case type lives on that screen;
   4. the clicked cell's text;
   5. the screen slot.

   This matters for B, where one screen (HR「経費精算・給与変更」) holds two processes: expenses (P1) and payroll changes (P4). Labelling by screen alone would merge them.
4. **Boundaries** (`boundaries.py`). On A, I measured how GT boundaries sit relative to observable actions (`scripts/02_calibrate_a.py`, medians):

   | Anchor | Offset |
   |---|---|
   | Navigation to the new screen | −1.57 s |
   | Row click, same process as previous case | −3.44 s |
   | Row click after a process change | −5.16 s |
   | End of session | dashboard navigation + 8.45 s |

   Idle time between cases stays with the preceding case. For B, the lags are multiplied by B's own **tempo**, which is measurable without GT: navigation-to-row-click is 2.21 s in B against 3.05 s in A, a ratio of 0.73.

### 2.3 Results on dataset A (`outputs/eval_a.md`)

62 sessions are scored. Metrics:
- **Boundary F1:** all segment starts and ends against GT starts and ends, matched one to one within ±τ.
- **Segment F1:** one-to-one matches with IoU ≥ 0.5.
- **Labels:** V-measure and purity over 0.5 s frames.

| Method | bF1 ±1 s | bF1 ±2 s | bF1 ±5 s | Segment F1 | Label V | Purity |
|---|---|---|---|---|---|---|
| Idle gap > 5 s (baseline) | 0.071 | 0.113 | 0.279 | 0.192 | - | - |
| Screen-slot runs (baseline) | 0.375 | 0.480 | 0.567 | 0.773 | 0.909 | 0.962 |
| **procmine (full)** | **0.925** | **0.949** | **0.960** | **0.972** | **0.956** | **0.978** |
| · sessions without extension | 0.733 | 0.909 | 0.963 | 0.972 | 0.963 | 0.985 |
| Ablation: no navigation anchor | 0.720 | 0.895 | 0.960 | 0.972 | 0.939 | 0.970 |
| Ablation: L3 clicks only (no L2 fallback) | 0.900 | 0.908 | 0.915 | 0.928 | 0.957 | 0.977 |
| Ablation: cut idle gaps > 12 s | 0.852 | 0.890 | 0.903 | 0.892 | 0.970 | 0.988 |
| Ablation: no lag calibration (cut at the click) | 0.131 | 0.574 | 0.813 | 0.966 | 0.859 | 0.935 |

Reading:
- Idle gaps are nearly useless. The median gap between events is 0.05 s, and 1,313 of 1,689 consecutive executions in the manifest have zero gap between them.
- The case state machine gets the units right; calibration gets the timing right.
- Screen-only labels are equivalent on A, where one screen = one process, but not on B.

**Why I stopped there.** The remaining misses are mostly waits after a "suspended" case (44 boundaries); detecting them would mean modelling a generator artefact. Better timing no longer moves the Step-2 ranking. On B, each screen's share of time under the crude screen-run baseline is within ~1.5 points of mine, and the top two screens are the same.

What does change the ranking is **identity**. The busiest screen (HR 経費精算・給与変更, 15%) holds two processes: expenses P1 (10.1%) and payroll changes P4 (5.2%). A screen-level view ranks it first; the process view ranks invoice matching (13.9%) first.

### 2.4 Dataset B (`segments.jsonl`)

The same code and configuration run on B. Only what the method learns from B's own logs changes: tempo (0.73), L2 profile, and the screen and table catalogue.

Result: 704 segments, 13 labels, no overlaps.

**Disclosed cross-check.** For a few B sessions the harness console, including the ordered task IDs, is readable in B's own screen text. I did not use it to produce segments. I compared against it once (`scripts/06_crosscheck_b_console.py`):
- **148/148** tasks matched in type and order on the 3 runs that are complete in the capture;
- 54/54 on a fourth session checked by hand.

The first comparison exposed four errors: a click resolved as `#main`, a stale toast from another window, a missed row click, and an ambiguous screen. I fixed each with a generic rule, re-validated all four fixes on A (no change), and tuned no numeric parameter on B. Boundary timing on B cannot be validated; it relies on the A-calibrated lags scaled by tempo.

## 3. Step 2: what the work is (`outputs/analysis_b.md`)

704 cases and 168.5 case-minutes, done by 4 people (Windows accounts), each doing 9–12 of the 13 case types across all three departments. Timings come from a test environment with compressed waits, so they are compared between processes only. Median case: 11.9 s.

| Type | Process | Dept | Cases | Share of time | Median case (s) | Doc lookup | Keys/case | Recorded outcome |
|---|---|---|---|---|---|---|---|---|
| P6 | 請求書照合・承認 invoice matching | Fin | 76 | **13.9%** | 15.8 | 70% | 14.6 | 差異なし承認 58% / **差異あり要確認 42%** |
| P12 | 契約管理 contract management | Log | 60 | 11.6% | 19.8 | 92% | 14.0 | always 関連書類確認済み |
| P3 | 入社手続き照合 onboarding check | HR | 62 | 11.6% | 17.0 | 77% | 14.3 | always 照合項目すべて確認済み |
| P1 | 経費精算確認 expense claim | HR | 82 | 10.1% | 11.3 | 16% | 7.9 | always 規程内 |
| P10 | 発注管理 purchase order | Fin | 80 | 8.9% | 10.5 | 24% | 5.0 | 通常 / 緊急 12% |
| P11 | 在庫調整登録 inventory adjustment | Log | 66 | 7.7% | 10.5 | 2% | 9.9 | ± quantity |
| P2 | 勤怠・休暇申請確認 leave request | HR | 70 | 6.9% | 9.2 | 1% | 4.7 | always 問題なし承認 |
| P7 | 支払処理 payment processing | Fin | 37 | 6.4% | 20.3 | 73% | 16.0 | 4 process paths |
| P9 | 経費承認（管理職） manager expense approval | Fin | 32 | 5.6% | 19.3 | 81% | 13.0 | always 承認 |
| P4 | 給与変更登録 payroll change | HR | 48 | 5.2% | 9.8 | 12% | 6.8 | always 確認完了 |
| P13 | IT申請処理 IT request | Log | 40 | 4.9% | 10.8 | 17% | 8.8 | forwarded |
| P5 | 福利厚生申請処理 benefits | HR | 36 | 4.4% | 12.8 | 50% | 5.5 | 4 request kinds |
| P8 | 予算差異分析 budget variance | Fin | 15 | 2.7% | 21.0 | 40% | 52.4 | corrective action recorded |

**Handling patterns.** The note each worker submits is a fixed template filled from the case row. For example, `勤怠申請確認。種別：{leave type}。取得日：{date}。問題なし承認。`: 108/110 observed notes of six processes are reproduced exactly from the row alone.

Variation within a process shows up in three places:
- which reference document is opened: P6 uses the fixed-amount vendor list, a calculation sheet, or the new-vendor procedure;
- whether the result is also logged to Excel or a memo;
- in P6 and P10, the recorded outcome.

**Caveat on volume.** Each process queue holds exactly 12 cases per run (case numbers -001…-012). B's volumes therefore reflect how the test harness scheduled work, not business demand. The ranking below leans on per-case effort and decision structure as much as on volume, and volume must be re-measured on production queues before scaling.

### Prioritised candidates

| Rank | Process | Why | Form |
|---|---|---|---|
| **1** | **P6 invoice matching** | Largest share of time. Lookup-heavy (70%). The only process with an observable decision, and it is reproducible from on-screen data (25/25). The exception path is explicit (42% on hold) and a written procedure exists to check against. Standard accounts-payable automation pattern | Assistant: drafted decision + note + reference check + audit log; human confirms. **Built** |
| 2 | P1 expense claims (+P9 later) | Most cases (82). Note fully derivable (33/34). But every logged case is "within policy", so the rejection rule is unobserved | Draft notes now. Decision rule only after HR confirms per-category limits (経費規程) |
| 3 | P12 contracts, P3 onboarding | Highest per-case effort (doc lookups 92% / 77%). The judgement (reading contracts and checklists) is not observable. P3 needs detail-panel fields | Phase 2: open the right procedure document for the contract or hire type, pre-fill checklist and note; human decides |
| 4 | P10, P11, P2, P13, P4, P5 | Transcription-type, fast. Small saving per case, but cheap on the shared engine | Add definitions (detail-panel mapping needed for P4, P5, P10, P11) |
| - | P7 payments, P9 manager approvals, P8 budget variance | Money movement; approval authority; low-volume analytical judgement | Not automated. P8 is better served by a report |

## 4. Step 3: what I built (`prototype/`)

### Why invoice matching, and why this scope

P6 ranks first on both value (time share, lookups) and evidence (a decision that can be tested against logged human outcomes). All 13 processes share one screen grammar (list `{pfx}-table`, note `{pfx}-note`, button `btn-{pfx}-ok`) and one working loop. So I built **one engine with per-process definitions** (`definitions.json`), but covered only one process end to end:

- **P6 (full):** drafted decision, note, reference check, rule-conflict flag and audit line.
- **P1, P2, P8, P12, P13 (drafting only):** note drafted from the row, validated against logs; a human decides.
- **Deferred:**
  - P3, P4, P5, P10, P11: the note needs fields from the detail panel;
  - P7, P9: governance;
  - P8's decision: it is judgement.

The note-drafting definitions cost almost nothing on top of the engine, and they show the extension path works with evidence (108/110) rather than claiming it.

### Why this form

It is a browser-side assistant plus a small rules service; a person always clicks OK.

| Alternative | Why rejected |
|---|---|
| Unattended RPA or bot approving invoices | Approvals would run under the shared manager accounts (no accountable person). The rejection branches of most processes are unobserved. The practised and documented rules disagree (§5) |
| Backend/API integration | No API is visible; the portals are SPAs and the logs show only UI traffic. Worth pursuing with IT as phase 2, but it cannot be the first deliverable |
| LLM agent | Notes are deterministic templates (108/110 reproduced by templates alone). An LLM adds cost, nondeterminism and audit burden for no gain. Possible later for reading unstructured contract documents (P12) |
| Workflow tool (n8n, Power Automate) | Nothing to trigger on; the work happens inside the portal UI |

The company already deploys a browser extension to these machines (the recording agent's). The deployment channel exists, and the assistant keys on the same DOM grammar the logs show.

### What it does, and the evidence

- `replay.py` runs every real B case through the engine:

  | Process | Notes reproduced exactly | Decisions agree |
  |---|---|---|
  | P6 | 25/25 | 25/25 |
  | P1 | 33/34 | - |
  | P2 | 14/15 | - |
  | P8 | 5/5 | - |
  | P12 | 11/11 | - |
  | P13 | 20/20 | - |

  The two misses are capture artefacts.
- `server.py` runs the invoice screen, rebuilt with the logged DOM grammar and 24 real invoices from B. Open a row, and the assistant proposes approve or hold with the reason, compares the invoice to the fixed-amount list, and warns on rule conflicts. The person can override. OK appends to `audit_log.csv` with who, what, the draft, whether it was overridden, and the conflict flag.

### What manual work remains, and realistic impact

- **Removed per case:** re-typing the note (P6 averages 14.6 keystrokes per case), opening the Word reference list (70% of cases), switching apps (2.8 per case), and the memo or Excel logging line (17%).
- **Remains:** reading and confirming every case; handling every hold (42% of P6 in B); resolving rule conflicts; maintaining the vendor list.
- **Size of the impact.** I do not convert this into hours: the environment compresses waits, and B's volumes are harness-scheduled. The honest claim is that the mechanical part of each case (typing, looking up, logging) disappears and the decision remains. To size it, run a two-week pilot on one team: measure handling time with and without the assistant, override rate, hold rate, and post-approval corrections. Widen scope only if overrides stay low.

## 5. Risks, evidence and mitigations

| Risk | Evidence in the logs | Mitigation |
|---|---|---|
| **The written rule ≠ the practised rule** | P6 decisions follow the 種別 column (定常 → approve, 調整 → hold; 25/25). The written procedure (月次定額取引先一覧) says to match vendor and amount against a list: 25 of 48 approvals are for vendors not on it. The portal's 北陸部品工業株式会社 is probably the list's 北陸電子部品 under another name: its invoices cluster around the listed 420,000円. That is a master-data mismatch | Business owner picks the authoritative rule before any auto-approval. The assistant flags conflicts and starts in draft-only mode. Review overrides weekly |
| **UI drift breaks screen-level automation** | Between A and B the same buttons changed id (`btn-la-approve` → `btn-la-ok`) and rows switched from case-number ids to row indexes. The extension mis-resolved clicks (`#main`), was absent in 8 sessions and died mid-session in 1 | Key on id grammar, not literals. Contract test on page structure; the assistant disables itself if the grammar is not found. Fall back to manual |
| **No individual accountability** | All 4 users operate under the same three manager accounts | Individual accounts/SSO before automating approvals. The assistant's audit log records the real user and any override |
| **Exception branches unobserved** | P1 "規程内" 38/38, P2 "問題なし承認" 23/23, P12/P3 always "確認済み". A shows exception buttons (`btn-ob-flag`, `btn-rt-query`) and exception variants that B's screens do not | Automate decisions only where both branches are observed (P6). Elsewhere draft only; collect override data in the pilot |
| **Test-environment timings and harness-driven volumes** | Median case 11.9 s; every queue holds exactly 12 cases per run | No absolute savings claimed. Pilot measurement; re-rank with production queue volumes |
| **Monitoring itself leaks data** | Screen-text capture recorded terminal consoles (file paths, run parameters, GT file paths), employee names and amounts, even though clipboard contents are redacted | Restrict text capture to allow-listed apps; mask personal data; retention limits; privacy/works-council review before scaling |
| **Reference data maintained by hand** | The fixed-amount list is a Word document, opened in 70% of P6 cases | Move it into a governed table with an owner. The assistant reads the table, not the document |

## 6. How I allocated effort, and why

Within the seven-day window, I weighted effort by ROI rather than spreading it evenly: Step 1 is instrumentation for Step 2, not the product. The table below is the order and weight of the work, not a per-day log. I committed the repository in phases from the working history at the end, so the commit timestamps cluster rather than spread across the calendar.

| Phase | Focus | Why |
|---|---|---|
| 1 | Data audit; scorer rebuilt from `gt.jsonl` | Without a scorer every change is a guess. The audit reversed three assumptions (empty session, "drop null GT", noise between cases) |
| 2 | Baselines (idle gap, screen runs), measured and rejected; action trace | Cheap evidence of what does not work |
| 3 | Case state machine, lag calibration, L2 fallbacks, identity | Took A to segment F1 0.97. Stopped there: the ranking no longer changed |
| 4 | Transfer to B (grammar, tempo, learned L2 profile); `segments.jsonl`; disclosed cross-check | Transfer is where A-overfitting would show |
| 5 | Step 2 analysis and ranking; found P6's decision rule and the rule conflict | This is where the client's ROI is decided |
| 6 | Prototype: engine, definitions, replay against real cases, demo | Something that runs, with measured agreement |
| 7 | Report, risks, work log, repo | |

Most of the effort went to Steps 2-3, the decisions the client pays for, with enough spent on Step 1 to make the ranking robust to segmentation error, and no more.

## 7. Reproduce

See `README.md`. Everything is Python standard library; the full pipeline runs in a few minutes.
