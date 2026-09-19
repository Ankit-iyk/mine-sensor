import pytest

from ai_engine.fingerprint.baseline import compute_baseline, update_baseline_incremental
from ai_engine.fingerprint.fingerprint import (
    build_fingerprint,
    deviation_score,
    get_fingerprint,
    reset_fingerprints,
    update_fingerprint,
)


def setup_function():
    reset_fingerprints()


def test_compute_baseline_basic():
    result = compute_baseline([2.0, 4.0, 6.0])
    assert result["mean"] == 4.0
    assert result["std"] == pytest.approx(1.633, rel=1e-3)


def test_compute_baseline_empty_raises():
    with pytest.raises(ValueError):
        compute_baseline([])


def test_compute_baseline_single_value_zero_std():
    result = compute_baseline([5.0])
    assert result["mean"] == 5.0
    assert result["std"] == 0.0


def test_build_fingerprint_stores_tilt_and_vibration():
    fingerprint = build_fingerprint(
        "N01", tilt_history=[1.0, 1.2, 1.1], vibration_history=[2.0, 2.5, 2.2]
    )
    assert fingerprint["tilt"]["mean"] == pytest.approx(1.1, rel=1e-2)
    assert fingerprint["count"] == 3
    assert get_fingerprint("N01") == fingerprint


def test_update_fingerprint_creates_if_missing():
    fingerprint = update_fingerprint("N02", tilt_magnitude=1.5, vibration_value=3.0)
    assert fingerprint["tilt"]["mean"] == 1.5


def test_update_fingerprint_shifts_mean_toward_new_value():
    build_fingerprint("N03", tilt_history=[1.0, 1.0, 1.0], vibration_history=[2.0, 2.0, 2.0])
    updated = update_fingerprint("N03", tilt_magnitude=10.0, vibration_value=2.0)
    assert updated["tilt"]["mean"] > 1.0


def test_deviation_score_no_fingerprint_returns_zero():
    result = deviation_score("N99", tilt_magnitude=5.0, vibration_value=5.0)
    assert result == {"tilt_deviation": 0.0, "vibration_deviation": 0.0}


def test_deviation_score_flags_outlier():
    build_fingerprint(
        "N04",
        tilt_history=[1.0, 1.1, 0.9, 1.0],
        vibration_history=[2.0, 2.1, 1.9, 2.0],
    )
    result = deviation_score("N04", tilt_magnitude=10.0, vibration_value=2.0)
    assert result["tilt_deviation"] > 5.0
