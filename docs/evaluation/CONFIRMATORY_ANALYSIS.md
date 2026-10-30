# Confirmatory simulation analysis

Date: 2026-10-27 (Asia/Calcutta)

## Scope and provenance

This analysis reads the pre-protocol-frozen outputs in [`confirmatory_v1/`](confirmatory_v1/). The run used 30 paired seeds per noise family, 16 registered scenarios, and the frozen protocol identified by SHA-256 `2dd1833ebd31c269ea1d720538900887cccbfb44a072b6b05c339e4dff91ea58`. The run metadata records source, model, protocol, dependency, and output hashes; each output hash was checked against the file. These are simulator results only.

**Freeze caveat:** `protocol_freeze.json` was written at 17:50:44 local time and the confirmatory run outputs were generated starting at 18:23:40 (same calendar day, 2026-10-27), confirming the freeze predates the run by filesystem timestamp. However, no git commit was created before the run because the repository checkout already contained uncommitted owner changes at that point. The freeze is therefore verified only by filesystem timestamp, not by an independent commit hash. Readers should treat the protocol as *timestamp-frozen before the run* rather than as a fully preregistered protocol in the sense of a pre-committed, independently verifiable registration.

The inferential unit is the generated seed episode, not an individual timestamp. `paired_tests.csv` reports seed-paired differences, bootstrap 95% intervals, sign-flip p-values, and Holm-adjusted p-values. The sign is candidate minus reference, so a negative delay or false-alarm difference favors the candidate for those metrics. The frozen comparison uses code-fixed operating points; it does not compare methods at a shared false-alarm budget.

## What the scenario summaries show

There is no single method that leads across scenarios and outcomes. Selected simulator means from `results.csv` illustrate the tradeoffs:

| Scenario | Method | Event recall | F1 | Mean detected-event delay (s) |
|---|---|---:|---:|---:|
| Gradual tilt | baseline z-score | 1.000 | 0.964 | 6.17 |
| Gradual tilt | current system | 1.000 | 0.960 | 6.67 |
| Gradual tilt | current system + spatial | 1.000 | 0.946 | 9.20 |
| Gradual tilt | Isolation Forest | 1.000 | 0.939 | 6.23 |
| Step tilt | baseline z-score | 1.000 | 0.976 | 0.00 |
| Step tilt | current system | 1.000 | 0.891 | 0.00 |
| Step tilt | Isolation Forest | 1.000 | 0.777 | 0.00 |
| Persistent offset | current system | 1.000 | 1.000 | 0.00 |
| Regional multi-node event | baseline deviation + spatial | 1.000 | 0.973 | 4.20 |
| Regional multi-node event | current system + spatial | 1.000 | 0.916 | 10.61 |
| Correlated multi-node drift | baseline z-score | 1.000 | 0.969 | 1.46 |
| Correlated multi-node drift | current system + spatial | 1.000 | 0.959 | 1.14 |
| Vibration bursts | Isolation Forest | 1.000 | 0.937 | 0.00 |
| Vibration bursts | current system | 0.267 | 0.024 | 22.75 |
| Acceleration only | Isolation Forest | 0.300 | 0.019 | 13.44 |
| Acceleration only | current system | 0.000 | 0.000 | — |
| Combined vibration + acceleration | Isolation Forest | 1.000 | 0.931 | 0.00 |
| Combined vibration + acceleration | current system | 0.133 | 0.011 | 20.50 |

These rows establish behavior under the coded distributions, not sensor validity or generalization. Several signatures are intentionally represented in the feature inputs, and acceleration-only event recall remains low for all listed methods. Event recall saturates at 1.0 for many tilt events and therefore does not distinguish their false-alarm behavior or precision.

## Paired comparisons and ablations

In gradual tilt, `current_system_spatial - baseline_deviation_only_spatial` has mean F1 difference -0.0222 (95% paired bootstrap CI [-0.0258, -0.0187], Holm p=0.0050), with equal event recall. The spatial baseline has higher F1 and a shorter reported delay in this simulator episode. In regional multi-node events, the same comparison has F1 difference -0.0575 (CI [-0.0609, -0.0541], Holm p=0.0050), again with equal event recall. Thus these registered results do not show a consistent advantage for the proposed spatial system over a simple spatial deviation baseline.

For the temporal ablation, the full and no-temporal-persistence methods remain identical in the gradual-tilt evaluation rows. The targeted path test proves that the two inference paths can differ on a designed sequence, but these scenarios do not show an incremental temporal contribution. This is a negative result, not evidence of equivalence outside the tested simulator conditions.

The forest’s strong vibration and combined-channel results contrast with weak acceleration-only results. This supports a narrow statement that the forest detector responds to some coded feature anomalies; it does not establish broad added value. A separate operating-point-matched forest comparison was not preregistered, and the experiment does not support a general winner claim.

## Metric limitation found during analysis

`false_alarms_nuisance_per_hour_mean` is identical across all scenario/method rows for a given method/noise family. Inspection of the metric path shows the value is measured on the shared baseline-drift control episode and then carried into each scenario summary. It is not a per-scenario impulse-nuisance or phone-vibration nuisance exposure rate. Consequently:

- Do not interpret those repeated values as nuisance false-alarm rates for the scenario named in a row.
- Do not use the per-scenario nuisance false-alarm paired tests in `paired_tests.csv` as scenario-specific evidence.
- The machine outputs remain preserved as run products; this issue is not repaired by editing the generated files after results were seen.
- A corrected nuisance-exposure endpoint requires a separately versioned, post-hoc supplemental analysis or a new protocol and untouched seed families. It must be labelled accordingly.

The `false_alarms_normal_per_hour` field is separately named and uses the normal exposure path; consult raw seed rows and metric implementation before drawing conclusions about deployment rates. The current experiment also does not establish an operational false-alarm budget: parameters were not calibrated to a common budget, and generated exposure is short relative to field monitoring.

## Unsupported and unresolved outcomes

`sensor_dropout` is explicitly marked unsupported for detector comparison. The compared methods do not implement packet freshness or outage detection; empty event metrics are not successful detection. The short simulation episodes cannot establish a low long-run false-alarm rate, a field-ready minimum detectable tilt, or safety-related warning performance. Physical recordings, calibrated sensors, realistic environmental nuisance distributions, and independent mine validation are absent.

## Reproduction

The registered command was:

```powershell
python -m ai_engine.evaluation.run_all --seeds 30 --output-dir docs/evaluation/confirmatory_v1
```

Summary metrics and intervals are in `confirmatory_v1/results.csv`; per-seed records are in `confirmatory_v1/raw_metrics.csv`; paired tests are in `confirmatory_v1/paired_tests.csv`; run provenance and hashes are in `confirmatory_v1/metadata.json`; unsupported cases are in `confirmatory_v1/unsupported_conditions.csv`. Figures are generated from these run artifacts.
