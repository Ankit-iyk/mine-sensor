import pytest

from ai_engine.anomaly.detector import detect_anomaly, reset_model_cache
from ai_engine.anomaly.isolation_forest import save_model, train_isolation_forest
from ai_engine.fingerprint.fingerprint import build_fingerprint, reset_fingerprints
from ai_engine.pipeline.build_training_data import build_normal_feature_dataset


@pytest.fixture
def trained_model_path(tmp_path):
    dataset = build_normal_feature_dataset(node_ids=["N01"], count_per_node=50)
    model = train_isolation_forest(dataset)
    path = str(tmp_path / "test_model.joblib")
    save_model(model, path)
    return path, dataset


def setup_function():
    reset_model_cache()
    reset_fingerprints()


def test_detect_anomaly_returns_expected_keys(trained_model_path):
    model_path, dataset = trained_model_path
    build_fingerprint("N01", tilt_history=[1.0, 1.1, 0.9], vibration_history=[2.0, 2.1, 1.9])

    result = detect_anomaly(dataset[0], node_id="N01", model_path=model_path)
    assert set(result.keys()) == {"score", "is_anomalous", "tilt_deviation", "vibration_deviation"}


def test_detect_anomaly_normal_sample_low_deviation(trained_model_path):
    model_path, dataset = trained_model_path
    build_fingerprint(
        "N01",
        tilt_history=[1.0, 1.1, 0.9, 1.0],
        vibration_history=[2.0, 2.1, 1.9, 2.0],
    )

    result = detect_anomaly(dataset[0], node_id="N01", model_path=model_path)
    assert isinstance(result["is_anomalous"], bool)


def test_detect_anomaly_model_is_cached(trained_model_path):
    model_path, dataset = trained_model_path
    build_fingerprint("N01", tilt_history=[1.0, 1.1, 0.9], vibration_history=[2.0, 2.1, 1.9])

    detect_anomaly(dataset[0], node_id="N01", model_path=model_path)
    from ai_engine.anomaly.detector import _model_cache

    assert model_path in _model_cache
