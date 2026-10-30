# Phase 0 baseline audit

Audit date: 2026-10-27 (Asia/Calcutta)

## Repository and environment

- Repository root: `C:\Users\deeks\OneDrive\Desktop\mine substences\mine-sensor`.
- Branch: `ai-ml-development`, at `784a895a6c176b6922d95476a2199a6ae7205622` (`origin/ai-ml-development`).
- The checkout began with a user-owned, uncommitted modification in `ai_engine/evaluation/run_all.py`. It was inspected and preserved; it adds report sections for scenario winners and descriptive confidence-interval overlap labels. No changes were made to that file by this audit.
- The prompt's repo-local `.venv` path does not exist. The usable environment is the parent folder's `.venv`, Python 3.14.0. Global Python 3.11.9 has no pytest. `Get-ComputerInfo` was denied; OS was obtained from Python as `Windows-11-10.0.26300-SP0`.
- Installed versions: NumPy 2.5.3, pandas 3.0.6, scikit-learn 1.9.1, pytest 9.1.1, FastAPI 0.141.1, Pydantic 2.13.5, matplotlib 3.11.2, joblib 1.6.0.
- The default sandbox TEMP location prevented pytest from creating temp directories. Setting `TEMP` and `TMP` to repository `.test-tmp` fixed this for AI-engine tests.

## Test baseline

The documented AI command is `python -m pytest ai_engine/tests -q`; it passed **111 tests** in 23.94 seconds on the corrected temp path (exit 0). Machine-readable JUnit evidence is in `baseline_ai_tests.xml`.

The backend command is `python -m pytest -q` from `backend/`. Its sandboxed run stalled because Python's Windows asyncio proactor blocked while creating a local socketpair; an isolated timed stack dump confirmed the blockage occurred in event-loop initialization, before application code. With local socket access outside the sandbox, the required backend suite passed **119 tests** with **2 upstream deprecation warnings** in 102.48 seconds (exit 0). JUnit evidence is `baseline_backend_tests.xml`.

See `baseline_test_report.json` for commands, exit statuses, environment, and evidence paths.

## Existing evaluation and reproducibility

- Checked-in `docs/evaluation/results.csv` has 358 rows and reports 12 seeds, not 30. `results.md` likewise says 12 seeds. The evaluation source defaults to 30 and accepts `--seeds`, `--real-csv`, `--event-log`, `--output-dir`, and `--refresh-reports`.
- A one-seed smoke run completed with 358 rows using `python -m ai_engine.evaluation.run_all --seeds 1 --output-dir docs/evaluation/baseline_artifacts`. Outputs are separate from the checked-in historical results. They are explicitly smoke evidence only; their one-seed intervals are not inferential results. Metadata and the result CSV hash are stored next to the outputs.
- The run code uses training seed base 100000, test base 10000, and shifted-test base 200000. It creates event-free training rows from simulator scenarios. Current code describes those ranges as disjoint; no confirmatory protocol has been frozen, and independence at the scenario/run level has not yet been established beyond the code inspection.
- Historical gradual-tilt figures are traceable to the existing results CSV (12 seeds): z-score nuisance alarms/hour 0.8696 and F1 0.9640; current system 45.2174 and 0.9580; current system with spatial correlation 6.0870 and 0.9448. The existing CSV also shows the no-temporal-persistence ablation has identical listed summary metrics to the current system for gradual tilt. This is a reported-output observation, not proof that the component is ineffective in every scenario. No attempt was made to regenerate the 12-seed historical run.
- The model artifact exists at `ai_engine/models/isolation_forest.joblib` (1,117,737 bytes; SHA-256 `5ce973c38507aa717989d5b77efc614a971fe98b9cab96e41c83a7cb55de4692`). Its provenance, feature contract, and clean-environment loading remain unaudited.

## Data inventory

The only tracked matching copies are under `docs/evaluation/placeholder_data/`. The README there identifies them as synthetic placeholders.

| File | Shape | SHA-256 | Verified coverage / contents |
|---|---:|---|---|
| `placeholder_data/sensor_data.csv` | 38,700 rows × 9 columns | `0b157dbc00fd3f3a4133b52e9db46b7a0d2521deb06edef1783f1d5c830052` | 2026-10-24 10:15:00 to 11:19:29.900 +05:30; 3,869.9 s (64.498 min); median interval 0.0999999 s, min 0.0999999, max 0.10000014; no nonpositive intervals, no gaps >0.15 s, no duplicate full rows. Columns: timestamp, tilt_x_deg, tilt_y_deg, accel_x_g, accel_y_g, accel_z_g, vibration, event_label, event_id. |
| `placeholder_data/event_log.csv` | 16 rows × 7 columns | `def5a85984d343cbc04f54c1ea128d3fa05e0535e1dd85de6e3c916e56e6cf9b` | One event per ID: 10 tilt, 5 tap, 1 phone_vibration. Columns: event_id, event_type, target_angle_deg, axis, start_timestamp, duration_s, note. |

No two-hour CSV copy was found in tracked files. The verified sensor span is about 64.5 minutes, not two hours. Timestamp span and continuous cadence agree for this file; its placeholder provenance still does not make it a physical recording.

## Services and dashboard

- Node, npm, and `dashboard/node_modules` are present. `npm run build` passed (exit 0): Next.js compiled, type-checked, generated four static pages, and finalized optimization. Next.js warned that it detected an ancestor `package-lock.json` outside the Git repository and selected an external Turbopack root. No browser validation was run.
- Docker is unavailable. No physical device or MQTT broker was verified. Docker/MQTT/hardware end-to-end validation was not run.
- No dashboard browser validation was run.

## Phase 0 disposition

**PASSED** for the local baseline: AI engine 111 passed; backend 119 passed with two warnings; one-seed smoke run completed; dashboard build passed. The earlier sandbox-specific socket stall is recorded above. Phase 1 may proceed. The uncommitted source change remains untouched.
