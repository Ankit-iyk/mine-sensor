import csv
from datetime import datetime, timedelta, timezone

import numpy as np

from ai_engine.evaluation.noise_floor import analyze_stationary_csv


def test_noise_floor_writes_noise_drift_allan_and_false_alarm_outputs(tmp_path):
    source = tmp_path / "stationary.csv"
    rng = np.random.default_rng(17)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with source.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "timestamp", "node_id", "tilt_x", "tilt_y",
            "accel_x", "accel_y", "accel_z", "vibration", "label",
        ])
        for index in range(300):
            timestamp = start + timedelta(seconds=index)
            drift = index * 0.0001
            writer.writerow([
                timestamp.isoformat(), "N01",
                1.0 + drift + rng.normal(0, 0.01),
                0.5 + rng.normal(0, 0.015),
                rng.normal(0, 0.02), rng.normal(0, 0.02),
                9.8 + rng.normal(0, 0.03), 0, "",
            ])

    output = tmp_path / "out"
    report = analyze_stationary_csv(source, output, target_false_alarms_per_hour=10)

    assert report["node_id"] == "N01"
    assert report["minimum_detectable_tilt_deg"] >= 0
    axes = {row["axis"] for row in report["axis_summary"]}
    assert axes == {"tilt_x", "tilt_y", "accel_x", "accel_y", "accel_z"}
    assert report["axis_summary"][0]["noise_std"] > 0
    assert report["axis_summary"][0]["drift_per_hour"] > 0.15
    assert report["allan_deviation"]
    assert (output / "noise_floor_summary.csv").is_file()
    assert (output / "allan_deviation.csv").is_file()
    assert (output / "false_alarms_vs_threshold.csv").is_file()
    assert (output / "false_alarms_vs_threshold.png").is_file()
