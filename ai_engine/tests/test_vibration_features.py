import pytest

from ai_engine.features.vibration import (
    rolling_vibration_mean,
    rolling_vibration_std,
    vibration_event_count,
    vibration_frequency,
    vibration_intensity,
    vibration_rate,
)


def test_vibration_intensity_passthrough():
    assert vibration_intensity(7.5) == 7.5


def test_vibration_event_count_uses_threshold():
    history = [0.1, 0.6, 0.2, 0.9, 0.4]
    assert vibration_event_count(history, threshold=0.5) == 2


def test_vibration_frequency_empty_and_normal():
    assert vibration_frequency([]) == 0.0
    history = [0.1, 0.6, 0.2, 0.9]
    assert vibration_frequency(history, threshold=0.5) == 0.5


def test_vibration_rate_needs_two_points():
    assert vibration_rate([3.0]) == 0.0
    assert vibration_rate([3.0, 8.0]) == 5.0


def test_rolling_vibration_mean_empty_and_normal():
    assert rolling_vibration_mean([]) == 0.0
    assert rolling_vibration_mean([0.2, 0.4, 0.6]) == pytest.approx(0.4)


def test_rolling_vibration_std_needs_two_points():
    assert rolling_vibration_std([5.0]) == 0.0
    assert rolling_vibration_std([0.2, 0.4, 0.6]) == pytest.approx(0.1633, rel=1e-3)
