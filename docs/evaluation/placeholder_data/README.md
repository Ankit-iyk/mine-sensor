# Synthetic placeholder CSVs

`sensor_data.csv` and `event_log.csv` are **SYNTHETIC placeholders**, not measured recordings and not hardware-validated. The event-log notes also identify every listed event as synthetic placeholder data.

The sensor samples are at 10 Hz with perfectly regular 0.1-second timestamps. These files exist only to test the CSV loader and evaluation workflow. Replace them with measured recordings before drawing conclusions about sensor performance.

`sensor_data.csv` contains 38,700 data rows (excluding its header), from
`2026-10-24T10:15:00+05:30` through `2026-10-24T11:19:29.900+05:30`.
The exact timestamp span is 3,869.9 seconds (1 hour, 4 minutes, 29.9 seconds).

Run the focused evaluation from the repository root:

```powershell
python -m ai_engine.evaluation.run_all `
  --real-csv docs/evaluation/placeholder_data/sensor_data.csv `
  --event-log docs/evaluation/placeholder_data/event_log.csv `
  --output-dir docs/evaluation/placeholder_data/results
```

The models in this run are fitted only on the first 30 minutes of stationary samples. Acceleration columns ending in `_g` are converted to m/s² because that is the unit expected by the backend telemetry schema. The normalized vibration values in this dataset are converted to the backend's 10-bit ADC-count scale.
