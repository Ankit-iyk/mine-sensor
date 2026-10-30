# SUBSENSE project status

Status date: 2026-10-27 (Asia/Calcutta). Repository commit: `784a895a6c176b6922d95476a2199a6ae7205622`, branch `ai-ml-development`.

## PAST — historically recorded work

| Status | Reported work | Evidence inspected |
|---|---|---|
| VERIFIED | AI engine, Isolation Forest model, feature extraction, temporal/spatial/risk/explanation pipeline, and backend adapter exist. | `ai_engine/pipeline/inference.py`, `ai_engine/adapter.py`, model file, AI tests. |
| VERIFIED | Backend and dashboard source exist; backend test suite contains 119 collected tests. | `backend/app/`, `backend/tests/`, `dashboard/`. |
| VERIFIED | Evaluation implementation includes 23 named methods/ablations in current source, simulator and distribution-shift runs, and outputs for 12 seeds in the checked-in result file. | `ai_engine/evaluation/run_all.py`, `ai_engine/evaluation/methods.py`, `docs/evaluation/results.csv`, `docs/evaluation/results.md`. |
| VERIFIED | Tracked sensor/event CSVs are synthetic placeholders; historical file is 38,700 rows spanning about 64.5 minutes, with 16 event-log rows. | `docs/evaluation/placeholder_data/README.md` and CSV inspection recorded in `docs/evaluation/BASELINE_AUDIT.md`. |
| VERIFIED | The working tree already contained a user edit in `ai_engine/evaluation/run_all.py`; it is preserved. | `git status` and inspected diff at baseline. |

## PRESENT — verified current state

| Status | State | Evidence |
|---|---|---|
| TESTED IN PROCESS | AI-engine tests: 111 passed, exit 0. | `docs/evaluation/baseline_ai_tests.xml`. |
| TESTED IN PROCESS | Backend tests: 119 passed, 2 upstream deprecation warnings, exit 0. The sandboxed run stalled in Windows asyncio socketpair creation; it completed outside the sandbox. | `docs/evaluation/baseline_backend_tests.xml`; details in `docs/evaluation/BASELINE_AUDIT.md`. |
| EXPERIMENTALLY EVALUATED | Existing CSV contains the historical 12-seed evaluation. A separate one-seed smoke run completed with 358 rows; this is not confirmatory evidence. | `docs/evaluation/results.csv`; `docs/evaluation/baseline_artifacts/`. |
| VERIFIED | Dashboard production build passed with static page generation and TypeScript checking; browser behavior was not checked. | `docs/evaluation/baseline_test_report.json`; build output recorded in `docs/evaluation/BASELINE_AUDIT.md`. |
| VERIFIED | Existing gradual-tilt rows reproduce the historical values cited in the project prompt to rounding; no-temporal-persistence summaries match the current-system rows for that scenario. | `docs/evaluation/results.csv`, `docs/evaluation/BASELINE_AUDIT.md`. |
| VERIFIED | Available CSV duration is approximately 64.5 minutes. No matching two-hour CSV is present in tracked data. | Data audit in `docs/evaluation/BASELINE_AUDIT.md`. |
| TESTED IN PROCESS | Pre-existing user edit adds scenario winner and descriptive CI-overlap report sections in `run_all.py`; included in successful one-seed smoke outputs. | Git diff and `docs/evaluation/baseline_artifacts/results.md`. |
| TESTED IN PROCESS | Phase 1 now labels model versus mock detector output, logs missing-model fallback reason, and has targeted score-semantics and persistence-ablation tests. | `backend/app/ml/`, `ai_engine/adapter.py`, `ai_engine/tests/`, `backend/tests/`, and `docs/evaluation/phase1_test_report.json`. |
| EXPERIMENTALLY EVALUATED | Phase 2 froze the protocol and completed the 30-seed confirmatory evaluation: 710 aggregate rows, 21,300 seed rows, 1,600 paired comparisons, 16 scenarios, with protocol/output hashes checked. | `docs/evaluation/confirmatory_v1/metadata.json`, `results.csv`, `raw_metrics.csv`, `paired_tests.csv`. |
| VERIFIED | Confirmatory interpretation identifies baseline wins, narrow forest wins on selected coded anomalies, weak acceleration-only performance, and a repeated nuisance-rate metric that cannot support per-scenario nuisance claims. | `docs/evaluation/CONFIRMATORY_ANALYSIS.md`. |
| NOT RUN | Docker/MQTT/hardware end-to-end test and dashboard browser verification. | Docker command unavailable; no physical hardware verified. |

## FUTURE — remaining work

| Status | Work remaining |
|---|---|
| PARTIAL | Phase 1 traced units, feature mapping, score meaning, fallback, and ablation behavior. Remaining validation includes import-failure fallback, broader risk/explanation assertions, and full scenario-by-scenario ablation analysis. | `docs/evaluation/PHASE1_CORRECTNESS.md`. |
| PARTIAL | Phase 2 protocol and seed-level paired statistics are implemented and evaluated. Calibration at a shared false-alarm budget and sensitivity sweeps remain. The confirmatory nuisance false-alarm endpoint has a scope bug documented in the analysis. | `docs/evaluation/PHASE2_REPORT.md`, `PROTOCOL.md`, `CONFIRMATORY_ANALYSIS.md`. |
| NOT RUN | Parameter sensitivity study; in-process full API path; Docker/MQTT end-to-end path; dashboard browser status verification; manuscript build; final full reproduction from a clean checkout. | Details in phase reports and `docs/evaluation/CONFIRMATORY_ANALYSIS.md`. |
| PARTIAL | Source classification checks a configured hardware key and downgrades unauthenticated `source=hardware`, but uses a shared static key and has no signed canonical payload, nonce/replay defense, enrollment, or persistent identity. | `backend/app/ingestion/device_auth.py`, `message_handler.py`, `api/routes/telemetry.py`, `source_tracker.py`, backend tests. |
| NOT IMPLEMENTED | Reproduction script, CI workflow, full dependency strategy, benchmark/deployment documentation, authorship review, claim ledger, model card, datasheet, manuscript, and dedicated threat model. | Final status and remaining work are enumerated in `docs/FINAL_AUDIT.md`. |
| REQUIRES EXTERNAL VALIDATION | Physical sensor data, hardware identity/measurement validity, real-mine predictive performance, operational safety, independent review, and external adoption. |

## Phase gate

Phases 0–2 have test evidence in the associated reports. The backend test suite required running outside the sandbox because Windows asyncio socketpair setup was blocked inside it. The full 30-seed Phase 2 evaluation completed; analysis is simulation-scoped, and its nuisance-rate limitation is explicitly recorded. Later requested phases remain incomplete. The final evidence-based scorecard and checklist are in `docs/FINAL_AUDIT.md`; detailed baseline evidence and the machine-readable report are in `docs/evaluation/BASELINE_AUDIT.md` and `docs/evaluation/baseline_test_report.json`.
