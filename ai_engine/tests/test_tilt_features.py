import pytest

from ai_engine.features.tilt import (
    rolling_tilt_mean,
    rolling_tilt_std,
    tilt_acceleration,
    tilt_deviation,
    tilt_magnitude,
    tilt_rate,
)


def test_tilt_magnitude_basic():
    assert tilt_magnitude(3, 4) == 5.0


def test_tilt_deviation_from_baseline():
    assert tilt_deviation(current_magnitude=7.0, baseline_mean=2.0) == 5.0


def test_tilt_rate_needs_two_points():
    assert tilt_rate([5.0]) == 0.0
    assert tilt_rate([5.0, 8.0]) == 3.0


def test_tilt_acceleration_needs_two_rates():
    assert tilt_acceleration([1.0]) == 0.0
    assert tilt_acceleration([1.0, 4.0]) == 3.0


def test_rolling_tilt_mean_empty_and_normal():
    assert rolling_tilt_mean([]) == 0.0
    assert rolling_tilt_mean([2.0, 4.0, 6.0]) == 4.0


def test_rolling_tilt_std_needs_two_points():
    assert rolling_tilt_std([5.0]) == 0.0
    assert rolling_tilt_std([2.0, 4.0, 6.0]) == pytest.approx(1.633, rel=1e-3)
