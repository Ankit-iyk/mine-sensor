import pytest

from ai_engine import adapter
from ai_engine.adapter import AIEngineDetector


def _predict(monkeypatch, *, is_anomalous, tilt_deviation, baseline_deviation):
    detector = AIEngineDetector()
    detector._model = object()
    monkeypatch.setattr(
        adapter,
        "score_sample",
        lambda model, features: {
            "is_anomalous": is_anomalous,
            "raw_score": 0.1,
        },
    )
    return detector.predict(
        {
            "tilt_deviation": tilt_deviation,
            "baseline_deviation": baseline_deviation,
        }
    )


def test_adapter_uses_backend_deviations_for_anomalous_state(monkeypatch):
    result = _predict(
        monkeypatch,
        is_anomalous=True,
        tilt_deviation=0.12,
        baseline_deviation=0.12,
    )

    assert result["state"] == "ANOMALOUS"
    assert result["detector_mode"] == "model"


def test_adapter_classifies_small_backend_deviations_as_micro_anomaly(monkeypatch):
    result = _predict(
        monkeypatch,
        is_anomalous=True,
        tilt_deviation=0.10,
        baseline_deviation=0.10,
    )

    assert result["state"] == "MICRO_ANOMALY"


def test_adapter_keeps_model_inliers_normal_even_with_large_deviation(monkeypatch):
    result = _predict(
        monkeypatch,
        is_anomalous=False,
        tilt_deviation=1.0,
        baseline_deviation=1.0,
    )

    assert result["state"] == "NORMAL"


def test_adapter_maps_lower_isolation_forest_scores_to_higher_anomaly_scores(monkeypatch):
    detector = AIEngineDetector()
    detector._model = object()
    raw_scores = iter((0.4, -0.4))

    def score_sample(_model, _features):
        raw_score = next(raw_scores)
        return {"is_anomalous": raw_score < 0, "raw_score": raw_score}

    monkeypatch.setattr(adapter, "score_sample", score_sample)
    features = {"tilt_deviation": 0.2, "baseline_deviation": 0.2}

    inlier = detector.predict(features)
    outlier = detector.predict(features)

    assert inlier["anomaly_score"] == pytest.approx(0.1)
    assert outlier["anomaly_score"] == pytest.approx(0.9)
    assert inlier["detector_mode"] == outlier["detector_mode"] == "model"
