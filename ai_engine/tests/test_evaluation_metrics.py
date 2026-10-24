import math

import pytest

from ai_engine.evaluation.metrics import (
    confidence_interval,
    event_metrics,
    false_alarms_per_hour,
    point_metrics,
)


def test_point_metrics_perfect_predictions():
    result = point_metrics([False, True, True], [0.1, 0.8, 0.9], [False, True, True])
    assert result == {"precision": 1.0, "recall": 1.0, "f1": 1.0, "pr_auc": 1.0}


def test_point_metrics_without_positive_labels_has_undefined_recall_and_auc():
    result = point_metrics([False, False], [0.1, 0.2], [False, True])
    assert result["precision"] == 0.0
    assert math.isnan(result["recall"])
    assert result["f1"] == 0.0
    assert math.isnan(result["pr_auc"])


def test_event_metrics_counts_missed_events_and_onset_relative_delay():
    rows = [
        {"event_id": "a", "is_event": True, "event_onset_time": "2024-01-01T00:00:01+00:00", "timestamp": "2024-01-01T00:00:01+00:00"},
        {"event_id": "a", "is_event": True, "event_onset_time": "2024-01-01T00:00:01+00:00", "timestamp": "2024-01-01T00:00:02+00:00"},
        {"event_id": "b", "is_event": True, "event_onset_time": "2024-01-01T00:00:01+00:00", "timestamp": "2024-01-01T00:00:01+00:00"},
    ]
    result = event_metrics(rows, [False, True, False])
    assert result["event_count"] == 2.0
    assert result["event_recall"] == 0.5
    assert result["detection_delay_seconds"] == 1.0


def test_false_alarms_per_hour_counts_alert_runs():
    base = "2024-01-01T00:00:"
    rows = [
        {"node_id": "N1", "timestamp": base + f"{second:02d}+00:00", "is_event": False}
        for second in range(60)
    ]
    alerts = [False] * 5 + [True] * 5 + [False] * 20 + [True] * 5 + [False] * 25
    assert false_alarms_per_hour(rows, alerts) == pytest.approx(2 / (59 / 3600))


def test_confidence_interval_is_seed_level_and_finite():
    mean, low, high, n = confidence_interval([1.0, 2.0, 3.0])
    assert (mean, n) == (2.0, 3)
    assert low < mean < high
