"""
SUBSENSE — Ground Stability Fingerprint Engine (Phase 7)

Transforms raw features and physical measurements into a multi-dimensional
Ground Stability Fingerprint.

The Fingerprint characterizes:
- Tilt Stability Index [0.0, 1.0] (angular displacement & velocity)
- Vibration Stability Index [0.0, 1.0] (seismic energy & spike recurrence)
- Creep / Drift Stability [0.0, 1.0] (continuous trend slope)
- Temporal Persistence Stability [0.0, 1.0] (short-lived transient vs permanent change)
- Composite Ground Stability Index [0.0, 1.0] (1.0 = rock solid, 0.0 = imminent subsidence)

Provides radar/spider-chart ready stability vectors for the UI dashboard.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any
import math

from app.processing.schemas import FeatureVector


@dataclass
class GroundStabilityFingerprint:
    """
    Multi-dimensional stability profile of the ground at a sensor node location.
    """
    node_id: str
    timestamp: datetime

    # Component stability indices (1.0 = perfectly stable, 0.0 = critical instability)
    tilt_stability: float
    vibration_stability: float
    creep_stability: float
    persistence_stability: float

    # Composite stability index (0.0 to 1.0)
    stability_index: float

    # Qualitative classification
    stability_grade: str   # "STABLE" | "WATCH" | "UNSTABLE" | "CRITICAL"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class GroundStabilityEngine:
    """
    Evaluates physical ground stability metrics from extracted feature vectors.
    """

    # Physical thresholds based on geotechnical mine subsidence criteria
    MAX_ALLOWABLE_TILT_DEG: float = 2.0     # 2 degrees permanent tilt is severe
    MAX_ALLOWABLE_RATE_DEG_S: float = 0.08  # 0.08 deg/s rate indicates rapid movement

    def compute_fingerprint(self, features: FeatureVector) -> GroundStabilityFingerprint:
        """
        Compute the Ground Stability Fingerprint from a feature vector.
        """
        # ── 1. Tilt Stability (Angular displacement & velocity) ─
        # Combines deviation from baseline and angular rate
        dev_penalty = min(1.0, features.tilt_deviation / self.MAX_ALLOWABLE_TILT_DEG)
        rate_penalty = min(1.0, features.tilt_rate / self.MAX_ALLOWABLE_RATE_DEG_S)
        tilt_stability = round(max(0.0, 1.0 - (0.6 * dev_penalty + 0.4 * rate_penalty)), 4)

        # ── 2. Vibration Stability (Energy & event frequency) ──
        # Combines normalized vibration intensity and spike event frequency
        vib_intensity_penalty = min(1.0, features.vibration_intensity / 0.8)
        vib_freq_penalty = min(1.0, features.vibration_frequency / 0.5)
        vibration_stability = round(max(0.0, 1.0 - (0.5 * vib_intensity_penalty + 0.5 * vib_freq_penalty)), 4)

        # ── 3. Creep Stability (Persistent trend slope) ─────────
        # Trend slope in deg/s across the window
        slope_penalty = min(1.0, abs(features.trend_slope) / 0.04)
        creep_stability = round(max(0.0, 1.0 - slope_penalty), 4)

        # ── 4. Persistence Stability (Anomalous fraction) ───────
        persistence_penalty = min(1.0, features.persistence)
        persistence_stability = round(max(0.0, 1.0 - persistence_penalty), 4)

        # ── 5. Composite Ground Stability Index ─────────────────
        # Weighted geometric/arithmetic blend prioritizing tilt and persistence
        composite = (
            0.40 * tilt_stability
            + 0.25 * persistence_stability
            + 0.20 * creep_stability
            + 0.15 * vibration_stability
        )
        stability_index = round(float(min(1.0, max(0.0, composite))), 4)

        # ── 6. Qualitative Grade ────────────────────────────────
        if stability_index >= 0.80:
            stability_grade = "STABLE"
        elif stability_index >= 0.60:
            stability_grade = "WATCH"
        elif stability_index >= 0.35:
            stability_grade = "UNSTABLE"
        else:
            stability_grade = "CRITICAL"

        return GroundStabilityFingerprint(
            node_id=features.node_id,
            timestamp=features.timestamp,
            tilt_stability=tilt_stability,
            vibration_stability=vibration_stability,
            creep_stability=creep_stability,
            persistence_stability=persistence_stability,
            stability_index=stability_index,
            stability_grade=stability_grade,
        )


# Global singleton instance
stability_engine = GroundStabilityEngine()
