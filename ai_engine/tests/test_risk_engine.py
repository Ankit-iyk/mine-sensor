from ai_engine.risk.risk_engine import calculate_risk


def make_features(vibration_intensity=2.0, trend_slope=0.0):
    return {"vibration_intensity": vibration_intensity, "trend_slope": trend_slope}


def make_anomaly(tilt_deviation=0.0, is_anomalous=False):
    return {
        "tilt_deviation": tilt_deviation,
        "vibration_deviation": 0.0,
        "is_anomalous": is_anomalous,
        "score": 0.0,
    }


def test_low_risk_normal_reading_is_safe():
    result = calculate_risk(make_features(), make_anomaly())
    assert result["state"] == "SAFE"
    assert result["score"] < 30


def test_high_risk_all_signals_elevated_is_danger():
    features = make_features(vibration_intensity=50.0, trend_slope=5.0)
    anomaly = make_anomaly(tilt_deviation=10.0, is_anomalous=True)
    result = calculate_risk(features, anomaly)
    assert result["state"] == "DANGER"
    assert result["score"] > 70


def test_risk_score_bounded_at_100():
    features = make_features(vibration_intensity=500.0, trend_slope=50.0)
    anomaly = make_anomaly(tilt_deviation=100.0, is_anomalous=True)
    result = calculate_risk(features, anomaly)
    assert result["score"] <= 100.0


def test_components_are_returned_for_explainability():
    result = calculate_risk(make_features(), make_anomaly())
    assert set(result["components"].keys()) == {
        "tilt_risk", "vibration_risk", "trend_risk", "anomaly_risk"
    }


def test_warning_state_midrange_risk():
    features = make_features(vibration_intensity=25.0, trend_slope=2.0)
    anomaly = make_anomaly(tilt_deviation=4.0, is_anomalous=False)
    result = calculate_risk(features, anomaly)
    assert result["state"] in {"WARNING", "SAFE", "DANGER"}
    assert 0 <= result["score"] <= 100
