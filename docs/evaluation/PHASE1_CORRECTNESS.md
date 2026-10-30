# Phase 1 correctness audit

Date: 2026-10-27 (Asia/Calcutta)

## Decision path inspected

### AI-engine entry point

`ai_engine.pipeline.inference.analyze_telemetry()` obtains `node_id` and `zone_id`, validates required fields and coarse ranges, normalizes tilt and vibration into additional fields, extracts rolling features, updates a per-node fingerprint, scores the Isolation Forest, updates process-local anomalous-node membership, classifies per-node temporal state, computes spatial correlation, calculates a weighted risk score, updates trajectory history, and builds an explanation. The result contains each intermediate stage.

The AI-engine pipeline's temporal classification is not an input to `calculate_risk()`; it currently contributes to explanation text. The spatial membership set is process-local and does not expire nodes by timestamp, so stale anomaly membership can affect later readings until overwritten. These are inspected behavior and a residual correctness concern, not validated operational behavior.

### Backend path

The backend validates the Pydantic `TelemetryReading`, filters tilt, stores a rolling window, normalizes raw 10-bit vibration by 1023, extracts backend features, updates fingerprint and temporal precursor state, updates spatial state, evaluates composite risk with anomaly/temporal/spatial inputs, emits alerts, and optionally persists results. REST ingestion checks a configured hardware key when payload `source` says `hardware`; source trust itself remains an outstanding Phase 5 security audit.

The backend `FeatureVector` includes acceleration magnitude in m/s². The Isolation Forest's declared 11-column `FEATURE_COLUMNS` does not include acceleration features, so acceleration does not enter this model through the adapter. Training and inference both use the same 11-column order via `train_from_backend.py` and `AIEngineDetector._map_features()`. The AI-only telemetry validator's acceleration range is expressed as approximately ±2 (consistent with g units in its generator), while backend ingestion schema uses m/s²; those are separate input contracts and must not be conflated.

Vibration path: backend payloads use integer ADC counts 0–1023; backend processing maps them to 0–1; training through `train_from_backend.py` and adapter inference both consume the normalized backend vibration features with scale factor 1. The AI-only entry point accepts vibration 0–1. Its `normalize()` additionally creates `vibration_norm` using a 0–100 scale, but `extract_features()` uses the original vibration field. The direct AI training helper and backend training path are distinct; the tracked detector's documented training source is the backend path.

## Correctness changes

1. **Observable detector fallback:** model-load failure already logged and fell back to `MockAnomalyDetector`, but missing paths had no explicit reason and returned predictions could be ambiguous if `ml_model_version` was configured with a production-looking label. The loader now logs the missing-artifact reason. The common inference output adds `detector_mode`; the model adapter says `model`, and the mock detector says `mock`. A backend test sets a production-like version string while forcing a missing artifact and verifies the mode remains `mock`.
2. **Score semantics test:** scikit-learn's `IsolationForest.decision_function()` is higher for inliers and lower for outliers; `predict()` labels the outlier `-1`. The adapter maps `clamp(0.5 - raw_score, 0, 1)`, which is monotone in the needed direction. This is an uncalibrated anomaly score, not a probability. Tests use a known inlier and an extreme outlier and check raw-score ordering; a separate adapter test verifies synthetic raw values 0.4 and -0.4 map to 0.1 and 0.9 (within floating-point tolerance).
3. **Temporal-persistence ablation test:** the evaluation wrapper requires three consecutive same-node alerts unless two same-step nodes corroborate. A controlled one-row sequence is suppressed by the full wrapper and emitted by `no_temporal_persistence`, proving the ablation disables the persistence requirement. Existing historical result summaries for gradual tilt happen to match some non-spatial summaries; that observation does not invalidate the path-level test and does not establish the ablation's behavior across all scenarios.

## Remaining issues found

- AI-engine input validation checks presence, range comparisons, and a minimally sized timestamp string, but does not parse the timestamp or consistently coerce/reject nonnumeric values with a stable validation error.
- `ai_engine.preprocessing.normalization._scale()` does not clip normalized values. Upstream range validation limits the intended inputs, but malformed numeric types remain a concern.
- The AI-only per-node global state is not time-windowed/expired and is not thread-safe. The backend has separate temporal/spatial engines; this audit did not equate their semantics.
- Model-score transformation is monotonic and bounded but not statistically calibrated. No calibration or threshold validation against independent physical data exists.
- Fallback is explicit in returned inference mode and logs for absent/model-load errors. A failure importing `ai_engine.adapter` at backend loader module-import time is not covered by the fallback try/except and can prevent backend ML loader import; this remains unresolved.
- The model file loads through the current in-process loader as part of the baseline backend suite, but clean-environment compatibility and model provenance beyond the documented training script were not independently established.
- No unit or deployment behavior is established for physical hardware. No real sensor measurements were used.

## Verification

- Full AI-engine suite: 113 passed, exit 0; JUnit: `phase1_ai_tests.xml`.
- Full backend suite: 120 passed, 2 upstream deprecation warnings, exit 0; JUnit: `phase1_backend_tests.xml`.
- Evaluation smoke run with one seed: output in `phase1_artifacts/`; smoke-only, not confirmatory.
- Initial phase-1 AI run exposed an overly exact floating-point assertion in a new test (112 passed, 1 failed). It was changed to `pytest.approx`; focused test (4 passed) and final full suite then passed. The smoke run was executed after the final code state.
