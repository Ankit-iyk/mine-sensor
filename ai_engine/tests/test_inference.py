import pytest

from ai_engine.anomaly.detector import reset_model_cache
from ai_engine.anomaly.isolation_forest import save_model, train_isolation_forest
from ai_engine.features.extractor import reset_state
from ai_engine.fingerprint.fingerprint import reset_fingerprints
from ai_engine.intelligence.spatial import register_node, reset_node_registry
from ai_engine.intelligence.temporal import reset_temporal_state
from ai_engine.intelligence.trajectory import reset_trajectory_state
from ai_engine.pipeline.build_training_data import build_normal_feature_dataset
from ai_engine.pipeline.inference import analyze_telemetry, reset_pipeline_state


@pytest.fixture
def trained_model_path(tmp_path):
    dataset = build_normal_feature_dataset(node_ids=["N01"], count_per_node=50)
    model = train_isolation_forest(dataset)
    path = str(tmp_path / "test_model.joblib")
    save_model(model, path)
    return path


def make_reading(
    ts="2026-09-19T09:00:00Z",
    tilt_x=1.2,
    tilt_y=1.0,
    vibration=0.02,
    node_id="N01",
):
    return {
        "node_id": node_id,
        "zone_id": "Z01",
        "timestamp": ts,
        "ax": 0.02,
        "ay": 0.01,
        "az": 0.98,
        "tilt_x": tilt_x,
        "tilt_y": tilt_y,
        "vibration": vibration,
    }


def setup_function():
    reset_pipeline_state()
    reset_fingerprints()
    reset_temporal_state()
    reset_trajectory_state()
    reset_node_registry()
    reset_state()
    reset_model_cache()


def test_analyze_telemetry_returns_full_contract(trained_model_path):
    result = analyze_telemetry(make_reading(), model_path=trained_model_path)
    assert set(result.keys()) == {
        "node_id", "zone_id", "features", "anomaly", "temporal",
        "spatial", "risk", "trajectory", "explanation",
    }


def test_analyze_telemetry_normal_reading_is_safe(trained_model_path):
    result = analyze_telemetry(make_reading(), model_path=trained_model_path)
    assert result["risk"]["state"] in {"SAFE", "WARNING"}
    assert "reasons" in result["explanation"]


def test_analyze_telemetry_tracks_state_across_calls(trained_model_path):
    analyze_telemetry(
        make_reading(ts="2026-09-19T09:00:00Z"),
        model_path=trained_model_path,
    )
    result = analyze_telemetry(
        make_reading(ts="2026-09-19T09:00:10Z", tilt_x=1.3),
        model_path=trained_model_path,
    )
    assert len(result["trajectory"]["history"]) == 2


def test_analyze_telemetry_spatial_correlation_with_registered_neighbours(trained_model_path):
    register_node("N01", 0, 0)
    register_node("N02", 5, 0)
    result = analyze_telemetry(make_reading(node_id="N01"), model_path=trained_model_path)
    assert "correlation" in result["spatial"]
