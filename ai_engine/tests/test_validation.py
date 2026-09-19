import pytest

from ai_engine.preprocessing.validation import ValidationError, validate


def valid_sample():
    return {
        "node_id": "N01", "zone_id": "Z01", "timestamp": "2026-09-19T09:30:12Z",
        "ax": 0.04, "ay": 0.02, "az": 0.98,
        "tilt_x": 1.8, "tilt_y": 2.1, "vibration": 0
    }


def test_valid_telemetry_passes():
    assert validate(valid_sample()) is not None


def test_missing_field_raises():
    sample = valid_sample()
    del sample["tilt_x"]
    with pytest.raises(ValidationError):
        validate(sample)


def test_out_of_range_raises():
    sample = valid_sample()
    sample["tilt_x"] = 500
    with pytest.raises(ValidationError):
        validate(sample)
