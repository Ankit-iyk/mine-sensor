import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

from ai_engine.evaluation import run_all


def test_training_partition_includes_only_event_free_wide_conditions(monkeypatch):
    calls = []

    def fake_generate(scenario, seed, noise_model):
        calls.append((scenario, seed, noise_model))
        return [{
            "scenario": scenario,
            "noise_model": noise_model,
            "seed": seed,
            "is_event": False,
        }]

    def fake_extract(readings):
        source = readings[0]
        return [
            {
                "scenario": source["scenario"],
                "noise_model": source["noise_model"],
                "seed": source["seed"],
                "is_event": False,
            }
            for _ in range(run_all._TRAIN_KEEP_EVERY)
        ]

    monkeypatch.setattr(run_all, "generate_episode", fake_generate)
    monkeypatch.setattr(run_all, "extract_backend_features", fake_extract)

    rows = run_all._training_features(seeds=1)

    assert len(calls) == 30 * 3
    assert { (scenario, noise) for scenario, _, noise in calls } == {
        ("normal", "simulator"),
        ("baseline_drift", "simulator"),
        ("normal", "distribution_shift"),
    }
    assert all(row["seed"] >= run_all._TRAIN_SEED_BASE for row in rows)
    assert all(not row["is_event"] for row in rows)
    assert {row["noise_model"] for row in rows} == {"simulator", "distribution_shift"}


def test_report_refresh_preserves_signed_forest_value_intervals():
    row = {
        "method": "forest_added_value",
        "f1_ci95_low": -0.03,
        "f1_ci95_high": -0.01,
    }

    run_all._bound_confidence_intervals(row)

    assert row["f1_ci95_low"] == -0.03
    assert row["f1_ci95_high"] == -0.01


def test_report_refresh_restores_historically_clipped_paired_interval():
    row = {
        "method": "forest_added_value",
        "f1_mean": -0.022,
        "f1_ci95_low": 0.0,
        "f1_ci95_high": -0.015,
    }

    run_all._bound_confidence_intervals(row)

    assert row["f1_ci95_low"] == pytest.approx(-0.029)
    assert row["f1_ci95_low"] <= row["f1_mean"] <= row["f1_ci95_high"]


def test_report_csv_confidence_intervals_contain_every_finite_mean():
    path = Path(__file__).resolve().parents[2] / "docs" / "evaluation" / "results.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows

    for row in rows:
        for column, raw_mean in row.items():
            if not column.endswith("_mean") or raw_mean in ("", None):
                continue
            mean = float(raw_mean)
            if not math.isfinite(mean):
                continue
            metric = column[:-5]
            low = float(row[f"{metric}_ci95_low"])
            high = float(row[f"{metric}_ci95_high"])
            assert math.isfinite(low), (row["noise_model"], row["scenario"], row["method"], metric)
            assert math.isfinite(high), (row["noise_model"], row["scenario"], row["method"], metric)
            assert low <= mean <= high, (
                row["noise_model"], row["scenario"], row["method"],
                metric, low, mean, high,
            )


def test_calibration_threshold_uses_requested_score_quantile():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        {
            "node_id": "N01",
            "timestamp": start + timedelta(seconds=36 * index),
            "is_event": False,
        }
        for index in range(100)
    ]
    scores = np.asarray([
        value
        for value in range(99, -1, -1)
        for _ in (0,)
    ], dtype=float)
    scores[::2], scores[1::2] = np.arange(0, 100, 2), np.arange(99, 0, -2)

    threshold, quantile, rate = run_all._calibrate_score_threshold(
        suite=object(),
        method="baseline_z_score",
        calibration_rows=rows,
        scores=scores,
        target_false_alarms_per_hour=5.0,
    )

    assert quantile == np.mean(scores <= threshold)
    assert rate <= 5.0
    assert threshold < float(scores.max())


def test_rule_of_three_requires_three_hours_for_one_per_hour_bound():
    assert run_all._false_alarm_rate_upper_95(0, 0.25) == 12.0


def test_placeholder_report_refuses_minimum_tilt_claim_with_short_heldout_period():
    path = Path(__file__).resolve().parents[2] / "docs" / "evaluation" / "placeholder_data" / "results" / "results.md"
    report = path.read_text(encoding="utf-8")

    assert "held-out stationary period is under 3 hours" in report
    assert "a 1/hour false-alarm claim cannot be supported" in report
    assert "not estimable (<3 h)" in report
