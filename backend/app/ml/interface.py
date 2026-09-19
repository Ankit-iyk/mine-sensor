"""
SUBSENSE — ML Model Integration Interface (Phase 8)

Adheres strictly to ml-contract/README.md.
Defines the abstract interface that any model (mock, IsolationForest, OneClassSVM, Autoencoder)
must implement to be hot-swapped into the SUBSENSE intelligence pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class AnomalyInferenceOutput:
    """Standardized output structure for ML inference."""
    anomaly_score: float     # 0.0 to 1.0 (higher = more anomalous)
    state: str               # "NORMAL" | "MICRO_ANOMALY" | "ANOMALOUS"
    model_version: str       # for traceability in database & logs
    confidence: Optional[float] = None
    raw_score: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "anomaly_score": self.anomaly_score,
            "state": self.state,
            "model_version": self.model_version,
            "confidence": self.confidence,
            "raw_score": self.raw_score,
        }


class AnomalyDetector(ABC):
    """
    Abstract base class for all SUBSENSE anomaly detection models.
    """

    # Configurable classification thresholds
    THRESHOLD_NORMAL: float = 0.30
    THRESHOLD_ANOMALY: float = 0.60

    @abstractmethod
    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Run inference on a single feature vector dictionary.

        Parameters
        ----------
        features : dict containing feature vector (matching ml-contract schema)

        Returns
        -------
        dict containing:
            - anomaly_score: float in [0.0, 1.0]
            - state: "NORMAL" | "MICRO_ANOMALY" | "ANOMALOUS"
            - model_version: str
            - confidence: float, optional
            - raw_score: float, optional
        """
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        """Load trained model weights / pipelines from disk."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Return model version string."""
        pass

    def classify_score(self, score: float) -> str:
        """Map a 0.0-1.0 anomaly score to standard state string."""
        if score < self.THRESHOLD_NORMAL:
            return "NORMAL"
        elif score < self.THRESHOLD_ANOMALY:
            return "MICRO_ANOMALY"
        else:
            return "ANOMALOUS"
