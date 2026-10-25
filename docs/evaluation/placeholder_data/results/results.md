# SYNTHETIC PLACEHOLDER DATA — evaluation only

These outputs use synthetic placeholder data only. They are not measured recordings and are not hardware-validated. Models were fit only on the first 30 minutes of stationary samples; the backend feature pipeline then processed the ordered input stream. This run exists to exercise the CSV loader and evaluation workflow.

- Sensor CSV: `docs\evaluation\placeholder_data\sensor_data.csv`
- Event log: `docs\evaluation\placeholder_data\event_log.csv`
- Training features after 1-in-10 subsampling: 1800
- Acceleration units: input `_g` columns converted to m/s² (backend schema units).
- Vibration values in [0, 1] are treated as normalized and converted to 10-bit ADC counts.
- Event recall requires all logged events at that angle to be detected; false alarms are measured on post-training stationary samples only.

## Tilt event results

| target angle | method | events detected / total | event recall | detection delay (s) | false alarms/hour | PR-AUC |
|---:|---|---:|---:|---:|---:|---:|
| 0.25° | fixed_tilt_threshold | 0/3 | 0.000 | n/a | 5.218 | 0.100 |
| 0.25° | baseline_z_score | 3/3 | 1.000 | 1.067 | 46.959 | 0.100 |
| 0.25° | ewma | 0/3 | 0.000 | n/a | 12.175 | 0.084 |
| 0.25° | cusum | 3/3 | 1.000 | 3.200 | 6.957 | 0.013 |
| 0.25° | isolation_forest | 3/3 | 1.000 | 0.167 | 1019.180 | 0.102 |
| 0.25° | one_class_svm | 3/3 | 1.000 | 0.200 | 1460.940 | 0.074 |
| 0.25° | local_outlier_factor | 3/3 | 1.000 | 0.200 | 1217.450 | 0.059 |
| 0.25° | current_system | 3/3 | 1.000 | 2.067 | 33.045 | 0.102 |
| 0.25° | current_system_spatial | 3/3 | 1.000 | 2.067 | 33.045 | 0.102 |
| 0.5° | fixed_tilt_threshold | 0/4 | 0.000 | n/a | 5.218 | 0.255 |
| 0.5° | baseline_z_score | 4/4 | 1.000 | 0.500 | 46.959 | 0.255 |
| 0.5° | ewma | 4/4 | 1.000 | 3.350 | 12.175 | 0.205 |
| 0.5° | cusum | 4/4 | 1.000 | 0.550 | 6.957 | 0.046 |
| 0.5° | isolation_forest | 4/4 | 1.000 | 0.000 | 1019.180 | 0.198 |
| 0.5° | one_class_svm | 4/4 | 1.000 | 0.000 | 1460.940 | 0.129 |
| 0.5° | local_outlier_factor | 4/4 | 1.000 | 0.000 | 1217.450 | 0.152 |
| 0.5° | current_system | 4/4 | 1.000 | 1.400 | 33.045 | 0.198 |
| 0.5° | current_system_spatial | 4/4 | 1.000 | 1.400 | 33.045 | 0.198 |
| 1° | fixed_tilt_threshold | 3/3 | 1.000 | 2.400 | 5.218 | 0.573 |
| 1° | baseline_z_score | 3/3 | 1.000 | 0.533 | 46.959 | 0.573 |
| 1° | ewma | 3/3 | 1.000 | 2.100 | 12.175 | 0.392 |
| 1° | cusum | 3/3 | 1.000 | 0.000 | 6.957 | 0.085 |
| 1° | isolation_forest | 3/3 | 1.000 | 0.000 | 1019.180 | 0.150 |
| 1° | one_class_svm | 3/3 | 1.000 | 0.000 | 1460.940 | 0.115 |
| 1° | local_outlier_factor | 3/3 | 1.000 | 0.000 | 1217.450 | 0.512 |
| 1° | current_system | 3/3 | 1.000 | 0.933 | 33.045 | 0.150 |
| 1° | current_system_spatial | 3/3 | 1.000 | 1.000 | 33.045 | 0.150 |

## Minimum detectable tilt at no more than 1 false alarm/hour

Each method's continuous score threshold is calibrated on the first 30-minute stationary training segment to allow no more than 1 false alarm/hour. The minimum angle is reported only when the held-out stationary control rate also stays ≤1/hour and all logged events at that angle are detected.

| method | calibrated score threshold | training false alarms/hour | test false alarms/hour | recall at 0.25° | recall at 0.5° | recall at 1.0° | minimum angle at ≤1 FA/hour |
|---|---:|---:|---:|---:|---:|---:|---|
| fixed_tilt_threshold | 0.036 | 0.000 | 38.263 | 1.000 | 1.000 | 1.000 | none at 100% event recall |
| baseline_z_score | 2.572 | 0.000 | 38.263 | 1.000 | 1.000 | 1.000 | none at 100% event recall |
| ewma | 0.025 | 0.000 | 10.435 | 1.000 | 1.000 | 1.000 | none at 100% event recall |
| cusum | 0.000 | 0.000 | 1.739 | 1.000 | 1.000 | 1.000 | none at 100% event recall |
| isolation_forest | 0.213 | 0.000 | 50.437 | 0.667 | 1.000 | 1.000 | none at 100% event recall |
| one_class_svm | 11.876 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | none at 100% event recall |
| local_outlier_factor | 36.463 | 0.000 | 22.610 | 0.333 | 1.000 | 1.000 | none at 100% event recall |
| current_system | 0.713 | 0.000 | 50.437 | 0.667 | 1.000 | 1.000 | none at 100% event recall |
| current_system_spatial | 0.713 | 0.000 | 27.827 | 0.333 | 0.500 | 0.333 | none at 100% event recall |

## Vibration channel response (synthetic events)

The threshold comparison uses backend-normalized vibration intensity ≥0.35.

| event type | events | samples | mean intensity | max intensity | samples ≥0.35 | events with any sample ≥0.35 |
|---|---:|---:|---:|---:|---:|---:|
| tap | 5 | 50 | 0.112 | 0.589 | 0.100 | 5/5 |
| phone_vibration | 1 | 50 | 0.398 | 0.485 | 0.700 | 1/1 |
