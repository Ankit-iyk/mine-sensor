# Real stationary-run outputs

No hardware stationary recording is included or claimed as measured data.
Run `python -m ai_engine.evaluation.noise_floor PATH_TO_STATIONARY.csv
--output-dir docs/evaluation/real` to generate `noise_floor_summary.csv`,
`allan_deviation.csv`, `false_alarms_vs_threshold.csv`, and
`false_alarms_vs_threshold.png` from a real recording. The generated files
should only be committed when their source recording and collection metadata
are available for review.
