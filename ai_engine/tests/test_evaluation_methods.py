from datetime import datetime, timedelta, timezone

import numpy as np

from ai_engine.evaluation.methods import MethodSuite, _stuck_sensor_predictions


def _row(index, node="N01", zone="Z01", step=None, **overrides):
    return {
        "node_id": node,
        "zone_id": zone,
        "step": index if step is None else step,
        "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index),
        "tilt_deviation": 0.2,
        "baseline_deviation": 0.2,
        "tilt_x": 1.0 + index * 0.01,
        "tilt_y": 0.5,
        "accel_magnitude": 9.8,
        "vibration_intensity": 0.0,
        **overrides,
    }


def test_no_isolation_forest_baseline_uses_shared_persistence_wrapper():
    suite = object.__new__(MethodSuite)
    rows = [_row(index, tilt_x=2.0) for index in range(4)]

    scores, alerts = suite.predict(rows, "baseline_deviation_only_spatial")

    assert np.all(scores == 0.2)
    assert alerts.tolist() == [False, False, True, True]


def test_stuck_sensor_check_uses_a_ten_reading_zero_variance_window():
    rows = [
        _row(index, tilt_x=1.0, tilt_y=0.5, accel_magnitude=0.0, vibration_intensity=0.0)
        for index in range(11)
    ]

    _, alerts = _stuck_sensor_predictions(rows)

    assert alerts.tolist() == [False] * 9 + [True, True]


def test_same_step_multi_node_alerts_are_spatially_corroborated():
    suite = object.__new__(MethodSuite)
    first = _row(0, node="N01", step=1, tilt_deviation=0.6)
    second = _row(0, node="N02", step=1, tilt_deviation=0.7)
    alerts = suite._persist_and_corroborate([first, second], np.asarray([True, True]), None)

    assert alerts.tolist() == [True, True]
