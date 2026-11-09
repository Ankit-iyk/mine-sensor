# SUBSENSE project status

Status date: 2026-11-02 (Asia/Calcutta). Branch: `ai-ml-development`.

## PAST — historically recorded work

| Status | Reported work | Evidence inspected |
|---|---|---|
| VERIFIED | AI engine, Isolation Forest model, feature extraction, temporal/spatial/risk/explanation pipeline, and backend adapter exist. | `ai_engine/pipeline/inference.py`, `ai_engine/adapter.py`, model file, AI tests. |
| VERIFIED | Backend and dashboard source exist; backend test suite contains 119 collected tests. | `backend/app/`, `backend/tests/`, `dashboard/`. |
| VERIFIED | Evaluation implementation includes 23 named methods/ablations in current source, simulator and distribution-shift runs, and outputs for 12 seeds in the checked-in result file. | `ai_engine/evaluation/run_all.py`, `ai_engine/evaluation/methods.py`, `docs/evaluation/results.csv`, `docs/evaluation/results.md`. |
| VERIFIED | Tracked sensor/event CSVs are synthetic placeholders; `sensor_data.csv` has 38,700 rows spanning exactly 3,869.9 seconds (1 hour, 4 minutes, 29.9 seconds), with 16 event-log rows. | `docs/evaluation/placeholder_data/README.md` and CSV inspection recorded in `docs/evaluation/BASELINE_AUDIT.md`. |
| VERIFIED | The working tree already contained a user edit in `ai_engine/evaluation/run_all.py`; it is preserved. | `git status` and inspected diff at baseline. |

## PRESENT — verified current state

| Status | State | Evidence |
|---|---|---|
| TESTED IN PROCESS | AI-engine tests: 125 passed, exit 0 on the current change set. | Local verification during the 2026-11-02 update. |
| TESTED IN PROCESS | Backend tests: 124 passed, 2 upstream deprecation warnings, exit 0 on the current change set. | Local verification during the 2026-11-02 update. |
| EXPERIMENTALLY EVALUATED | Existing CSV contains the historical 12-seed evaluation. A separate one-seed smoke run completed with 358 rows; this is not confirmatory evidence. | `docs/evaluation/results.csv`; `docs/evaluation/baseline_artifacts/`. |
| VERIFIED | Dashboard production build passed with static page generation and TypeScript checking; browser behavior was not checked. | `docs/evaluation/baseline_test_report.json`; build output recorded in `docs/evaluation/BASELINE_AUDIT.md`. |
| VERIFIED | Existing gradual-tilt rows reproduce the historical values cited in the project prompt to rounding; no-temporal-persistence summaries match the current-system rows for that scenario. | `docs/evaluation/results.csv`, `docs/evaluation/BASELINE_AUDIT.md`. |
| VERIFIED | The only bundled sensor CSV has 38,700 data rows and spans exactly 3,869.9 seconds (1 hour, 4 minutes, 29.9 seconds). No two-hour CSV is present in tracked data. | Data audit in `docs/evaluation/BASELINE_AUDIT.md`. |
| TESTED IN PROCESS | Pre-existing user edit adds scenario winner and descriptive CI-overlap report sections in `run_all.py`; included in successful one-seed smoke outputs. | Git diff and `docs/evaluation/baseline_artifacts/results.md`. |
| TESTED IN PROCESS | Phase 1 now labels model versus mock detector output, logs missing-model fallback reason, and has targeted score-semantics and persistence-ablation tests. | `backend/app/ml/`, `ai_engine/adapter.py`, `ai_engine/tests/`, `backend/tests/`, and `docs/evaluation/phase1_test_report.json`. |
| EXPERIMENTALLY EVALUATED | Phase 2 froze the protocol and completed the 30-seed confirmatory evaluation: 710 aggregate rows, 21,300 seed rows, 1,600 paired comparisons, 16 scenarios, with protocol/output hashes checked. | `docs/evaluation/confirmatory_v1/metadata.json`, `results.csv`, `raw_metrics.csv`, `paired_tests.csv`. |
| VERIFIED | Confirmatory interpretation identifies baseline wins, narrow forest wins on selected coded anomalies, weak acceleration-only performance, and a repeated nuisance-rate metric that cannot support per-scenario nuisance claims. | `docs/evaluation/CONFIRMATORY_ANALYSIS.md`. |
| NOT RUN | Docker/MQTT/hardware end-to-end test and dashboard browser verification. | In-process API status flow is covered; Docker/MQTT and physical hardware are not verified. |

## FUTURE — remaining work

| Status | Work remaining |
|---|---|
| PARTIAL | Phase 1 traced units, feature mapping, score meaning, fallback, and ablation behavior. Remaining validation includes import-failure fallback, broader risk/explanation assertions, and full scenario-by-scenario ablation analysis. | `docs/evaluation/PHASE1_CORRECTNESS.md`. |
| PARTIAL | Phase 2 protocol and seed-level paired statistics are implemented and evaluated. Calibration at a shared false-alarm budget and sensitivity sweeps remain. The confirmatory nuisance false-alarm endpoint has a scope bug documented in the analysis. | `docs/evaluation/PHASE2_REPORT.md`, `PROTOCOL.md`, `CONFIRMATORY_ANALYSIS.md`. |
| PARTIAL | In-process API telemetry/status flow verified through OFFLINE → SIMULATED → LIVE → OFFLINE. Database persistence and detector processing were stubbed; Docker/MQTT end-to-end path, dashboard browser status, manuscript build, and clean-checkout reproduction remain unverified. | `backend/tests/test_telemetry_mode.py`, `scripts/run_e2e_inprocess.py`, `docs/evaluation/e2e_run.md`. |
| PARTIAL | REST/MQTT hardware ingestion verifies per-node HMAC-SHA256 payloads, timestamp freshness, and in-process nonce replay; durable replay state, enrollment, key lifecycle, and rate limits remain absent. | `backend/app/ingestion/device_auth.py`, `message_handler.py`, `api/routes/telemetry.py`, `source_tracker.py`, backend tests. |
| VERIFIED | A PowerShell reproduction script, GitHub Actions workflow, authorship note, and telemetry threat model are present. | `scripts/reproduce.ps1`, `.github/workflows/tests.yml`, `docs/AUTHORSHIP.md`, `docs/THREAT_MODEL.md`. |
| REQUIRES EXTERNAL VALIDATION | Physical sensor data, hardware identity/measurement validity, forecasting and real-mine performance, operational safety, independent review, and external adoption. |

## Phase gate

The 2026-11-02 update ran both full Python test suites successfully. The checked-in evaluation remains simulation-scoped, and its nuisance-rate limitation is explicitly recorded. Docker/MQTT and physical hardware remain unverified. The final evidence-based scorecard and checklist are in `docs/FINAL_AUDIT.md`; detailed baseline evidence and the machine-readable report are in `docs/evaluation/BASELINE_AUDIT.md` and `docs/evaluation/baseline_test_report.json`.
