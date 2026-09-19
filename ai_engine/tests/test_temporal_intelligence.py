from ai_engine.intelligence.temporal import (
    classify_temporal_state,
    reset_temporal_state,
)


def setup_function():
    reset_temporal_state()


def test_stable_state_when_no_anomalies():
    for _ in range(5):
        result = classify_temporal_state("N01", is_anomalous=False, trend_slope=0.0)
    assert result["state"] == "STABLE"


def test_transient_state_single_anomaly():
    classify_temporal_state("N02", is_anomalous=False, trend_slope=0.0)
    classify_temporal_state("N02", is_anomalous=False, trend_slope=0.0)
    result = classify_temporal_state("N02", is_anomalous=True, trend_slope=0.1)
    assert result["state"] == "TRANSIENT"


def test_persistent_state_sustained_flat_anomaly():
    for _ in range(6):
        result = classify_temporal_state("N03", is_anomalous=True, trend_slope=0.0)
    assert result["state"] == "PERSISTENT"


def test_escalating_state_sustained_rising_anomaly():
    for _ in range(6):
        result = classify_temporal_state("N04", is_anomalous=True, trend_slope=2.0)
    assert result["state"] == "ESCALATING"


def test_nodes_are_isolated():
    for _ in range(6):
        classify_temporal_state("N05", is_anomalous=True, trend_slope=2.0)
    result = classify_temporal_state("N06", is_anomalous=False, trend_slope=0.0)
    assert result["state"] == "STABLE"
