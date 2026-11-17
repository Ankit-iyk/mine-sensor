# Stage 0 research gap and implementation plan

## One selected gap

**Transient-versus-persistent event discrimination on a low-cost tilt plus
vibration node.** The required system must distinguish progressive tilt
consistent with subsidence from blast-like impulses and other temporary
disturbances. The repository currently implements anomaly scores, threshold
gates, precursor stages, and spatial scope; it does not classify an event as
blast, progressive tilt, or another transient. The current v1 results are
binary detection outcomes on simulated, code-defined scenarios, not
event-category accuracy (`ai_engine/anomaly/isolation_forest.py:54-64`;
`ai_engine/adapter.py:43-65`; `ai_engine/evaluation/datasets.py:173-196`).

## Implementable contribution

Implement a separately versioned class-aware pipeline that adds the output
`PROGRESSIVE_TILT_PROXY`, `BLAST_IMPULSE`, `TRANSIENT_DISTURBANCE`, or
`UNKNOWN` alongside—not in place of—the existing anomaly score. A blast or
other transient must not be named or reported as progressive subsidence solely
because a vibration or acceleration feature is anomalous. A separate
disturbance warning may still be emitted. The output must be simulation-scoped
until independent sensor calibration and mine/bench evidence exist.

## Stage plan

1. **Data preparation**
   - Obtain source files only after checking record-level licenses and
     redistribution conditions. Start with the open Mount Erzberg blast
     waveform record; use the Jacobina mining-induced seismicity listing only
     for its available catalog/derived data because raw waveforms are not
     included.
   - Create a manifest with source URL, license, checksum, record/event/station
     identifiers, units, sample rate, sensor response availability, and
     simulated-versus-measured provenance.
   - Keep public particle-velocity recordings distinct from node acceleration
     and tilt. Do not convert across modalities without a documented response
     and calibration path.
   - For the progressive class, implement a parameterized simulated trajectory
     until a suitable mine tilt/displacement time series is sourced. Keep the
     label `PROGRESSIVE_TILT_PROXY`; do not claim ground-truth subsidence.
   - Split by whole blast sequence, station, and simulation seed before
     generating overlapping windows. Do not let traces/windows from the same
     source event leak across training and test.

2. **Signal processing**
   - Preserve raw source units and original sample rates in the manifest.
   - Define any baseline removal, filtering, integration/differentiation,
     antialias filtering, resampling, clipping, and missing-data behavior
     before looking at v2 outcomes.
   - Keep the vibration waveform path separate from the slow tilt path. Record
     the actual firmware/node sample rate only after it has been verified.
   - Do not claim that a 500 Hz source waveform has been mapped to this node
     until its sensor/mount transfer has been measured.

3. **Feature extraction**
   - Vibration/transient window features: peak and peak-to-peak amplitude,
     windowed energy, envelope rise and decay time, duration above a
     predeclared baseline, and recovery-to-noise interval.
   - Tilt/progression features: baseline-relative residual, robust slope,
     slope change, cumulative angle change with explicit units and sampling
     interval, monotonicity, and persistence over multiple predeclared windows.
   - Cross-channel features: time-aligned acceleration/vibration and tilt
     changes, with missing/unsynchronized data represented explicitly rather
     than imputed as a negative event.
   - Keep existing features as comparators. Do not tune the feature or noise
     ranges to favor one detector.

4. **Model selection**
   - Compare simple predeclared baselines (tilt z-score, EWMA, CUSUM, and the
     existing Isolation Forest) against a multiclass model.
   - Candidate classifier families: multinomial logistic regression as a
     transparent baseline and a small tree ensemble for nonlinear feature
     interactions. Choose hyperparameters only using training/validation
     groups and a frozen rule; never select on the confirmatory test seed
     family.
   - Report `UNKNOWN` or abstention when the feature vector is out of the
     training domain. An anomaly score is not a calibrated class probability.

5. **Training**
   - Training examples must carry explicit class labels and provenance.
     Simulated blast and progressive-proxy examples remain labelled simulated;
     public waveforms remain identified by their source and units.
   - Fit normalization and any feature selection on training data only.
     Group-split by event/source record and use fixed class weighting declared
     in the v2 protocol.
   - Save the model artifact, environment/version information, training
     manifest, random seeds, and class mapping. Do not train on v1 confirmatory
     test rows.

6. **Evaluation**
   - Freeze a new v2 protocol and a new seed family before generating any
     confirmatory results. Preserve `docs/evaluation/confirmatory_v1/`,
     `docs/evaluation/PROTOCOL.md`, and `protocol_freeze.json` byte-for-byte.
   - Report per-class precision, recall, F1, support, and a confusion matrix;
     report `UNKNOWN`/abstention counts and all losses or run failures.
   - Define blast false alarms on blast-free exposure, separately for every
     named non-blast scenario: false `BLAST_IMPULSE` labels divided by the
     actual duration of that scenario, with event and window-level counts.
     Also report false `PROGRESSIVE_TILT_PROXY` classifications on blast
     episodes. Never reuse a shared baseline-control count as a
     scenario-specific rate.
   - Report event-level time-to-detection for progressive tilt and transient
     recognition, with the denominator and censoring rule stated. Include
     confidence intervals and every frozen scenario, including unfavorable
     outcomes.
   - Run tests and the validator before and after the implementation as
     appropriate; no v2 run is authorized by this Stage 0 report.

7. **Integration**
   - Extend the backend contract to carry class, confidence/abstention, and
     provenance/version alongside the anomaly result.
   - Keep class output separate from SAFE/WARNING/DANGER risk states. Map
     `PROGRESSIVE_TILT_PROXY` to a research warning only; do not present it as
     confirmed mine subsidence. Preserve a distinct disturbance indication
     for blasts and other transients.
   - Add tests proving that a coded blast cannot become a progressive-tilt
     class solely through a high vibration score, that persistent drift is
     distinguishable in the declared simulation, and that unknown/missing
     inputs abstain safely.
   - Update model/data documentation to describe only the frozen v2 evidence
     after it exists.

## Exact files proposed for Stage 1

No file below is being changed now. This is the exact proposed initial scope;
any additional file needed after inspection requires approval before editing.

### New files

- `simulator/simulator/events_v2.py` — parameterized pulse, decay, transient
  recovery, and progressive-tilt proxy generators.
- `ai_engine/evaluation/datasets_v2.py` — group-aware v2 episode construction
  and explicit class/provenance labels.
- `ai_engine/evaluation/features_v2.py` — time-window features with units,
  sample-rate handling, and recovery/persistence definitions.
- `ai_engine/evaluation/classifier_v2.py` — class-aware model/baseline
  comparison interface and `UNKNOWN` handling.
- `ai_engine/evaluation/run_v2.py` — frozen-protocol runner and complete
  per-class, per-scenario outputs.
- `ai_engine/training/train_event_classifier_v2.py` — grouped training,
  artifact, and training-manifest creation.
- `ai_engine/tests/test_event_v2.py` — focused generator/feature/evaluation
  tests.
- `backend/app/ml/event_classifier.py` — inference wrapper for class output
  and abstention.
- `backend/tests/test_event_classifier.py` — class and safe-integration tests.
- `backend/alembic/versions/0002_event_class.py` — nullable class/provenance
  columns for existing anomaly records, with a reversible migration.
- `docs/evaluation/PROTOCOL_v2.md` — pre-run protocol, metrics, and analysis
  rules.
- `docs/evaluation/protocol_freeze_v2.json` — hashable v2 configuration;
  `protocol_freeze.json` remains untouched.
- `docs/evaluation/confirmatory_v2/source_manifest.csv` — source and
  provenance manifest.
- `docs/evaluation/confirmatory_v2/results.csv` — generated only after v2 is
  frozen and execution is approved.
- `docs/evaluation/confirmatory_v2/losses.csv` — generated failure/loss
  record, including excluded or invalid episodes.
- `docs/evaluation/confirmatory_v2/run_manifest.json` — generated command,
  environment, seed, and artifact hashes.

### Existing files to modify

- `ai_engine/adapter.py` — preserve anomaly output while adding the versioned
  class result.
- `backend/app/processing/schemas.py` — typed event-class/provenance fields.
- `backend/app/processing/features.py` — route or combine v2 time-window
  features without changing the frozen v1 generator.
- `backend/app/ml/interface.py` — define the versioned class-aware interface.
- `backend/app/ml/loader.py` — load the event classifier separately from the
  Isolation Forest.
- `backend/app/processing/pipeline.py` — pass event class and abstention
  through the in-process pipeline.
- `backend/app/intelligence/risk_engine.py` — keep class and risk-state
  semantics distinct and prevent non-subsidence classes from being described
  as subsidence.
- `backend/app/db/models.py` — persist the class output and provenance.
- `backend/app/db/repositories/anomalies.py` — store and retrieve the
  class-aware inference.
- `backend/app/api/routes/anomalies.py` — expose typed class/provenance fields
  through the existing anomaly API.
- `dashboard/src/lib/api.ts` — map the API class field into dashboard data.
- `dashboard/src/types/node.ts` — type the class and abstention state.
- `dashboard/src/components/MineMap.tsx` — display event class separately
  from risk and alert status.
- `README.md` — describe the added v2 class path and its evidence scope only
  after verified results exist.
- `MODEL_CARD.md` — record v2 training data, labels, intended use, and limits
  only after a model is trained and validated.

No paper, v1 results, v1 protocol, or frozen protocol file is in this proposed
change list.

## Stage boundary

Stage 0 is complete. No implementation, data download, model training, new
simulation, or v2 evaluation has been performed. **Stopped before Stage 1;
waiting for approval.**
