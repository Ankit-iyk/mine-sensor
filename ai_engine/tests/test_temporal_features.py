import pytest
from datetime import datetime, timedelta

from ai_engine.features.temporal import (
    fifteen_min_mean,
    five_min_mean,
    one_hour_mean,
    persistence,
    rate_of_change,
    trend_slope,
)


def make_history(base_time, values, step_seconds=60):
    return [(base_time + timedelta(seconds=i * step_seconds), value) for i, value in enumerate(values)]


def test_five_min_mean_filters_window():
    base = datetime(2026, 9, 19, 9, 0, 0)
    history = make_history(base, [1, 2, 3, 4, 5, 6, 7, 8], step_seconds=60)
    ref_time = base + timedelta(minutes=7)
    result = five_min_mean(history, ref_time)
    assert result > 0


def test_fifteen_min_and_hour_mean_empty_history():
    ref_time = datetime(2026, 9, 19, 9, 0, 0)
    assert fifteen_min_mean([], ref_time) == 0.0
    assert one_hour_mean([], ref_time) == 0.0


def test_trend_slope_rising():
    base = datetime(2026, 9, 19, 9, 0, 0)
    history = make_history(base, [1, 2, 3, 4, 5], step_seconds=60)
    assert trend_slope(history) > 0


def test_trend_slope_flat():
    base = datetime(2026, 9, 19, 9, 0, 0)
    history = make_history(base, [5, 5, 5, 5], step_seconds=60)
    assert trend_slope(history) == pytest.approx(0.0, abs=1e-9)


def test_trend_slope_insufficient_data():
    assert trend_slope([(datetime(2026, 9, 19, 9, 0, 0), 5)]) == 0.0


def test_persistence_fraction():
    assert persistence([]) == 0.0
    assert persistence([True, True, False, True]) == 0.75


def test_rate_of_change_basic():
    base = datetime(2026, 9, 19, 9, 0, 0)
    history = [(base, 10), (base + timedelta(seconds=10), 20)]
    assert rate_of_change(history) == 1.0


def test_rate_of_change_insufficient_data():
    assert rate_of_change([(datetime(2026, 9, 19, 9, 0, 0), 5)]) == 0.0
