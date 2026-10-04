"""
SUBSENSE — Explainable Composite Risk Engine (Phase 11)

Fuses all intelligence layers into a single 0–100 Risk Score:
  Risk = f(ML Anomaly, Ground Stability Fingerprint, Temporal Precursors, Spatial Correlation)

Classification:
  - 0.0  to 39.9 : SAFE       (green)
  - 40.0 to 69.9 : WARNING    (yellow/amber)
  - 70.0 to 100.0: DANGER     (red)

Trend:
  - STABLE
  - ESCALATING
  - IMPROVING
  - FLUCTUATING
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import numpy as np

from app.processing.schemas import FeatureVector
from app.processing.fingerprint import GroundStabilityFingerprint
from app.intelligence.temporal import TemporalPrecursorAssessment
from app.intelligence.spatial import SpatialCorrelationAssessment


@dataclass
class RiskAssessment:
    """Output of the risk evaluation engine."""
    node_id: str
    zone_id: str
    timestamp: datetime
    risk_score: float        # 0.0 to 100.0
    state: str               # SAFE | WARNING | DANGER
    trend: str               # STABLE | ESCALATING | IMPROVING | FLUCTUATING
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "zone_id": self.zone_id,
            "timestamp": self.timestamp.isoformat(),
            "risk_score": self.risk_score,
            "state": self.state,
            "trend": self.trend,
            "reasons": self.reasons,
        }


class RiskEngine:
    """
    Computes explainable composite risk scores and monitors trends across time.
    """

    SAFE_MAX: float = 39.9
    WARNING_MAX: float = 69.9

    def __init__(self) -> None:
        # History of recent risk scores per node: node_id -> deque of (timestamp, score)
        self._score_history: dict[str, deque[tuple[datetime, float]]] = {}

    def evaluate_risk(
        self,
        node_id: str,
        zone_id: str,
        timestamp: datetime,
        features: FeatureVector,
        fingerprint: GroundStabilityFingerprint,
        anomaly_output: dict[str, Any],
        temporal: TemporalPrecursorAssessment,
        spatial: SpatialCorrelationAssessment,
    ) -> RiskAssessment:
        anomaly_score = float(anomaly_output.get("anomaly_score", 0.0))
        stability_index = float(fingerprint.stability_index)
        instability = 1.0 - stability_index
        precursor_score = float(temporal.precursor_score)
        spatial_index = float(spatial.spatial_correlation_index)

        # ── 1. Base Physical Risk ────────────────────
        base_risk = 100.0 * (
            0.35 * instability
            + 0.35 * precursor_score
            + 0.30 * anomaly_score
        )

        # ── 2. Spatial Verification Adjustment ───────
        reasons: list[str] = []

        if spatial.is_multi_node_event:
            # Multi-node confirmed: amplify risk score
            amplification = 1.0 + 0.30 * spatial_index
            risk_score = min(100.0, base_risk * amplification)
            reasons.append(
                f"Multi-node subsidence confirmed across {len(spatial.affected_neighbors) + 1} "
                f"nodes in zone {zone_id} ({', '.join([node_id] + spatial.affected_neighbors)})"
            )
        elif anomaly_score >= 0.60 and not spatial.is_multi_node_event:
            # Single-node disturbance: damp risk to filter out isolated false alarms
            risk_score = base_risk * 0.65
            reasons.append(
                f"Single-node localized movement on {node_id} unconfirmed by neighbors "
                f"(isolated false alarm protection active)"
            )
        else:
            risk_score = base_risk

        risk_score = round(max(0.0, min(100.0, risk_score)), 1)

        # ── 3. Compile Diagnostic Reasons ───────────
        if temporal.stage in ("ACCELERATING_PRECURSOR", "IMMINENT_COLLAPSE_WARNING"):
            reasons.append(
                f"Accelerating angular displacement detected (+{temporal.tilt_acceleration:.4f} deg/s²)"
            )

        if features.tilt_deviation >= 0.50:
            reasons.append(f"Cumulative tilt deviation ({features.tilt_deviation:.2f}°) exceeds baseline")

        if features.tilt_rate >= 0.04:
            reasons.append(f"Rapid tilt velocity ({features.tilt_rate:.3f} deg/s)")

        if temporal.tremor_cluster_density >= 0.50:
            reasons.append("Elevated micro-seismic fracture clustering in strata")

        if not reasons:
            reasons.append("Ground conditions nominal. No precursor or spatial correlation detected.")

        # ── 4. Classify State ────────────────────────
        if risk_score > self.WARNING_MAX:
            state = "DANGER"
        elif risk_score > self.SAFE_MAX:
            state = "WARNING"
        else:
            state = "SAFE"

        # ── 5. Trend Analysis ────────────────────────
        if node_id not in self._score_history:
            self._score_history[node_id] = deque(maxlen=30)
        history = self._score_history[node_id]

        trend = "STABLE"
        if len(history) >= 4:
            recent_scores = [h[1] for h in history]
            delta = risk_score - recent_scores[0]
            std_dev = float(np.std(recent_scores))

            if std_dev > 10.0:
                trend = "FLUCTUATING"
            elif delta >= 5.0:
                trend = "ESCALATING"
            elif delta <= -5.0:
                trend = "IMPROVING"
            else:
                trend = "STABLE"

        history.append((timestamp, risk_score))

        return RiskAssessment(
            node_id=node_id,
            zone_id=zone_id,
            timestamp=timestamp,
            risk_score=risk_score,
            state=state,
            trend=trend,
            reasons=reasons,
        )

    def reset(self) -> None:
        self._score_history.clear()


# Global singleton instance
risk_engine = RiskEngine()
