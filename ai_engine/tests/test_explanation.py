from ai_engine.explainability.explanation import generate_explanation


def make_risk(state="SAFE", tilt_risk=0.0, vibration_risk=0.0):
    return {
        "score": 10.0,
        "state": state,
        "components": {
            "tilt_risk": tilt_risk,
            "vibration_risk": vibration_risk,
            "trend_risk": 0.0,
            "anomaly_risk": 0.0,
        },
    }


def test_safe_state_no_notable_signals_gives_default_reason():
    result = generate_explanation(
        features={},
        anomaly={},
        temporal={"state": "STABLE"},
        spatial={"correlation": 0.0},
        risk=make_risk(),
        zone_id="Z01",
    )
    assert result["reasons"] == ["All readings within normal range"]
    assert "stable" in result["summary"].lower()


def test_high_tilt_risk_adds_reason():
    result = generate_explanation(
        features={},
        anomaly={},
        temporal={"state": "STABLE"},
        spatial={"correlation": 0.0},
        risk=make_risk(state="WARNING", tilt_risk=50.0),
        zone_id="Z01",
    )
    assert "Tilt deviation is increasing" in result["reasons"]


def test_escalating_state_adds_two_reasons():
    result = generate_explanation(
        features={},
        anomaly={},
        temporal={"state": "ESCALATING"},
        spatial={"correlation": 0.0},
        risk=make_risk(state="DANGER"),
        zone_id="Z02",
    )
    assert "Abnormal behaviour is persistent" in result["reasons"]
    assert "Risk trajectory is escalating" in result["reasons"]


def test_spatial_correlation_adds_reason():
    result = generate_explanation(
        features={},
        anomaly={},
        temporal={"state": "STABLE"},
        spatial={"correlation": 0.8},
        risk=make_risk(),
        zone_id="Z01",
    )
    assert "Neighbouring nodes show correlated behaviour" in result["reasons"]


def test_danger_summary_wording():
    result = generate_explanation(
        features={},
        anomaly={},
        temporal={"state": "STABLE"},
        spatial={"correlation": 0.0},
        risk=make_risk(state="DANGER"),
        zone_id="Z03",
    )
    assert "Critical" in result["summary"]
    assert "Z03" in result["summary"]
