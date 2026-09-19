import pytest

from ai_engine.preprocessing.filtering import (
    filter_readings,
    moving_average,
    remove_duplicates,
)


def test_remove_duplicates_keeps_first_reading():
    readings = [
        {"node_id": "N01", "timestamp": "2026-09-19T09:30:12Z", "vibration": 1},
        {"node_id": "N01", "timestamp": "2026-09-19T09:30:12Z", "vibration": 2},
        {"node_id": "N01", "timestamp": "2026-09-19T09:30:13Z", "vibration": 3},
    ]

    assert remove_duplicates(readings) == [readings[0], readings[2]]


def test_moving_average_uses_trailing_window():
    assert moving_average([1, 2, 6, 3], window_size=3) == [1, 1.5, 3, 11 / 3]


def test_filter_readings_deduplicates_and_adds_smoothed_value():
    readings = [
        {"node_id": "N01", "timestamp": "t1", "vibration": 1},
        {"node_id": "N01", "timestamp": "t1", "vibration": 99},
        {"node_id": "N01", "timestamp": "t2", "vibration": 3},
    ]

    result = filter_readings(readings, "vibration", window_size=2)

    assert len(result) == 2
    assert [reading["vibration_smooth"] for reading in result] == [1, 2]
    assert readings[0] == {"node_id": "N01", "timestamp": "t1", "vibration": 1}


def test_moving_average_rejects_non_positive_window():
    with pytest.raises(ValueError):
        moving_average([1, 2], window_size=0)
