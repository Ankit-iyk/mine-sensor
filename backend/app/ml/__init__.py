"""SUBSENSE ML Package."""
from app.ml.interface import AnomalyDetector, AnomalyInferenceOutput
from app.ml.mock_model import MockAnomalyDetector
from app.ml.loader import get_detector, set_detector

__all__ = [
    "AnomalyDetector",
    "AnomalyInferenceOutput",
    "MockAnomalyDetector",
    "get_detector",
    "set_detector",
]
