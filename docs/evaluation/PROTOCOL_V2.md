# Confirmatory protocol v2: transient versus progressive tilt

## Freeze and scope

This protocol is frozen before v2 data generation, model training, calibration,
or confirmatory evaluation. Its SHA-256 is recorded in
`docs/evaluation/protocol_freeze_v2.json`. The v1 protocol, freeze, scenarios,
and results remain unchanged.

The intended task is to distinguish a blast-like transient disturbance from
progressive tilt used as a subsidence proxy and from other transient/normal
conditions. Results from generated signals are simulation-only. `PROGRESSIVE_TILT`
is not evidence of mine subsidence. No simulated amplitude or parameter is a
hardware calibration.

The classifier labels are:

1. `BLAST_TRANSIENT`: a generated blast-like impulsive disturbance.
2. `PROGRESSIVE_TILT_PROXY`: sustained monotonic tilt drift.
3. `OTHER_TRANSIENT_OR_NORMAL`: non-blast transients, sensor fault, and normal
   operation. Per-scenario reporting keeps these conditions distinct even
   though they share a classifier label.
4. `UNKNOWN`: an abstention emitted only when the calibrated supervised
   classifier's maximum class probability is below the fixed 0.50 threshold.

## Signal and episode contract

Each episode represents one node for six simulated hours. The slow tilt stream
has one observation per simulated minute. A five-second, 100 Hz signal window
is generated around a transient; slow tilt observations before and after that
window are retained. The high-rate path is a simulation interface only: the
firmware sample rate and the live vibration channel's physical units have not
been verified. No interpolation is used to imply additional measured samples.
All episode clocks start at zero and use a fixed one-minute slow-signal
interval. Each model produces an inference every 15 minutes after the first
15 minutes, using only observations available by that time. Unless a row
below says otherwise, values in this protocol are assumptions.

The deterministic seed sets are disjoint:

| Purpose | Inclusive seed range | Count |
|---|---:|---:|
| Model fitting | 400000–400199 | 200 |
| Rule/probability calibration | 450000–450049 | 50 |
| Confirmatory evaluation | 500000–500029 | 30 |

Within each split, the same seed is used across scenarios and methods for
paired comparisons. A seed is never moved between splits. Training and
calibration contain only the parameter distributions specified below;
confirmatory sensitivity and shifted-parameter conditions are not used to fit,
select, or calibrate a model. For reproducible independent streams, initialize
NumPy `SeedSequence` with `[episode_seed, scenario_index, condition_index,
stream_index]`; scenario indices are assigned in the order listed in the
scenario table, condition indices in the order default, sensitivity, shifted,
and stream indices are fixed as 0 for tilt noise, 1 for acceleration noise,
2 for vibration noise, and 3 for event parameters.

## Classes, scenarios, and generators

All amplitudes, rates, intervals, and distributional forms not expressly
identified as existing simulator constants or properties of a downloaded
source are simulation assumptions. The v2 generator must record the seed,
scenario, parameter values, units, class label, and provenance for every
episode. Generated records must use `origin="simulation"` and must not be
described as sensor recordings.

### Common background and sampling assumptions

| Parameter | Frozen value | Basis |
|---|---:|---|
| Episode duration | 6 hours | Assumption; long enough to make slow-rate and per-hour outcomes meaningful in the simulated task. |
| Slow tilt interval | 60 seconds | Assumption for tractable slow-drift episodes; not a verified firmware rate. |
| Transient waveform rate | 100 Hz | Assumption for resolving sub-second transients; not a verified firmware rate. |
| Baseline tilt | `tilt_x=1.0°`, `tilt_y=0.8°` | Existing simulator defaults in `simulator/simulator/node.py`; simulator values, not site measurements. |
| Stationary tilt noise | independent zero-mean Gaussian, σ=`0.05°` per axis per slow sample | Existing `NOISE_TILT` simulator constant; not a datasheet or calibration value. |
| Stationary acceleration noise | independent zero-mean Gaussian, σ=`0.02 m/s²` per axis | Existing `NOISE_ACCEL` simulator constant; not a datasheet or calibration value. |
| Slow-trend background | Linear interpolation between slow tilt samples only for feature computation; no added high-rate tilt samples | Assumption; preserves the slow stream's stated sampling interval. |
| Vibration channel | normalized to `[0,1]` for generated high-rate feature windows | Unitless simulation variable; no conversion to the existing integer sensor field is claimed. |
| Event onset | 60 minutes after episode start | Assumption; fixed for paired event timing. |

### Blast-like transient

The blast generator produces a five-second, three-axis damped oscillatory
signal. Its main pulse is

`a_j(t) = A_j exp(-(t-t0)/tau) sin(2*pi*f_j*(t-t0)+phi_j) + noise_j(t)`

for `t >= t0`; it is zero before onset. The vibration-envelope feature uses
the absolute signal with a fixed 0.10-second moving RMS. The waveform is a
controlled parametric simulation, not a reconstruction of any particular
mine's blast or a low-cost sensor transfer function.

| Parameter | Default / training range | Basis |
|---|---:|---|
| Window length and sample rate | 5 seconds at 100 Hz | Assumptions for a short transient and resolvable envelope. |
| Main-pulse peak `A` | 0.50 normalized units; training range 0.25–0.75 | Assumption in a unitless channel; not derived from source particle velocity. |
| Dominant frequency `f` | Uniform 5–30 Hz | Assumption; covers an illustrative low-frequency transient band, not a measured mine or device range. |
| Decay constant `tau` | 0.30 seconds; training range 0.10–0.80 seconds | Assumption. `tau` is the exponential envelope time constant, not the event duration. |
| Pulse termination | At 5 seconds; no truncation before 4 tau | Fixed window assumption; the recorded tail remains in the feature window. |
| Axis amplitude ratios | x:y:z = 1.0:0.7:0.5; apply the same seeded sign to each axis | Assumption; no sensor orientation or mine geometry is available. |
| Phase `phi_j` | Independently uniform on `[0, 2*pi)` for each axis and pulse | Assumption to avoid a fixed phase preference. |
| Aftershocks | 0–2 damped pulses; each amplitude ratio 0.10–0.30; delay 0.15–1.00 seconds | Assumption representing possible repeated energy arrivals; not asserted to describe all blasts. |
| Training draw | Main peak, frequency, decay, aftershock count, ratios, delays, tilt offset, and recovery time sampled uniformly over their stated training ranges; integer aftershock count uniform on `{0,1,2}` | Fixed simulation sampling rule; not fitted to confirmatory data. |
| Event polarity | One sign per episode, sampled uniformly from `{-1,+1}` and shared across axes | Assumption; polarity is not used as class truth. |
| Transient tilt offset | Default peak `0.05°`; training range 0–`0.10°` | Assumption because no paired blast/tilt recording exists for this node. |
| Tilt-artifact recovery | Exponential return with `tau_theta=2.0 seconds`; training range 1–10 seconds | Assumption; no mount or sensor recovery measurement exists. |
| Channel noise in transient window | Same simulator acceleration noise; vibration baseline `0` with additive Gaussian σ=`0.02` normalized units | Existing acceleration noise constant plus an explicit vibration-channel assumption. |

The generated tilt artifact is signed by a seeded random direction and returns
to the pre-event tilt baseline. Blast-related vibration and acceleration
remain separate from the slow tilt series. Do not equate simulated vibration
units to the MPU6050 or SW-420 output without a verified transfer function.

### Progressive tilt proxy

The proxy starts at the fixed onset and increases monotonically through the
episode:

`theta(t) = theta0 + r * max(0, t - onset)`

where time is in hours and `r` is in degrees/hour. Both tilt axes change in a
fixed 1:0.7 ratio, matching the existing evaluation helper's axis ratio; this
is a code precedent, not a validated ground-deformation geometry. The proxy
does not recover during the episode.

| Parameter | Default / training range | Basis |
|---|---:|---|
| Drift rate `r` | `0.05°/hour`; training range `0.01–0.10°/hour` | Assumption; no mine tilt-rate record or site geometry is available. |
| Drift onset | 60 minutes | Assumption, shared event onset. |
| Direction | Positive x-axis with y-axis at 0.7 times x | Existing evaluation convention; physical direction remains unverified. |
| Added slow tilt noise | σ=`0.05°` per axis per minute | Existing simulator constant; not a measured sensor specification. |
| Vibration during drift | Background only | Assumption isolating persistent tilt evidence. |

This class is a `PROGRESSIVE_TILT_PROXY`, not ground-truth subsidence.

### Other transient and normal conditions

| Scenario | Frozen generation | Label and basis |
|---|---|---|
| `normal` (index 0) | Six-hour stationary baseline with common tilt/acceleration noise and no injected event | `OTHER_TRANSIENT_OR_NORMAL`; baseline follows simulator constants. |
| `phone_like_vibration` (index 1) | Two 0.5-second vibration bouts, five seconds apart; peak 0.35 normalized units; no persistent tilt | `OTHER_TRANSIENT_OR_NORMAL`; existing simulator/evaluation concept, with waveform values assumptions. |
| `nonblast_impulse` (index 2) | One 0.10-second damped pulse, peak 0.50 normalized units, no aftershock, no tilt offset | `OTHER_TRANSIENT_OR_NORMAL`; parameters are assumptions, not a blast model. |
| `accel_vibration_without_tilt` (index 3) | A 0.50-second vibration/acceleration burst, peak 0.50 normalized units, with unchanged tilt | `OTHER_TRANSIENT_OR_NORMAL`; preserves the existing non-tilt anomaly case as a distinct scenario. |
| `stuck_sensor` (index 4) | From onset through episode end, tilt and vibration repeat the last valid baseline sample; quality flag indicates repeated values | `OTHER_TRANSIENT_OR_NORMAL`; fault simulation, not ground movement. |
| `progressive_correlated` (index 5) | Same progressive trajectory on three simulated nodes, with independent noise and common onset/rate | `PROGRESSIVE_TILT_PROXY`; correlation structure is an assumption. |
| `blast_tilt_recovery` (index 6) | Blast-like transient plus the default recovering `0.05°` tilt artifact | `BLAST_TRANSIENT`; used to test that transient tilt is not called progressive. |
| `blast_impulse` (index 7) | Blast-like transient with zero tilt artifact | `BLAST_TRANSIENT`. |
| `progressive_single` (index 8) | Single-node progressive tilt proxy | `PROGRESSIVE_TILT_PROXY`. |

The nine scenarios above are run in the default confirmatory condition.
`condition_index` is 0 for default, 1 through 12 for the ordered sensitivity
values in the four table rows, and 13 for shifted. Scenario identity is
retained when calculating rates; `normal`, each transient type, sensor fault,
and each progressive case are never pooled for per-scenario blast
false-alarm calculations.

## Feature extraction

Features are computed on the declared streams without adding observations:

1. **Vibration peak:** maximum 0.10-second RMS envelope within the transient
   window.
2. **Vibration decay time:** least-squares slope of log envelope after its
   maximum until the envelope reaches 10% of its peak or the five-second
   window ends; report seconds and a missing-value flag if no valid decay
   segment exists.
3. **Residual tilt:** vector difference between pre-event median tilt and the
   median of the first available slow samples at least 10 minutes after the
   event. For faults or episodes without events, use the corresponding
   episode-end residual and mark the window type.
4. **Cumulative tilt:** baseline-relative vector displacement in degrees,
   computed from observed slow tilt samples; do not call it integrated
   displacement.
5. **Drift slope:** Theil–Sen slope in degrees/hour over trailing 60-minute
   windows; require at least 30 observed slow samples, otherwise mark
   unavailable.
6. **Persistence:** fraction of the last four non-overlapping 15-minute
   windows whose median baseline-relative tilt exceeds the rule threshold.
   Missing windows remain missing and are not counted as negative evidence.
7. **Additional fixed features:** accelerometer peak and RMS in the transient
   window, vibration energy, vibration-event duration, monotonicity fraction
   of slow tilt changes, and missing/repeated-sample indicators.

All feature units, missingness indicators, and window timestamps are retained.
Training normalization is fit only on training seeds.

## Models

### Rule baseline

The rule model emits one of the three named labels using the six features
above. It predicts `PROGRESSIVE_TILT_PROXY` only if all three conditions hold:
drift slope exceeds a threshold, cumulative tilt exceeds a threshold, and the
declared persistence fraction exceeds a threshold. Otherwise it predicts
`BLAST_TRANSIENT` only when vibration peak exceeds a threshold, decay time is
below a threshold, and residual tilt is within a threshold of baseline.
Remaining inputs are `OTHER_TRANSIENT_OR_NORMAL`.

Threshold candidates are fixed before data generation:

- drift slope: `0.005`, `0.01`, `0.05°/hour`;
- cumulative tilt: `0.05`, `0.10`, `0.20°`;
- persistence: `0.50`, `0.75`, `1.00`;
- vibration peak: `0.25`, `0.50`, `0.75` normalized units;
- decay time: `0.10`, `0.30`, `0.80 seconds`;
- residual-tilt limit for a transient: `0.05`, `0.10`, `0.20°`.

Select one threshold tuple on calibration seeds by maximum macro-F1; break
ties by lower blast-as-progressive rate, then lower normal false-alarm rate,
then lexicographically by the listed threshold order. No confirmatory seed or
sensitivity condition is used to select it.

### Supervised classifier

Use multinomial L2-regularized logistic regression on the fixed feature set,
with training-only standardization, `C=1.0`, `class_weight="balanced"`,
`max_iter=1000`, and fixed `random_state=0`. This lightweight model is selected
because it is inspectable and suitable for a small feature vector; no model
family search is permitted. Fit only on seeds 400000–400199.

Fit one scalar temperature on calibration seeds 450000–450049 by selecting
from `{0.50, 0.75, 1.00, 1.50, 2.00}` the value with minimum multiclass
negative log-likelihood, breaking ties toward the larger temperature. Apply
softmax to the model logits divided by this temperature. Emit `UNKNOWN` when
the largest calibrated probability is below `0.50`; otherwise emit the
largest-probability class. Report abstentions separately and do not silently
drop them from metrics.

### Legacy anomaly comparisons

Run the existing Isolation Forest and `current_system` on their supported
legacy feature contract using unchanged code/model artifacts. They are binary
anomaly methods, not event-category classifiers. Report their binary
event-versus-non-event precision/recall/F1 and confusion matrices separately.
Do not fabricate a blast/progressive class output for either method. Compare
them with class-aware methods only on the common binary event-detection
metrics, and label that comparison accordingly.

## Confirmatory evaluation and metrics

Evaluate once on seeds 500000–500029. The default condition uses only the
default parameters above. Paired comparisons use the same seed/scenario rows
for every method.

For the rule and supervised classifier, report:

- per-class precision, recall, F1, support, and a three-class confusion matrix;
- `UNKNOWN` count/rate for the supervised classifier;
- for every blast scenario, the number and rate of blast episodes classified
  as `PROGRESSIVE_TILT_PROXY`, with the scenario denominator shown;
- progressive-proxy detection delay from onset to the first qualifying
  progressive classification; report censored episodes as not detected by
  the six-hour episode end, not as zero-delay;
- false classifications of `BLAST_TRANSIENT` and
  `PROGRESSIVE_TILT_PROXY` in each named non-blast scenario;
- normal false alarms per hour, calculated from normal-only exposure as
  normal samples classified as either event class divided by observed normal
  exposure hours. No shared control rate may be copied into another scenario.

For Isolation Forest and `current_system`, report binary event-detection
metrics only as defined above. They do not receive per-class metrics or
blast-as-progressive rates because they do not produce event classes.

Use 10,000 paired, seed-level bootstrap resamples for percentile 95% confidence
intervals; bootstrap RNG seed is `600002`. Use 10,000 paired permutation
resamples for predeclared method comparisons, with RNG seed `600003`, an
add-one p-value correction, and Holm adjustment within each metric family.
Metric families are macro-F1, blast-as-progressive rate, progressive recall,
and normal false alarms/hour. Report every comparison, adjusted p-value,
interval, denominator, and loss; do not infer a class result from binary
anomaly detection. For per-class metrics, score every 15-minute inference
window. For blast-as-progressive rate, count one false classification for a
seed/scenario episode if any post-onset window is classified
`PROGRESSIVE_TILT_PROXY`; divide by the number of blast episodes in that
scenario. For normal false alarms/hour, count normal-only inference windows
classified as either event class and divide by the actual elapsed normal-only
exposure hours. The nominal six-hour episode duration is not substituted when
observations are missing.

## Sensitivity and shifted-parameter evaluation

After all model and rule choices are frozen using training and calibration
seeds, run one-factor-at-a-time sensitivity conditions on the confirmatory
seed family. Each condition changes only the named parameter from its default:

| Parameter | Frozen sweep values | Basis |
|---|---|---|
| Blast decay `tau` | `0.10`, `0.30`, `0.80 seconds` | Assumption grid; default is `0.30`. |
| Blast tilt artifact peak | `0`, `0.05`, `0.10°` | Assumption grid; default is `0.05°` for `blast_tilt_recovery`. |
| Blast vibration peak | `0.25`, `0.50`, `0.75` normalized units | Assumption grid; default is `0.50`. |
| Progressive drift rate | `0.01`, `0.05`, `0.10°/hour` | Assumption grid; default is `0.05`. |

The held-out shifted condition, never used for training or calibration, sets
blast `tau=1.20 seconds`, tilt artifact `0.15°`, vibration peak `1.00`
normalized units, progressive drift rate `0.005°/hour`, tilt noise
`σ=0.10°`, and acceleration noise `σ=0.04 m/s²`. Each is an explicit
stress-test assumption outside or at the edge of the training distribution.
No refitting, threshold adjustment, or model selection is allowed on these
conditions.

## Outputs and loss handling

Save generated artifacts only under `docs/evaluation/confirmatory_v2/`:

- `results.csv`: one row per method, scenario, noise/parameter condition, and
  seed, including predictions, labels, metrics inputs, timing, and provenance;
- `paired_tests.csv`: paired statistics, Holm-adjusted p-values, confidence
  intervals, and denominators;
- `metadata.json`: protocol hash, code revision, environment, seed ranges,
  feature/model configuration, and execution command;
- `losses.csv`: every missing, malformed, excluded, or failed episode with
  reason; zero losses must be represented explicitly;
- figures: per-class confusion matrices for each class-aware method,
  binary confusion matrices for legacy anomaly methods, three example signals,
  sensitivity curves, and blast-as-progressive rates with 95% intervals.

Do not discard failed runs, missing windows, abstentions, or unfavorable
outcomes. If any planned artifact cannot be generated, record the reason in
`losses.csv` and in the analysis. No result or hardware claim may be added
without an output traceable to these saved artifacts.
