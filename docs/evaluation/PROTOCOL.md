# Prospective evaluation protocol v1

**Frozen before the v1 confirmatory run.** Version identifier: SHA-256 of this file, recorded in `protocol_freeze.json` once computed. No confirmatory result may be inspected before this file and its identifier are stored.

## Scope and prior exposure

The historical evaluation has already been inspected. It used 12 seeds from the source's original test families and is **exploratory/historical**, not independent confirmation. The one-seed smoke runs in `baseline_artifacts/` and `phase1_artifacts/` are also exploratory and must not be pooled with confirmatory results. No physical sensor recordings or mine measurements are in the data inventory.

This protocol evaluates a deterministic-by-seed simulation benchmark. Conclusions apply only to the coded scenarios, assumptions, and software revision. It is not an estimate of physical mine accuracy or an operational safety guarantee.

## Questions

1. How do the current-system rules compare with fixed tilt, z-score, EWMA, CUSUM, Isolation Forest, One-Class SVM, and LOF methods on the declared simulated events?
2. Does adding the Isolation Forest to the baseline-deviation detector improve paired event outcomes or false alarms?
3. Does temporal persistence improve the event/false-alarm trade-off?
4. Does same-step multi-node corroboration help regional events and hurt isolated events?
5. How do rankings change under the declared shifted-noise process?
6. Which results depend on event severity, noise, sampling, or cross-node assumptions?
7. Which simple method is best for a particular outcome/scenario?
8. Is the stationary exposure sufficient to support any requested false-alarm bound?

## Data partitions and seeds

- Training family: seeds `100000`–`100029`, event-free rows from the configured normal and baseline-drift conditions (plus the existing shifted-normal training condition). Training seeds are separate from test seeds by construction.
- Historical ordinary test family `10000`–`10011` and shifted family `200000`–`200011` have been used in checked-in results and are excluded from confirmation.
- Confirmatory ordinary test family: seeds `300000`–`300029`.
- Confirmatory shifted-noise family: seeds `400000`–`400029`.
- A seed episode across its three simulated nodes is the unit for paired comparisons. Readings within an episode are temporally dependent and are never treated as independent replicates.
- Each method receives identical scenario, noise-model, seed, node, and event-truth rows. No confirmatory test data may be used to select features, parameters, model, or claims.
- V1 uses fixed thresholds documented in `results.md` and the evaluation source. No method receives post-hoc threshold tuning (zero tuning configurations for every method). This is a fixed-operating-point comparison, not an equalized/calibrated false-alarm-budget comparison. Claims of calibrated operation are out of scope. A future calibration protocol needs a separate event-free calibration partition and must be frozen before any such run.

## Methods and operating points

Use the current implementation constants without alteration during v1: fixed tilt threshold 0.50 degrees; z-score threshold 3; EWMA alpha 0.20 and 0.30-degree score threshold; CUSUM reference 0.08 and threshold 0.80; Isolation Forest 100 trees, contamination 0.05, seed 71; One-Class SVM RBF and nu 0.05; LOF novelty mode, contamination 0.05, maximum 35 neighbors; current adapter decision; 3 consecutive same-node alerts or same-step alerts from at least 2 nodes for spatial wrappers; baseline-deviation threshold 0.11 degrees. No operating point may be changed after confirmatory outputs are viewed.

Training for learned comparators uses the existing training partition only. Z-score statistics, StandardScaler, IF, SVM, and LOF fit on that partition. The current thresholds are fixed from source and historical development, not tuned on the v1 test seeds.

## Scenario matrix and ground truth

The target matrix contains the eight currently implemented scenarios plus eight additions, for 16 total. Each generated episode must record its scenario, noise model, seed, severity, node, event ID, truth label, onset timestamp, and duration. The origin is always `simulation`.

| Scenario | Intended controlled condition | Truth designation |
|---|---|---|
| normal | Stable simulator telemetry | No event; stationary control |
| gradual_tilt | Gradual tilt change at one node | Tilt event from generated onset |
| step_tilt | Step tilt change at one node | Tilt event |
| persistent_offset | Persistent tilt offset | Tilt event |
| vibration_bursts | Repeated vibration-only bursts | Event, with no intended tilt change |
| sensor_failure | Stuck/failure signature already implemented | Sensor-fault event; report separately from subsidence |
| multi_node_regional | Same-time regional tilt event across nodes | One event per affected node, shared onset |
| baseline_drift | Slow background tilt drift | Nuisance; not subsidence truth |
| acceleration_only | Acceleration change with tilt held nominal | Sensor disturbance; not subsidence truth |
| combined_vibration_acceleration | Co-occurring vibration and acceleration disturbance | Sensor disturbance; not subsidence truth |
| correlated_multi_node_drift | Gradual correlated change across nodes | Ground-truth event, with shared onset |
| sensor_dropout | Missing observations for a declared node interval | Data-quality fault; missing rows are not silently imputed into event positives |
| sampling_jitter | Variable timestamps around nominal cadence | No event unless paired with another declared event |
| impulse_nuisance | Short impulse/tap nuisance | Nuisance; excluded from positive subsidence event truth |
| phone_vibration_nuisance | Phone-like vibration without tilt | Nuisance; excluded from positive subsidence event truth |
| mixed_overlapping_events | Overlapping tilt and nuisance signatures | Separate truth IDs for each generated event; matching rule applied by ID |

The last eight additions are planned requirements, not implemented or evaluated until simulator code, tests, and metadata demonstrate that each is generated as specified. If a condition cannot be implemented without a misleading physical analogy, mark it unsupported and remove it from the confirmatory matrix before the first run, preserving a new protocol hash.

## Outcomes and definitions

- Primary descriptive outcomes: event-level recall, false-alarm rising edges per eligible node-hour on normal control, false-alarm rising edges per eligible node-hour on nuisance controls, and detection delay among detected events.
- Secondary: per-reading precision, recall, F1, and average precision (reported as PR-AUC), plus scenario-specific metrics.
- An event is detected if any alert for the matching event ID occurs at or after onset while that event's truth interval is active. Each distinct ID is one event. Delay is first matched alert time minus onset; misses are excluded from the delay mean and counted in event recall's denominator.
- A false alarm is a rising edge in an alert run on a non-event row. Exposure is summed node-time, with gaps larger than 1.5 times nominal sampling interval separating eligible segments. Report normal and nuisance exposure separately.
- False-alarm targets are descriptive only in v1. Zero-event rule-of-three upper bounds are only computed with stated eligible held-out hours; short exposure is reported as unsupported for low-rate claims.
- Per-reading PR-AUC is average precision over the episode's rows and is not event-level precision-recall.

## Statistical plan

- Report per-seed metrics and 95% intervals across independent seed episodes. A single seed has no inferential interval.
- Compare methods on paired per-seed differences for the same scenario and noise model. The reference for forest value is `current_system_spatial - baseline_deviation_only_spatial`; positive event-recall/F1/PR-AUC is favorable, while positive delay/false-alarm differences are unfavorable.
- Use a paired bootstrap over seeds (10,000 resamples, fixed bootstrap RNG seed 20261027) for 95% intervals of paired differences. Apply Holm correction within each declared scenario/noise family for planned method-vs-reference tests. Report adjusted p-values and raw effect sizes. Do not infer equality from overlapping intervals. Without a prespecified equivalence margin and equivalence test, label non-significant results inconclusive.
- Planned comparisons: current_system_spatial vs baseline_deviation_only_spatial; each method vs baseline_z_score for event recall and nuisance false alarms; current_system_spatial vs each temporal/spatial ablation. Keep scenario-level results visible; do not select only favorable scenarios.
- If a method cannot consume a declared input (e.g., missing observations), record the case as unsupported and retain it in the report. Do not silently drop failed seeds.

## Sensitivity and deviations

Confirmatory v1 uses severity 1.0 and the declared ordinary/shifted generator settings. A separate sensitivity study may use severity 0.5, 1.0, and 2.0, and declared noise multipliers, only if each is generated and logged consistently across methods. Sensitivity results are exploratory unless a protocol addendum is hashed before those runs. Every code-driven deviation, failed seed, or unsupported scenario must be reported.

## Reproduction and artifacts

The confirmatory command is `python -m ai_engine.evaluation.run_all --seeds 30 --output-dir docs/evaluation/confirmatory_v1` after source changes set the seed bases to the frozen confirmatory families and implement the full scenario matrix. Expected output includes protocol hash, source/config/dependency hashes, per-seed metrics, aggregate CSV/Markdown, paired differences, adjusted tests, and figures. Do not overwrite historical `docs/evaluation/results.csv`.
