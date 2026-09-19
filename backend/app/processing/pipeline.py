"""
SUBSENSE — Unified Signal Processing & Feature Extraction Pipeline (Phases 5–13)

Pipeline flow per telemetry message:
  Raw Reading
  → Kalman Filter (denoises tilt angles, computes angular velocity)
  → Node Buffer (updates temporal window & baseline)
  → Feature Extractor (computes statistical, spectral & temporal features)
  → Ground Stability Fingerprint (multi-dimensional stability grading)
  → ML Anomaly Detection (heuristic MockAnomalyDetector or real model)
  → Temporal Precursor Analysis (Phase 9)
  → Spatial Correlation Engine (Phase 10)
  → Risk Engine (Phase 11 — fused 0–100 risk score)
  → Alert Engine (Phases 12/13 — debounced incidents & broadcast)
  → Database Persistence (features, anomalies, risk, incidents)
  → Returns NodeStabilityResult for REST / WebSocket consumers
"""

import math
import threading
from typing import Optional
import structlog

from app.config import settings
from app.ingestion.schemas import TelemetryReading
from app.processing.filters import NodeTiltFilter
from app.processing.buffer import NodeBuffer, ProcessedSample
from app.processing.baseline import NodeBaselineTracker
from app.processing.extractor import FeatureExtractor
from app.processing.schemas import FeatureVector, NodeStabilityResult

logger = structlog.get_logger(__name__)


class ProcessingPipeline:
    """
    Coordinates signal processing and feature extraction across all sensing nodes.
    Thread-safe for multi-threaded MQTT ingestion.
    """

    def __init__(
        self,
        window_size: int = settings.feature_window_size,
        q_angle: float = settings.kalman_q_angle,
        q_rate: float = settings.kalman_q_rate,
        r_measure: float = settings.kalman_r_measure,
        persist_to_db: bool = True,
    ) -> None:
        self.window_size = window_size
        self.q_angle = q_angle
        self.q_rate = q_rate
        self.r_measure = r_measure
        self.persist_to_db = persist_to_db

        self._lock = threading.Lock()
        self._filters: dict[str, NodeTiltFilter] = {}
        self._buffers: dict[str, NodeBuffer] = {}
        self._baselines: dict[str, NodeBaselineTracker] = {}
        self._extractor = FeatureExtractor()

    def _get_or_create_node_state(
        self, node_id: str
    ) -> tuple[NodeTiltFilter, NodeBuffer, NodeBaselineTracker]:
        with self._lock:
            if node_id not in self._filters:
                self._filters[node_id] = NodeTiltFilter(
                    node_id=node_id,
                    q_angle=self.q_angle,
                    q_rate=self.q_rate,
                    r_measure=self.r_measure,
                )
            if node_id not in self._buffers:
                self._buffers[node_id] = NodeBuffer(
                    node_id=node_id,
                    max_size=self.window_size,
                )
            if node_id not in self._baselines:
                self._baselines[node_id] = NodeBaselineTracker(node_id=node_id)
            return self._filters[node_id], self._buffers[node_id], self._baselines[node_id]

    def process_reading(self, reading: TelemetryReading) -> Optional[NodeStabilityResult]:
        """
        Process a single validated sensor reading through the full intelligence stack.
        Returns None until the rolling window has enough samples.
        """
        tilt_filter, node_buffer, baseline_tracker = self._get_or_create_node_state(reading.node_id)

        # ── 1. Kalman Filtering ──────────────────────
        est_x, est_y = tilt_filter.filter_sample(
            raw_tilt_x=reading.tilt_x,
            raw_tilt_y=reading.tilt_y,
            timestamp=reading.timestamp,
        )

        tilt_mag = math.sqrt(est_x.angle**2 + est_y.angle**2)
        vib_norm = min(1.0, max(0.0, reading.vibration / 1023.0))

        sample = ProcessedSample(
            timestamp=reading.timestamp,
            raw_tilt_x=reading.tilt_x,
            raw_tilt_y=reading.tilt_y,
            tilt_x=est_x.angle,
            tilt_y=est_y.angle,
            rate_x=est_x.rate,
            rate_y=est_y.rate,
            tilt_magnitude=tilt_mag,
            vibration=reading.vibration,
            vibration_norm=vib_norm,
        )

        # ── 2. Buffer & Temporal State Update ────────
        node_buffer.add_sample(sample)

        # ── 2b. Baseline Observation ─────────────────
        baseline_tracker.observe(
            tilt_x=est_x.angle,
            tilt_y=est_y.angle,
            vibration=float(reading.vibration),
        )

        # ── 3. Feature Extraction ────────────────────
        features = self._extractor.extract(
            node_buffer,
            baseline_tracker=baseline_tracker,
            zone_id=reading.zone_id,
        )
        if features is None:
            logger.debug(
                "buffering_insufficient_samples",
                node_id=reading.node_id,
                current_samples=node_buffer.size,
            )
            return None

        # ── 4. Ground Stability Fingerprint ──────────
        from app.processing.fingerprint import stability_engine
        fingerprint = stability_engine.compute_fingerprint(features)

        # ── 5. ML Anomaly Detection ──────────────────
        from app.ml.loader import get_detector
        detector = get_detector()
        anomaly_output = detector.predict(features.to_dict())

        # ── 6. Temporal Precursor Analysis ───────────
        from app.intelligence.temporal import temporal_engine
        temporal_assessment = temporal_engine.analyze_node(features)

        # ── 7. Spatial Correlation Engine ────────────
        from app.intelligence.spatial import spatial_engine
        spatial_assessment = spatial_engine.update_node_state(
            node_id=reading.node_id,
            zone_id=reading.zone_id,
            timestamp=reading.timestamp,
            anomaly_score=anomaly_output["anomaly_score"],
            state=anomaly_output["state"],
            tilt_x=features.tilt_x,
            tilt_y=features.tilt_y,
            precursor_score=temporal_assessment.precursor_score,
        )

        # ── 8. Risk Engine ───────────────────────────
        from app.intelligence.risk_engine import risk_engine
        risk_assessment = risk_engine.evaluate_risk(
            node_id=reading.node_id,
            zone_id=reading.zone_id,
            timestamp=reading.timestamp,
            features=features,
            fingerprint=fingerprint,
            anomaly_output=anomaly_output,
            temporal=temporal_assessment,
            spatial=spatial_assessment,
        )

        # ── 9. Alert Engine ──────────────────────────
        from app.intelligence.alerts import alert_engine
        alert_event = alert_engine.process_risk(
            risk=risk_assessment,
            affected_nodes=spatial_assessment.affected_neighbors or None,
        )

        # ── 10. Persist to Database ──────────────────
        if self.persist_to_db:
            from app.db.repositories.features import save_feature_safe
            from app.db.repositories.anomalies import save_anomaly_safe
            from app.db.repositories.risk import save_risk_safe
            save_feature_safe(features)
            save_anomaly_safe(reading.node_id, reading.timestamp, anomaly_output)
            save_risk_safe(
                node_id=reading.node_id,
                zone_id=reading.zone_id,
                timestamp=reading.timestamp,
                risk_score=risk_assessment.risk_score,
                state=risk_assessment.state,
                trend=risk_assessment.trend,
                reasons=risk_assessment.reasons,
            )

        logger.info(
            "stability_inferred",
            node_id=features.node_id,
            anomaly_score=anomaly_output["anomaly_score"],
            state=anomaly_output["state"],
            stability_grade=fingerprint.stability_grade,
            precursor_stage=temporal_assessment.stage,
            spatial_scope=spatial_assessment.event_scope,
            risk_score=risk_assessment.risk_score,
            risk_state=risk_assessment.state,
            alert_fired=alert_event is not None,
        )

        return NodeStabilityResult(
            node_id=reading.node_id,
            timestamp=reading.timestamp,
            features=features,
            fingerprint=fingerprint.to_dict(),
            anomaly=anomaly_output,
            temporal=temporal_assessment.to_dict(),
            spatial=spatial_assessment.to_dict(),
            risk=risk_assessment.to_dict(),
            alert=alert_event.to_dict() if alert_event else None,
        )

    def reset_node(self, node_id: str) -> None:
        """Reset filter, buffer, and baseline for a specific node (e.g. after maintenance)."""
        with self._lock:
            self._filters.pop(node_id, None)
            self._buffers.pop(node_id, None)
            self._baselines.pop(node_id, None)


# Shared global pipeline instance
pipeline = ProcessingPipeline()
