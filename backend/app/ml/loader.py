"""
SUBSENSE — ML Model Loader & Factory (Phase 8)

Instantiates the active AnomalyDetector implementation:
- If a model file is specified in ML_MODEL_PATH and exists on disk, attempts to load it.
- Otherwise falls back cleanly to MockAnomalyDetector.
"""

import os
from typing import Optional
import structlog

from app.config import settings
from app.ml.interface import AnomalyDetector
from app.ml.mock_model import MockAnomalyDetector

logger = structlog.get_logger(__name__)

_ACTIVE_DETECTOR: Optional[AnomalyDetector] = None


def get_detector() -> AnomalyDetector:
    """
    Return the singleton AnomalyDetector instance.
    """
    global _ACTIVE_DETECTOR
    if _ACTIVE_DETECTOR is not None:
        return _ACTIVE_DETECTOR

    model_path = settings.ml_model_path
    if model_path and os.path.isfile(model_path):
        try:
            # Future scikit-learn / joblib loader
            logger.info("loading_ml_model_from_disk", path=model_path)
            # When ML teammate provides model, SklearnAnomalyDetector loads it here
            detector = MockAnomalyDetector(version=settings.ml_model_version)
            detector.load(model_path)
            _ACTIVE_DETECTOR = detector
            return _ACTIVE_DETECTOR
        except Exception as exc:
            logger.error("failed_to_load_ml_model", path=model_path, error=str(exc))
            logger.info("fallback_to_mock_detector")

    _ACTIVE_DETECTOR = MockAnomalyDetector(version=settings.ml_model_version)
    logger.info("using_mock_detector", version=_ACTIVE_DETECTOR.version)
    return _ACTIVE_DETECTOR


def set_detector(detector: AnomalyDetector) -> None:
    """Explicitly inject a detector instance (useful for testing)."""
    global _ACTIVE_DETECTOR
    _ACTIVE_DETECTOR = detector
