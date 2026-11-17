# Stage 0 deviation report

This is a read-only audit of the implementation and frozen v1 evidence. No
simulation or evaluation was run for this report, and no existing source,
protocol, result, or paper file was edited in Stage 0. The hardware build and
wiring status below is user-provided; it was not independently inspected or
tested. File and line references identify repository evidence.

## Deviation register

| Original requirement / instruction | What the project was supposed to do | What the existing implementation or previous direction actually did | Exact deviation or mistake | Corrective action |
|---|---|---|---|---|
| Preserve the fixed objective: distinguish progressive mining-related tilt from blast impulses and other transient disturbances, rather than treating every tilt or vibration as subsidence. | Make an event-category decision grounded in temporal behavior and sensor channels, with a separate non-subsidence outcome for disturbances. | The README describes anomaly detection, risk assessment, and alerts; the AI detector returns anomaly score/state, and the evaluation labels coded rows by scenario (`README.md:3-4, 17-21`; `ai_engine/anomaly/isolation_forest.py:23-64`; `ai_engine/evaluation/datasets.py:173-196`). | The implementation and confirmatory benchmark do not implement or measure the requested blast-versus-progressive-tilt classification. No tracked history establishes when or why this objective was narrowed; that history is unverified. | Treat class discrimination as the engineering objective for a new v2 pipeline. Keep anomaly detection as a separate signal, and do not call an anomaly result a subsidence classification. |
| Detect genuine progressive tilt/subsidence behavior. | Detect a persistent or progressive ground-tilt pattern using evidence over time, without treating a short disturbance as subsidence. | The simulator has `gradual_tilt`; its code increases tilt by 0.04 degrees per reading and comments that this is about 2.4 degrees per minute at 1 Hz (`simulator/simulator/node.py:124-138`). The evaluation generator has `gradual_tilt` and `correlated_multi_node_drift` (`ai_engine/evaluation/datasets.py:20-58, 117-125, 259-263`). | There is a monotonic tilt scenario, but its rate and short episode are simulation choices, not a mine-ground measurement or validated subsidence model. The backend field named `cumulative_drift` is a moving average of recent deviation, not an integral of displacement (`backend/app/intelligence/temporal.py:86-91`). | Define and freeze v2 drift-rate, onset, duration, geometry, and noise assumptions before running it. Call the output progressive tilt unless independent evidence justifies a subsidence interpretation. |
| Distinguish blast-type impulses from progressive tilt. | Represent the blast waveform and classify it as a disturbance rather than progressive ground movement. | The production simulator creates one 16-reading high-vibration window with randomly varying values and calls it a nearby blast, machinery, or micro-seismic event; tilt stays at its baseline (`simulator/simulator/node.py:109-122`). Evaluation `vibration_bursts` uses two 16-step windows; `impulse_nuisance` sets three high vibration readings (`ai_engine/evaluation/datasets.py:217-225, 273-287`). | There is no blast-specific signal model: no measured impulse shape, physical duration, envelope decay, aftershock model, or blast label learned by a classifier. The shared nuisance-rate endpoint is copied from a baseline-drift control and cannot measure blast rejection (`docs/evaluation/CONFIRMATORY_ANALYSIS.md:50-55`; `ai_engine/evaluation/run_all.py:874, 1018`). | Use a verified blast waveform source to set the source-signal distributions, keep sensor conversion/calibration separate, and evaluate false subsidence classifications on blast exposure in a new frozen protocol. |
| Reject other transient disturbances that do not indicate subsidence. | Distinguish short tilt/acceleration/vibration artifacts from persistent progressive movement. | Evaluation includes `step_tilt`, `acceleration_only`, `combined_vibration_acceleration`, `impulse_nuisance`, and `phone_vibration_nuisance` (`ai_engine/evaluation/datasets.py:20-48, 233-296`). A step event alters tilt for a finite window; acceleration-only alters `accel_x` without tilt (`ai_engine/evaluation/datasets.py:217-238, 265-271`). | These are scripted detector scenarios, not a category classifier or validated physical disturbance models. The two nuisance-only scenarios have no positive event-recall denominator in v1, so their event recall does not establish a correct event classification. | Add separately labelled transient classes and their measurable onset/recovery features to v2. Retain all misses and false alarms; do not infer class discrimination from a binary anomaly score. |
| Include persistence/cumulative-drift versus transient-decay features, and determine whether an event-category classifier exists. | Use temporal features to distinguish slow, persistent movement from short-lived vibration or apparent tilt; output meaningful event classes. | Backend features include vibration spike count/frequency/persistence, accelerometer peak/statistics, anomalous-window persistence, and tilt trend slope (`backend/app/processing/features.py:83-131`). Temporal logic emits heuristic precursor stages and calls an average deviation `cumulative_drift` (`backend/app/intelligence/temporal.py:86-91, 116-153`). Spatial logic emits scope labels (`backend/app/intelligence/spatial.py:29-37`). | **Partial feature coverage:** persistence and slope exist, but there is no explicit vibration envelope-decay or tilt-return-to-baseline feature, and the named cumulative drift is not an integration. **No event-category classifier:** no model output distinguishes blast, progressive tilt, and other transient; the stage/scope labels are rule-based precursor/spatial labels, not those event classes. | Add windowed vibration peak/decay and residual-tilt/persistence features, then a separately evaluated class output with an explicit unknown class. |
| Select a research gap that directly serves the engineering objective. | Identify and implement transient-versus-persistent discrimination for a low-cost tilt-plus-vibration node. | The current paper describes a frozen-protocol simulation benchmark, while its Related Work section is marked for author completion (`paper/main.tex:5, 13-23, 42-43`). The benchmark compares detector outcomes, not event-category classification. | The repository evidence does not establish a literature-grounded prior gap selection or show that a blast-versus-subsidence classifier was evaluated. Any claim about what prior research did is unverified. | Use the single gap stated in `GAP_AND_PLAN.md`; complete any literature review only from sources the author has actually read. |
| State hardware assumptions accurately. | Deliver a low-cost sensor node; distinguish the user-provided build/wiring status from testing evidence. | The README documents a circuit design, says it was simulated in Cirkit Designer, and says there is no `firmware/` folder (`README.md:23-42`). The user states that hardware is built and wired per the connection diagram and has not been tested in a mine because access is unavailable. | The repository contains design and software evidence, not proof of device accuracy or mine performance. The user-provided build/wiring fact is not independently verified here. Mine testing has not occurred per the user. Bench testing status is not independently established by this audit. | Record the supplied build/mine-test status as such; obtain and document bench calibration and test evidence before making hardware-performance claims. |
| Use data that supports the target distinction, without presenting simulated values as measured. | Use real, appropriately licensed blast and slow-displacement sources where available, and mark all generated data as simulated. | The repository's bundled CSV and evaluation scenarios are described as simulated (`DATASHEET.md:5-13`; `MODEL_CARD.md:9-19`). The evaluation generator creates labels and feature rows in code (`ai_engine/evaluation/datasets.py:90-208`). | No repository evidence shows that the evaluation used mine-blast waveforms, sensor recordings of progressive subsidence, or a mine-derived ground-truth event classifier. | Use the checked candidate sources and explicit modality/transfer limits in `DATA_STRATEGY.md`. Preserve provenance and label any generated records as simulated. |
| Use a protocol and implementation whose timing matches its claims. | Evaluate persistent drift over a duration capable of exposing slow progression and represent transient signals at adequate sampling resolution. | The code sets `EPISODE_SECONDS = 120` and uses one-second evaluation steps (`ai_engine/evaluation/datasets.py:51-58, 114-116`; `DATASHEET.md:13`). The simulator's noise constants are assumptions (`simulator/simulator/node.py:32-33`). | `DATASHEET.md:9` and `docs/evaluation/SIMULATOR_PARAMETERS.md:12` say 180 steps per node, while the implementation generates 120. The one-second feature sequence cannot represent a 500 Hz blast waveform. | Resolve the duration discrepancy only in the new v2 documentation/code; add a separate high-rate signal path and a longer drift horizon. Do not edit frozen v1 files. |
| Keep repository additions and documentation proportional to the engineering objective. | Prioritize the functioning class-discrimination system and the evidence needed to evaluate it. | The repository contains multiple audit/status reports, phase reports, a technical-report paper, and result summaries (for example `docs/FINAL_AUDIT.md`, `docs/PROJECT_STATUS.md`, `docs/REVIEWER_CRITIQUE.md`, `paper/main.tex`). | File existence is verifiable; whether any addition is unnecessary or was an unnecessary previous documentation change cannot be determined from files alone and is **unverified**. No personal blame or deletion recommendation follows from this audit. | Do not remove material during Stage 0. For Stage 1, add only the v2 implementation/protocol/evidence files listed in `GAP_AND_PLAN.md`; review other documentation scope separately. |
| Keep the engineering project distinct from a paper or benchmark. | Implement a sensor pipeline that can distinguish the required event classes; use a report only to communicate evidence and limitations. | The paper describes a frozen-protocol simulation benchmark and explicitly says no recording, hardware validation, operational trial, or forecasting evaluation was performed (`paper/main.tex:13-23, 76-82`). | A paper or detector leaderboard is not the event-classification implementation. The current benchmark can report only the coded outcomes it measured. | Make the v2 classifier and end-to-end software behavior the engineering deliverable. Keep any paper claims bounded by frozen simulation evidence. |
| Keep dashboard output aligned with implemented model behavior. | Show an explicit event class only when a class-aware model actually produces it, separately from anomaly and risk state. | The active dashboard API adapter reads anomaly score and risk state (`dashboard/src/lib/api.ts:41-43, 87-112`); the map displays risk/status and trend (`dashboard/src/components/MineMap.tsx:322-341`). The separate modal labels vibration “Micro-Seismic” and shows a temporal precursor stage (`dashboard/src/components/NodeDetailModal.tsx:152-181`). | The active dashboard does not display a blast/progressive-tilt/other-transient class because the backend does not produce one. The modal's labels are not evidence of seismicity or event-category classification. | When a v2 class output exists, carry its provenance and abstention through the API and display it distinctly from risk; avoid implying that a generic vibration reading is micro-seismic. |
| Ensure code supports the actual objective and substantiate completion claims. | Preserve forest anomaly evidence while preventing it from being mistaken for a subsidence decision; verify every claimed behavior. | The adapter maps a positive forest result to `MICRO_ANOMALY` when both tilt and baseline deviations are below 0.11, otherwise `ANOMALOUS` (`ai_engine/adapter.py:26, 43-65`). Evaluation directly gates a positive on either deviation reaching 0.11 and counts only `ANOMALOUS` as an alert (`ai_engine/evaluation/methods.py:199-207`; `ai_engine/evaluation/run_all.py:1016`). The production backend still passes anomaly score/state into spatial, risk, and alert processing (`backend/app/processing/pipeline.py:150-175`; `backend/app/intelligence/risk_engine.py:80-135`; `backend/app/intelligence/alerts.py:62-103`). | The evaluation gate suppresses some non-tilt forest positives; the production risk path also uses anomaly score and other features, so it is inaccurate to claim that every low-tilt forest score is discarded from all backend risk calculations. Neither path outputs a blast-versus-subsidence category. Risk/state names such as `ZONE_WIDE_SUBSIDENCE` or `IMMINENT_COLLAPSE_WARNING` are not field validation. | Report the evaluation gate and production risk path separately. Treat hardware/field efficacy as unverified, and verify any future class behavior with tests and a newly frozen v2 evaluation. |

## Frozen v1 behavior by target category

The following are existing `confirmatory_v1/results.csv` values under the
`simulator` noise model, with the CSV's 30 requested seeds. `event_recall` is
the event-level detection measure; `recall` and `f1` are sample-level metrics.
These are simulated detector outcomes, not blast-versus-subsidence class
accuracy. CSV row references are included so the figures can be checked.

- **Progressive tilt:** `gradual_tilt` is the available single-node progressive
  tilt scenario; `correlated_multi_node_drift` is a separate multi-node drift
  scenario. Tilt/baseline deviation and trend/persistence features feed the
  compared detectors (`backend/app/processing/features.py:58-68, 120-131`).
  `baseline_z_score`, Isolation Forest, and the integrated current-system
  method are the relevant v1 detectors (`ai_engine/evaluation/methods.py:97-105,
  199-208`). The evaluation calls a qualifying positive an alert; in the
  production backend, detector output is combined with temporal and spatial
  scores into SAFE/WARNING/DANGER, and AlertEngine emits only after three
  consecutive WARNING/DANGER samples
  (`backend/app/processing/pipeline.py:150-175`;
  `backend/app/intelligence/risk_engine.py:80-135`;
  `backend/app/intelligence/alerts.py:62-103`). For `gradual_tilt`,
  `baseline_z_score` has event recall 1.0,
  recall 0.931111111111111, F1 0.9643053220379613, and mean detection delay
  6.166666666666667 seconds
  (`docs/evaluation/confirmatory_v1/results.csv:35`). `current_system` has event
  recall 1.0, recall 0.922962962962963, F1 0.9595523540376156, and delay
  6.666666666666667 seconds
  (`docs/evaluation/confirmatory_v1/results.csv:179`). For
  `correlated_multi_node_drift`, `current_system` has event recall 1.0,
  recall 0.9648148148148147, F1 0.9552756754759629, and delay
  1.0333333333333334 seconds
  (`docs/evaluation/confirmatory_v1/results.csv:188`). These measure detection
  against code labels, not actual mining-induced subsidence.
- **Blast-type impulse:** The simulator's `vibration_event` comment combines
  blast, machinery, and micro-seismic possibilities; its vibration and
  acceleration features count spikes/statistics rather than estimate a blast
  envelope (`simulator/simulator/node.py:109-122`;
  `backend/app/processing/features.py:83-103`). The evaluation's
  `vibration_bursts` contains two 16-step windows of randomized elevated
  scalar vibration, not a blast waveform
  (`ai_engine/evaluation/datasets.py:217-225, 273-279`). On
  `vibration_bursts`, `isolation_forest` has event recall 1.0, sample recall
  1.0, F1 0.9368907958019719, and delay 0 seconds
  (`docs/evaluation/confirmatory_v1/results.csv:117`).
  `current_system` has event recall 0.26666666666666666, sample recall
  0.0125, F1 0.02354978354978355, and mean delay 22.75 seconds among the
  reported detections (`docs/evaluation/confirmatory_v1/results.csv:181`).
  `current_system_spatial` has event recall 0 and F1 0
  (`docs/evaluation/confirmatory_v1/results.csv:197`). When both deviations
  are below 0.11, the adapter reports `MICRO_ANOMALY`; v1 does not count that
  state as an alert, while the production risk path still receives the
  anomaly score (`ai_engine/adapter.py:57-60`;
  `ai_engine/evaluation/run_all.py:1016`;
  `backend/app/processing/pipeline.py:150-175`). Thus the benchmark's
  integrated alert result is a coded-burst detection comparison, not evidence
  that blasts are correctly classified or rejected as subsidence.
- **Other transients:** On the finite `step_tilt` event,
  tilt deviation and slope features feed the same anomaly methods; the
  evaluation alert gate accepts tilt-deviation positives, so this event is
  counted as detected, not as a named transient class
  (`ai_engine/evaluation/datasets.py:217-238`;
  `ai_engine/evaluation/methods.py:199-208`). `current_system` has event
  recall 1.0, recall 1.0, F1 0.891478002834843, and delay 0 seconds
  (`docs/evaluation/confirmatory_v1/results.csv:180`). For `acceleration_only`,
  `isolation_forest` has event recall 0.3, recall 0.011111111111111112,
  F1 0.01889425310477942, and mean delay 13.444444444444445 seconds among
  detections (`docs/evaluation/confirmatory_v1/results.csv:122`); because it
  has no tilt/baseline deviation, `current_system` has event recall 0, recall
  0, and F1 0 under the evaluation gate
  (`ai_engine/evaluation/datasets.py:265-271`;
  `docs/evaluation/confirmatory_v1/results.csv:186`). For
  `combined_vibration_acceleration`, `isolation_forest` has event recall
  1.0, recall 1.0, F1 0.9311357091447185, and delay 0 seconds
  (`docs/evaluation/confirmatory_v1/results.csv:123`); `current_system` has event recall
  0.13333333333333333, recall 0.005555555555555556, F1
  0.010618279569892473, and delay 20.5 seconds among detections
  (`docs/evaluation/confirmatory_v1/results.csv:187`);
  `current_system_spatial` has event recall 0 and F1 0
  (`docs/evaluation/confirmatory_v1/results.csv:203`). Therefore, the forest is not uniformly successful:
  acceleration-only event recall is 0.3, not 1.0.
- **Nuisance-rate limitation:** `impulse_nuisance` and
  `phone_vibration_nuisance` rows have no positive event-recall denominator;
  their copied `false_alarms_nuisance_per_hour` values come from the shared
  baseline-drift control (`docs/evaluation/CONFIRMATORY_ANALYSIS.md:50-55`;
  `ai_engine/evaluation/run_all.py:874, 1018`). V1 did not validly measure a
  per-scenario blast false-alarm rate.

## Explicit inventory

- Blast-specific scenario or signal model: **No.** There is a generic
  finite high-vibration window; the simulator comment lists multiple possible
  causes.
  No blast waveform, decay envelope, or blast aftershock pattern is modeled.
- Features for persistence/cumulative drift versus transient decay: **Partial.**
  Window persistence, vibration spike statistics, and tilt slope exist.
  Explicit vibration decay and return-to-baseline residual features do not.
  The field named `cumulative_drift` is an average over the recent history,
  not an integrated displacement.
- Classifier that outputs blast/progressive-subsidence/other-transient
  categories: **No.** Isolation Forest reports anomaly yes/no and a score;
  temporal stages and spatial scope are heuristic state labels, not these
  event categories.

## Validation already performed for Stage 0

The requested tools ran sequentially before these reports were written:

- `tools/validate_claims.py`: passed, 8 claims.
- AI-engine test suite: 125 passed.
- Backend test suite, run from `backend\`: 130 passed, with 2 upstream
  deprecation warnings.

No new evaluation run was performed. No result file was generated. The
pre-existing worktree modifications were left in place and were not staged or
committed.
