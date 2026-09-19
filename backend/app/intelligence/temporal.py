"""
SUBSENSE — Temporal & Precursor Analysis Engine (Phase 9)

Implements geotechnical precursor detection for mine ground stability:
1. Angular Acceleration (d²θ/dt²): Identifies non-linear accelerating displacement
   which precedes tertiary rock mass failure and roof collapses.
2. Cumulative Plastic Drift: Integrates continuous displacement over rolling horizons.
3. Micro-Tremor Event Clustering: Evaluates seismic event inter-arrival frequency
   (clustering density indicates progressive micro-fracturing in strata).
4. Precursor Stage Classification:
   - NONE
   - CREEP_DETECTED
   - ACCELERATING_PRECURSOR
   - IMMINENT_COLLAPSE_WARNING
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Optional

from app.processing.schemas import FeatureVector


@dataclass
class TemporalPrecursorAssessment:
    """Precursor assessment output for a single sensor node."""
    node_id: str
    timestamp: datetime
    tilt_rate: float               # current angular velocity (deg/s)
    tilt_acceleration: float       # angular acceleration (deg/s²)
    cumulative_drift: float        # cumulative integrated displacement (deg)
    tremor_cluster_density: float  # micro-tremor clustering density [0.0, 1.0]
    precursor_score: float         # composite precursor risk score [0.0, 1.0]
    stage: str                     # NONE | CREEP_DETECTED | ACCELERATING_PRECURSOR | IMMINENT_COLLAPSE_WARNING
    explanations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp.isoformat(),
            "tilt_rate": self.tilt_rate,
            "tilt_acceleration": self.tilt_acceleration,
            "cumulative_drift": self.cumulative_drift,
            "tremor_cluster_density": self.tremor_cluster_density,
            "precursor_score": self.precursor_score,
            "stage": self.stage,
            "explanations": self.explanations,
        }


class NodeTemporalTracker:
    """Tracks temporal history and velocity derivatives for a single node."""

    def __init__(self, node_id: str, history_len: int = 120) -> None:
        self.node_id = node_id
        self.history_len = history_len

        # Deque of (timestamp, tilt_rate, tilt_deviation, vibration_intensity)
        self._history: deque[tuple[datetime, float, float, float]] = deque(maxlen=history_len)

        # Micro-tremor event timestamps
        self._tremor_events: deque[datetime] = deque(maxlen=50)

    def update(self, features: FeatureVector) -> TemporalPrecursorAssessment:
        ts = features.timestamp
        current_rate = float(features.tilt_rate)
        current_dev = float(features.tilt_deviation)
        current_vib = float(features.vibration_intensity)

        # Record micro-tremor if vibration exceeds 0.30
        if current_vib >= 0.30:
            self._tremor_events.append(ts)

        # ── 1. Calculate Angular Acceleration (d²θ/dt²) ─
        acceleration = 0.0
        if len(self._history) >= 2:
            # Finite difference over last few seconds for stability
            prev_ts, prev_rate, _, _ = self._history[-1]
            dt = max(0.5, (ts - prev_ts).total_seconds())
            acceleration = (current_rate - prev_rate) / dt

        self._history.append((ts, current_rate, current_dev, current_vib))

        # ── 2. Cumulative Plastic Drift (Integral of deviation) ─
        # Sum of displacement over recent history
        if len(self._history) >= 2:
            cumulative_drift = round(float(sum(h[2] for h in self._history) / len(self._history)), 4)
        else:
            cumulative_drift = current_dev

        # ── 3. Micro-Tremor Event Clustering Density ──
        # Evaluates frequency of micro-tremors within the last 60 seconds
        recent_tremors = 0
        for ev_ts in self._tremor_events:
            if (ts - ev_ts).total_seconds() <= 60.0:
                recent_tremors += 1

        # Normalized tremor cluster density: 6+ tremors in 60s is high density (1.0)
        tremor_cluster_density = min(1.0, recent_tremors / 6.0)

        # ── 4. Precursor Score & Stage Classification ──
        explanations = []

        # Acceleration penalty: >0.01 deg/s² is accelerating, >0.03 deg/s² is critical
        accel_component = 0.0
        if acceleration > 0.002:
            accel_component = min(1.0, acceleration / 0.03)
            explanations.append(f"Angular displacement accelerating at +{acceleration:.4f} deg/s²")

        # Velocity component
        rate_component = min(1.0, current_rate / 0.08)
        if current_rate >= 0.03:
            explanations.append(f"Elevated tilt velocity ({current_rate:.3f} deg/s)")

        # Drift component
        drift_component = min(1.0, cumulative_drift / 1.50)
        if cumulative_drift >= 0.50:
            explanations.append(f"Persistent cumulative ground displacement ({cumulative_drift:.2f} deg)")

        # Tremor clustering
        if tremor_cluster_density >= 0.50:
            explanations.append(f"High micro-seismic fracture recurrence ({recent_tremors} tremors in 60s)")

        # Composite precursor risk score
        precursor_score = round(
            min(
                1.0,
                0.35 * accel_component
                + 0.30 * rate_component
                + 0.20 * drift_component
                + 0.15 * tremor_cluster_density,
            ),
            4,
        )

        # Classify Stage
        if precursor_score >= 0.70 or (acceleration > 0.02 and current_rate > 0.05):
            stage = "IMMINENT_COLLAPSE_WARNING"
        elif precursor_score >= 0.45 or acceleration > 0.008:
            stage = "ACCELERATING_PRECURSOR"
        elif precursor_score >= 0.20 or current_rate > 0.02:
            stage = "CREEP_DETECTED"
        else:
            stage = "NONE"

        return TemporalPrecursorAssessment(
            node_id=self.node_id,
            timestamp=ts,
            tilt_rate=current_rate,
            tilt_acceleration=round(acceleration, 5),
            cumulative_drift=cumulative_drift,
            tremor_cluster_density=round(tremor_cluster_density, 3),
            precursor_score=precursor_score,
            stage=stage,
            explanations=explanations,
        )


class TemporalAnalysisEngine:
    """Manages temporal precursor trackers across all nodes."""

    def __init__(self) -> None:
        self._trackers: dict[str, NodeTemporalTracker] = {}

    def analyze_node(self, features: FeatureVector) -> TemporalPrecursorAssessment:
        if features.node_id not in self._trackers:
            self._trackers[features.node_id] = NodeTemporalTracker(features.node_id)
        return self._trackers[features.node_id].update(features)

    def reset(self) -> None:
        self._trackers.clear()


# Global singleton instance
temporal_engine = TemporalAnalysisEngine()
