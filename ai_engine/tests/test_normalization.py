import pytest

from ai_engine.preprocessing.normalization import _scale, normalize


def test_normalize_scales_correctly():
    telemetry = {"tilt_x": 0, "tilt_y": 45, "vibration": 50}
    result = normalize(telemetry)
    assert result["tilt_x_norm"] == 0.5
    assert result["tilt_y_norm"] == 0.75
    assert result["vibration_norm"] == 0.5


def test_normalize_preserves_original_fields():
    telemetry = {"tilt_x": 0, "tilt_y": 0, "vibration": 0}
    result = normalize(telemetry)
    assert result["tilt_x"] == 0
    assert "tilt_x_norm" in result


def test_scale_rejects_equal_bounds():
    with pytest.raises(ValueError):
        _scale(5, 10, 10)
