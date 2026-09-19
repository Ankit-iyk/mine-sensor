"""
SUBSENSE — Mock Anomaly Detection Model (Phase 8)

Provides a mock implementation of AnomalyDetector adhering strictly to ml-contract/README.md.
Used during development and testing before the trained ML model is delivered.
Supports:
1. Static Mode: Returns fixed anomaly_score=0.05, state="NORMAL" (per contract spec).
2. Dynamic Mode: Evaluates extracted features against physical precursor thresholds
   so simulation scenarios (progressive tilt, micro tremors) produce realistic anomalies.
"""

from typing import Any, Optional
import structlog

from app.ml.interface import AnomalyDetector, AnomalyInferenceOutput

logger = structlog.get_logger(__name__)


class MockAnomalyDetector(AnomalyDetector):
    """
    Mock anomaly detector implementing the SUBSENSE ML interface.
    """

    def __init__(self, version: str = "mock-0.1.0", dynamic_heuristic: bool = True) -> None:
        self._version = version
        self.dynamic_heuristic = dynamic_heuristic
        self._loaded_path: Optional[str] = None

    @property
    def version(self) -> str:
        return self._version

    def load(self, path: str) -> None:
        """Simulate loading a model file."""
        self._loaded_path = path
        logger.info("mock_model_loaded", path=path, version=self._version)

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Run mock inference on input features.
        """
        if not self.dynamic_heuristic:
            # Pure fixed contract behavior
            output = AnomalyInferenceOutput(
                anomaly_score=0.05,
                state="NORMAL",
                model_version=self._version,
                confidence=0.99,
                raw_score=0.05,
            )
            return output.to_dict()

        # Dynamic heuristic mode: computes score based on precursor signals
        tilt_rate = float(features.get("tilt_rate", 0.0))
        tilt_dev = float(features.get("tilt_deviation", 0.0))
        persistence = float(features.get("persistence", 0.0))
        vib_intensity = float(features.get("vibration_intensity", 0.0))
        trend_slope = abs(float(features.get("trend_slope", 0.0)))

        # Rate component: normal rate < 0.02 deg/s, critical > 0.10 deg/s
        rate_component = min(1.0, tilt_rate / 0.10)
        # Deviation component: normal < 0.2 deg, critical > 1.5 deg
        dev_component = min(1.0, tilt_dev / 1.50)
        # Slope component: accelerating climb
        slope_component = min(1.0, trend_slope / 0.05)

        # Weighted composite precursor anomaly score
        raw_score = (
            0.35 * rate_component
            + 0.25 * dev_component
            + 0.20 * persistence
            + 0.10 * slope_component
            + 0.10 * vib_intensity
        )

        score = round(float(min(1.0, max(0.02, raw_score))), 4)
        state = self.classify_score(score)
        confidence = round(float(0.80 + 0.18 * (1.0 - abs(score - 0.5) * 2)), 2)

        output = AnomalyInferenceOutput(
            anomaly_score=score,
            state=state,
            model_version=self._version,
            confidence=confidence,
            raw_score=raw_score,
        )
        return output.to_dict()
