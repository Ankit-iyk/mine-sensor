import pytest

from ai_engine.features.extractor import extract_features, reset_state


def make_reading(ts, tilt_x=1.0, tilt_y=1.0, vibration=0.02, node_id="N01"):
    return {
        "node_id": node_id, "zone_id": "Z01", "timestamp": ts,
        "ax": 0.0, "ay": 0.0, "az": 1.0,
        "tilt_x": tilt_x, "tilt_y": tilt_y, "vibration": vibration
    }


def setup_function():
    reset_state()


def test_extract_features_returns_all_expected_keys():
    result = extract_features(make_reading("2026-09-19T09:00:00Z"))
    expected_keys = {
        "tilt_magnitude", "tilt_deviation", "tilt_rate", "tilt_acceleration",
        "rolling_tilt_mean", "rolling_tilt_std",
        "vibration_intensity", "vibration_event_count", "vibration_frequency",
        "vibration_rate", "rolling_vibration_mean", "rolling_vibration_std",
        "five_min_mean", "fifteen_min_mean", "one_hour_mean",
        "trend_slope", "rate_of_change",
    }
    assert set(result.keys()) == expected_keys


def test_extract_features_first_call_has_zero_rate():
    result = extract_features(make_reading("2026-09-19T09:00:00Z"))
    assert result["tilt_rate"] == 0.0
    assert result["vibration_rate"] == 0.0


def test_extract_features_tracks_history_across_calls():
    extract_features(make_reading("2026-09-19T09:00:00Z", tilt_x=1.0, tilt_y=0.0))
    result = extract_features(make_reading("2026-09-19T09:00:10Z", tilt_x=4.0, tilt_y=0.0))
    assert result["tilt_rate"] == pytest.approx(3.0)


def test_extract_features_isolates_nodes():
    extract_features(make_reading("2026-09-19T09:00:00Z", tilt_x=10.0, node_id="N01"))
    result = extract_features(make_reading(
        "2026-09-19T09:00:00Z", tilt_x=1.0, tilt_y=0.0, node_id="N02"
    ))
    assert result["tilt_magnitude"] == pytest.approx(1.0)
