"""
Adapter implementing the backend's AnomalyDetector interface (ml-contract),
wrapping the ai_engine Isolation Forest and fingerprint scoring.

The backend vibration fields are normalized to 0.0-1.0, matching the
calibrated simulator and model training data.
"""

from ai_engine.anomaly.isolation_forest import (
    DEFAULT_MODEL_PATH,
    load_model,
    score_sample,
)
from ai_engine.fingerprint.fingerprint import deviation_score

try:
    from app.ml.interface import AnomalyDetector
except ModuleNotFoundError:
    class AnomalyDetector:
        """Fallback base for using ai_engine outside the backend package."""

        pass

# Backend-confirmed normalized vibration scale.
_VIBRATION_SCALE_FACTOR = 1.0


class AIEngineDetector(AnomalyDetector):
    """Implements predict(features), load(path), and the version property."""

    def __init__(self):
        self._model = None
        self._version = "ai-engine-v1"

    def load(self, path: str = DEFAULT_MODEL_PATH) -> None:
        self._model = load_model(path)

    @property
    def version(self) -> str:
        return self._version

    def predict(self, features: dict) -> dict:
        if self._model is None:
            raise RuntimeError("Model not loaded - call load() first")

        mapped = self._map_features(features)
        isolation_result = score_sample(self._model, mapped)

        node_id = features.get("node_id")
        if node_id:
            deviation = deviation_score(
                node_id,
                tilt_magnitude=mapped["tilt_magnitude"],
                vibration_value=mapped["vibration_intensity"],
            )
        else:
            deviation = {"tilt_deviation": 0.0, "vibration_deviation": 0.0}

        anomaly_score = max(0.0, min(1.0, 0.5 - isolation_result["raw_score"]))

        if not isolation_result["is_anomalous"]:
            state = "NORMAL"
        elif deviation["tilt_deviation"] < 3.0 and deviation["vibration_deviation"] < 3.0:
            state = "MICRO_ANOMALY"
        else:
            state = "ANOMALOUS"

        return {
            "anomaly_score": anomaly_score,
            "state": state,
            "model_version": self._version,
            "confidence": None,
            "raw_score": isolation_result["raw_score"],
        }

    def _map_features(self, backend_features: dict) -> dict:
        """Map backend FeatureVector fields into ai_engine FEATURE_COLUMNS."""
        scale = _VIBRATION_SCALE_FACTOR
        return {
            "tilt_magnitude": backend_features.get("tilt_magnitude", 0.0),
            "tilt_deviation": backend_features.get("tilt_deviation", 0.0),
            "tilt_rate": backend_features.get("tilt_rate", 0.0),
            "rolling_tilt_mean": backend_features.get("rolling_mean_tilt", 0.0),
            "rolling_tilt_std": backend_features.get("rolling_std_tilt", 0.0),
            "vibration_intensity": backend_features.get("vibration_intensity", 0.0) * scale,
            "vibration_event_count": backend_features.get("vibration_event_count", 0),
            "vibration_frequency": backend_features.get("vibration_frequency", 0.0),
            "rolling_vibration_mean": backend_features.get("rolling_mean_vib", 0.0) * scale,
            "rolling_vibration_std": backend_features.get("rolling_std_vib", 0.0) * scale,
            "trend_slope": backend_features.get("trend_slope", 0.0),
        }
