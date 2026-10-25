# SYNTHETIC PLACEHOLDER DATA — evaluation only

These outputs use synthetic placeholder data only. They are not measured recordings and are not hardware-validated. Models were fit only on the first 30 minutes of stationary samples, thresholds were calibrated on the following 15 minutes of stationary samples, and metrics use the remaining held-out period. The backend feature pipeline then processed the ordered input stream. This run exists to exercise the CSV loader and evaluation workflow.

- Sensor CSV: `docs\evaluation\placeholder_data\sensor_data.csv`
- Event log: `docs\evaluation\placeholder_data\event_log.csv`
- Training features after 1-in-10 subsampling: 1800
- Calibration feature rows: 9000
- Held-out stationary duration: 0.311111 hours
- Acceleration units: input `_g` columns converted to m/s² (backend schema units).
- Vibration values in [0, 1] are treated as normalized and converted to 10-bit ADC counts.
- Event recall requires all logged events at that angle to be detected; false alarms are measured on held-out stationary samples only.

## Tilt event results

| target angle | method | events detected / total | event recall | detection delay (s) | false alarms/hour | PR-AUC |
|---:|---|---:|---:|---:|---:|---:|
| 0.25° | fixed_tilt_threshold | 0/3 | 0.000 | n/a | 9.643 | 0.102 |
| 0.25° | baseline_z_score | 3/3 | 1.000 | 1.067 | 93.214 | 0.102 |
| 0.25° | ewma | 0/3 | 0.000 | n/a | 22.500 | 0.085 |
| 0.25° | cusum | 3/3 | 1.000 | 3.200 | 51.429 | 0.015 |
| 0.25° | isolation_forest | 3/3 | 1.000 | 0.167 | 1231.071 | 0.104 |
| 0.25° | one_class_svm | 3/3 | 1.000 | 0.200 | 1671.429 | 0.074 |
| 0.25° | local_outlier_factor | 3/3 | 1.000 | 0.200 | 1395.000 | 0.060 |
| 0.25° | current_system | 3/3 | 1.000 | 2.067 | 61.071 | 0.104 |
| 0.25° | current_system_spatial | 3/3 | 1.000 | 2.067 | 61.071 | 0.104 |
| 0.5° | fixed_tilt_threshold | 0/4 | 0.000 | n/a | 9.643 | 0.255 |
| 0.5° | baseline_z_score | 4/4 | 1.000 | 0.500 | 93.214 | 0.255 |
| 0.5° | ewma | 4/4 | 1.000 | 3.350 | 22.500 | 0.205 |
| 0.5° | cusum | 4/4 | 1.000 | 0.550 | 51.429 | 0.047 |
| 0.5° | isolation_forest | 4/4 | 1.000 | 0.000 | 1231.071 | 0.200 |
| 0.5° | one_class_svm | 4/4 | 1.000 | 0.000 | 1671.429 | 0.129 |
| 0.5° | local_outlier_factor | 4/4 | 1.000 | 0.000 | 1395.000 | 0.152 |
| 0.5° | current_system | 4/4 | 1.000 | 1.400 | 61.071 | 0.200 |
| 0.5° | current_system_spatial | 4/4 | 1.000 | 1.400 | 61.071 | 0.200 |
| 1° | fixed_tilt_threshold | 3/3 | 1.000 | 2.400 | 9.643 | 0.574 |
| 1° | baseline_z_score | 3/3 | 1.000 | 0.533 | 93.214 | 0.574 |
| 1° | ewma | 3/3 | 1.000 | 2.100 | 22.500 | 0.392 |
| 1° | cusum | 3/3 | 1.000 | 0.000 | 51.429 | 0.085 |
| 1° | isolation_forest | 3/3 | 1.000 | 0.000 | 1231.071 | 0.151 |
| 1° | one_class_svm | 3/3 | 1.000 | 0.000 | 1671.429 | 0.115 |
| 1° | local_outlier_factor | 3/3 | 1.000 | 0.000 | 1395.000 | 0.512 |
| 1° | current_system | 3/3 | 1.000 | 0.933 | 61.071 | 0.151 |
| 1° | current_system_spatial | 3/3 | 1.000 | 1.000 | 61.071 | 0.151 |

## Quantile calibration and minimum detectable tilt

Each score threshold is selected from the empirical quantiles of the separate 15-minute stationary calibration scores: choose the lowest quantile whose observed false-alarm rate is ≤1/hour. The held-out 95% upper bound uses the rule of three (3 / stationary hours) for zero alarms and the exact Poisson upper bound otherwise. The held-out stationary period is under 3 hours, so a 1/hour false-alarm claim cannot be supported with this much data; no angle is labelled minimum detectable.

| method | score threshold | calibration quantile | calibration false alarms/hour | held-out alarms | held-out false alarms/hour | 95% upper FA/hour | recall at 0.25° | recall at 0.5° | recall at 1.0° | minimum angle |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| fixed_tilt_threshold | 0.035 | 1.000 | 0.000 | 25 | 80.357 | 112.230 | 1.000 | 1.000 | 1.000 | not estimable (<3 h) |
| baseline_z_score | 2.532 | 1.000 | 0.000 | 25 | 80.357 | 112.230 | 1.000 | 1.000 | 1.000 | not estimable (<3 h) |
| ewma | 0.027 | 1.000 | 0.000 | 11 | 35.357 | 58.524 | 1.000 | 1.000 | 1.000 | not estimable (<3 h) |
| cusum | 0.000 | 1.000 | 0.000 | 16 | 51.429 | 78.111 | 1.000 | 1.000 | 1.000 | not estimable (<3 h) |
| isolation_forest | 0.204 | 1.000 | 0.000 | 74 | 237.857 | 288.612 | 1.000 | 1.000 | 1.000 | not estimable (<3 h) |
| one_class_svm | 9.884 | 1.000 | 0.000 | 12 | 38.571 | 62.494 | 1.000 | 1.000 | 1.000 | not estimable (<3 h) |
| local_outlier_factor | 1.155 | 1.000 | 0.000 | 13 | 41.786 | 66.435 | 1.000 | 1.000 | 1.000 | not estimable (<3 h) |
| current_system | 0.704 | 1.000 | 0.000 | 74 | 237.857 | 288.612 | 1.000 | 1.000 | 1.000 | not estimable (<3 h) |
| current_system_spatial | 0.685 | 1.000 | 0.000 | 44 | 141.429 | 181.841 | 1.000 | 1.000 | 1.000 | not estimable (<3 h) |

## Vibration channel response (synthetic events)

The threshold comparison uses backend-normalized vibration intensity ≥0.35.

| event type | events | samples | mean intensity | max intensity | samples ≥0.35 | events with any sample ≥0.35 |
|---|---:|---:|---:|---:|---:|---:|
| tap | 5 | 50 | 0.112 | 0.589 | 0.100 | 5/5 |
| phone_vibration | 1 | 50 | 0.398 | 0.485 | 0.700 | 1/1 |
