# Simulator parameter inventory and simulation-to-real gap

Audit date: 2026-10-27. This inventory describes code values, not validated sensor specifications. Every value below is a simulation assumption unless a source is explicitly supplied; no MPU6050 manufacturer range is used to justify the evaluation noise model.

## Evaluation episode generator

The registered experiments use `ai_engine/evaluation/datasets.py` (`generate_episode`, `_generate_episode`, and scenario helpers), which in turn uses `simulator/simulator/node.py` and `NodeBaseline`.

| Parameter | Current value / unit | Source | Meaning and evidence class |
|---|---:|---|---|
| Evaluation node count | 3 nodes (`N01`–`N03`) | `datasets.py` | Controlled benchmark topology; ASSUMPTION |
| Episode length | 180 steps per node | `datasets.py` | Simulated exposure duration; not field duration |
| Nominal interval | 1.0 s | `datasets.py` | Nominal cadence; ASSUMPTION |
| Tilt noise | Gaussian σ=0.05° | `simulator/simulator/node.py` (`NOISE_TILT`) | Independent additive noise in the simulator; not measured device noise |
| Acceleration noise | Gaussian σ=0.02 m/s² (code constant; feature generator may add channel disturbance) | `node.py` (`NOISE_ACCEL`); `datasets.py` | Simulation assumption; not datasheet accuracy or calibrated noise |
| Baseline tilt | 1.0° x, 0.8° y for evaluation nodes | `datasets.py` | Fixed synthetic starting orientation; ASSUMPTION |
| Vibration background pulse | probability 0.02 per reading; integer background/pulse generation in `_noise_vibration` | `node.py` | Synthetic nuisance distribution; not measured vibration spectrum |
| Shifted tilt noise | added Gaussian σ=0.12° per axis | `datasets.py` (`_apply_shifted_noise`) | Declared distribution shift; ASSUMPTION |
| Shifted acceleration noise | added Gaussian σ=0.06 m/s² per axis | `datasets.py` | Declared distribution shift; ASSUMPTION |
| Shifted cadence | uniform 0.8–1.2 s | `datasets.py` | Sampling shift; ASSUMPTION |
| Sampling-jitter cadence | uniform 0.5–1.5 s | `datasets.py` | Controlled jitter scenario; ASSUMPTION |
| Dropout | node N01 omits steps 50–64, recovery at 65 | `datasets.py` | Missing rows and recorded gap; detectors have no freshness alarm, so outcome is unsupported |
| Gradual tilt | event at step 30; configured ramp and severity in scenario helper | `datasets.py` | Programmed event shape, not a geological process model |
| Step tilt | onset and size in `_apply_scenario` | `datasets.py` | Programmed event; ASSUMPTION |
| Persistent offset | fixed offset in scenario helper | `datasets.py` | Programmed event; ASSUMPTION |
| Correlated drift | same-time multi-node drift | `datasets.py` | Dependence is stipulated to test spatial behavior; not estimated from mine data |
| Impulse / phone-like vibration / mixed events | scripted channel changes in scenario helpers | `datasets.py` | Synthetic nuisance signatures; no physical vibration recordings |

The above episode settings and code locations are traceable, but the currently generated `confirmatory_v1` run has severity 1.0 only. A severity/noise sensitivity sweep has **NOT RUN** and there is no evidence for a minimum detectable physical tilt. Simulator `SensorNode` random functions use Python's process-global `random` in parts of the original simulator; the evaluation wrapper's seeding and deterministic tests are documented in `PHASE2_REPORT.md` and `test_evaluation_datasets.py`.

## Production simulator is a separate path

`simulator/simulator/main.py` defines six zone nodes with baselines ranging from 0.50° to 1.40° (x) and 0.55° to 1.20° (y), and a default publication interval set by CLI/configuration. Its `SensorNode` uses the noise constants above and scripted scenarios. These production-demo defaults must not be conflated with the 3-node, 180-step evaluation generator.

## Simulation-to-real gap

Current models do not establish real sensor behavior. Unmodeled or unverified effects include sensor-specific bias, temperature drift, axis cross-coupling, mounting compliance, mechanical transfer functions, vibration spectra and aliasing, ADC quantization, MPU6050 scale/offset calibration, gravity/orientation errors, saturation, clock skew, packet duplication/reordering, correlated packet loss, radio interference, long-run baseline drift, sensor aging, and geological process dynamics. Environmental and mine operational nuisance distributions were not measured. Multi-node dependence is scripted. Simulator sensitivity cannot close these gaps.

## Required sensitivity protocol before a follow-up run

Predeclare independent severity, noise, drift, and dependence settings; retain all methods on identical scenario/noise/seed episodes; reserve untouched seeds; preserve the existing v1 artifacts; record an addendum hash before execution; report all settings and failures. The 30-seed confirmatory v1 is unchanged. Since its results have already been inspected, any new sweep is exploratory/post-hoc unless a genuinely untouched design and seed family are frozen first.
