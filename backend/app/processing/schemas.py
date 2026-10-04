"""
SUBSENSE — Processing Schemas & Data Structures (Phase 5 & 6)
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Optional


@dataclass
class ProcessedSample:
    """A single denoised and timestamped sensor sample in the window."""
    timestamp: datetime
    raw_tilt_x: float
    raw_tilt_y: float
    tilt_x: float          # filtered angle
    tilt_y: float          # filtered angle
    rate_x: float          # angular velocity deg/s
    rate_y: float          # angular velocity deg/s
    tilt_magnitude: float  # sqrt(tilt_x^2 + tilt_y^2)
    vibration: int         # 0-1023 ADC
    vibration_norm: float  # 0.0 - 1.0
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 9.81
    accel_magnitude: float = 9.81


@dataclass
class FeatureVector:
    """
    Extracted feature vector adhering strictly to ml-contract/README.md
    with extensions for Phase 3 runtime storage and processing.
    """
    node_id: str
    timestamp: datetime

    # Tilt features
    tilt_x: float
    tilt_y: float
    tilt_deviation: float
    tilt_rate: float

    # Vibration features
    vibration_raw: int
    vibration_intensity: float
    vibration_frequency: float

    # Rolling statistics
    rolling_mean_tilt: float
    rolling_std_tilt: float
    rolling_mean_vib: float
    rolling_std_vib: float

    # Temporal features
    persistence: float
    trend_slope: float

    # Extended Phase 3 features (with backward-compatible defaults)
    tilt_magnitude: float = 0.0
    accel_magnitude: float = 9.81
    accel_mean: float = 9.81
    accel_std: float = 0.05
    accel_peak: float = 9.85
    vibration_mean: float = 0.05
    vibration_std: float = 0.02
    vibration_event_count: int = 0
    vibration_persistence: float = 0.0
    baseline_deviation: float = 0.0
    zone_id: Optional[str] = None
    processing_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict matching ML model contract."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data



@dataclass
class NodeStabilityResult:
    """Consolidated node state produced by the intelligence pipeline."""
    node_id: str
    timestamp: datetime
    features: FeatureVector
    fingerprint: dict[str, Any]
    anomaly: dict[str, Any]
    temporal: Optional[dict[str, Any]] = None
    spatial: Optional[dict[str, Any]] = None
    risk: Optional[dict[str, Any]] = None     # RiskAssessment.to_dict()
    alert: Optional[dict[str, Any]] = None    # AlertEvent.to_dict() or None

    @property
    def tilt_rate(self) -> float:
        return self.features.tilt_rate

    @property
    def trend_slope(self) -> float:
        return self.features.trend_slope

    @property
    def tilt_deviation(self) -> float:
        return self.features.tilt_deviation

    @property
    def anomaly_score(self) -> float:
        return float(self.anomaly["anomaly_score"])

    @property
    def state(self) -> str:
        return str(self.anomaly["state"])


