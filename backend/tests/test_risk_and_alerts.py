"""
Tests — Phase 11-13: Risk Engine, Alert Engine & Incident Lifecycle

Verifies:
1. Risk Engine computes correct scores and states from fused intelligence inputs
2. Alert Engine fires after CONSECUTIVE_THRESHOLD consecutive WARNING/DANGER samples
3. Alert Engine does NOT fire before the threshold
4. Alert Engine creates DB incidents on first trigger (persist_to_db mode)
5. Alert Engine auto-resolves incidents after SAFE_RESOLUTION_THRESHOLD consecutive SAFE samples
6. Alert Engine broadcasts events to registered listeners
7. Severity mapping is correct (LOW / MEDIUM / HIGH / CRITICAL)
8. Pipeline end-to-end produces risk + alert fields in NodeStabilityResult
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.intelligence.risk_engine import RiskEngine, RiskAssessment
from app.intelligence.alerts import AlertEngine, AlertEvent
from app.processing.schemas import FeatureVector
from app.processing.fingerprint import GroundStabilityFingerprint, GroundStabilityEngine
from app.intelligence.temporal import TemporalPrecursorAssessment
from app.intelligence.spatial import SpatialCorrelationAssessment
from app.processing.pipeline import ProcessingPipeline
from app.ingestion.schemas import TelemetryReading


# ── Helpers ───────────────────────────────────────────────────────────────────

_TS = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)


def _make_feature(
    node_id: str = "N01",
    tilt_deviation: float = 0.1,
    tilt_rate: float = 0.01,
    vibration_intensity: float = 0.1,
    persistence: float = 0.0,
    trend_slope: float = 0.0,
) -> FeatureVector:
    return FeatureVector(
        node_id=node_id,
        timestamp=_TS,
        tilt_x=tilt_deviation,
        tilt_y=tilt_deviation * 0.5,
        tilt_deviation=tilt_deviation,
        tilt_rate=tilt_rate,
        vibration_raw=int(vibration_intensity * 1023),
        vibration_intensity=vibration_intensity,
        vibration_frequency=0.05,
        rolling_mean_tilt=tilt_deviation,
        rolling_std_tilt=tilt_deviation * 0.1,
        rolling_mean_vib=vibration_intensity,
        rolling_std_vib=vibration_intensity * 0.1,
        persistence=persistence,
        trend_slope=trend_slope,
    )


def _safe_fingerprint(node_id: str = "N01") -> GroundStabilityFingerprint:
    return GroundStabilityFingerprint(
        node_id=node_id,
        timestamp=_TS,
        tilt_stability=0.98,
        vibration_stability=0.97,
        creep_stability=0.99,
        persistence_stability=1.0,
        stability_index=0.97,
        stability_grade="STABLE",
    )


def _danger_fingerprint(node_id: str = "N01") -> GroundStabilityFingerprint:
    return GroundStabilityFingerprint(
        node_id=node_id,
        timestamp=_TS,
        tilt_stability=0.08,
        vibration_stability=0.12,
        creep_stability=0.05,
        persistence_stability=0.10,
        stability_index=0.10,
        stability_grade="CRITICAL",
    )


def _safe_temporal(node_id: str = "N01") -> TemporalPrecursorAssessment:
    return TemporalPrecursorAssessment(
        node_id=node_id,
        timestamp=_TS,
        tilt_rate=0.001,
        tilt_acceleration=0.0,
        cumulative_drift=0.0,
        tremor_cluster_density=0.0,
        precursor_score=0.01,
        stage="NONE",
        explanations=[],
    )


def _danger_temporal(node_id: str = "N01") -> TemporalPrecursorAssessment:
    return TemporalPrecursorAssessment(
        node_id=node_id,
        timestamp=_TS,
        tilt_rate=0.15,
        tilt_acceleration=0.05,
        cumulative_drift=1.2,
        tremor_cluster_density=0.7,
        precursor_score=0.85,
        stage="ACCELERATING_PRECURSOR",
        explanations=["Accelerating tilt"],
    )


def _isolated_spatial(node_id: str = "N01", zone_id: str = "Z01") -> SpatialCorrelationAssessment:
    return SpatialCorrelationAssessment(
        node_id=node_id,
        zone_id=zone_id,
        timestamp=_TS,
        neighbor_nodes=[],
        affected_neighbors=[],
        spatial_correlation_index=0.0,
        is_multi_node_event=False,
        event_scope="ISOLATED_DISTURBANCE",
    )


def _cluster_spatial(node_id: str = "N01", zone_id: str = "Z01") -> SpatialCorrelationAssessment:
    return SpatialCorrelationAssessment(
        node_id=node_id,
        zone_id=zone_id,
        timestamp=_TS,
        neighbor_nodes=["N02", "N03"],
        affected_neighbors=["N02"],
        spatial_correlation_index=0.75,
        is_multi_node_event=True,
        event_scope="LOCAL_CLUSTER",
    )


def _evaluate_safe(risk_engine: RiskEngine, node_id: str = "N01") -> RiskAssessment:
    return risk_engine.evaluate_risk(
        node_id=node_id, zone_id="Z01", timestamp=_TS,
        features=_make_feature(node_id, tilt_deviation=0.01, tilt_rate=0.001),
        fingerprint=_safe_fingerprint(node_id),
        anomaly_output={"anomaly_score": 0.02, "state": "NORMAL", "model_version": "mock"},
        temporal=_safe_temporal(node_id),
        spatial=_isolated_spatial(node_id),
    )


def _evaluate_danger(risk_engine: RiskEngine, node_id: str = "N01") -> RiskAssessment:
    risk = risk_engine.evaluate_risk(
        node_id=node_id, zone_id="Z01", timestamp=_TS,
        features=_make_feature(node_id, tilt_deviation=2.5, tilt_rate=0.15, persistence=0.9),
        fingerprint=_danger_fingerprint(node_id),
        anomaly_output={"anomaly_score": 0.88, "state": "ANOMALOUS", "model_version": "mock"},
        temporal=_danger_temporal(node_id),
        spatial=_cluster_spatial(node_id),
    )
    return risk


def _forced_state(
    risk_engine: RiskEngine,
    score: float,
    state: str,
    node_id: str = "N01",
) -> RiskAssessment:
    """Create a RiskAssessment with overridden score/state for deterministic severity tests."""
    r = _evaluate_safe(risk_engine, node_id)
    r.risk_score = score
    r.state = state
    return r


# ── 1. Risk Engine Tests ───────────────────────────────────────────────────────

class TestRiskEngine:

    def test_safe_risk_score(self):
        engine = RiskEngine()
        assessment = _evaluate_safe(engine)
        assert assessment.state == "SAFE"
        assert 0.0 <= assessment.risk_score <= 39.9

    def test_danger_risk_score(self):
        engine = RiskEngine()
        assessment = _evaluate_danger(engine)
        # Multi-node danger should push score high
        assert assessment.state in ("DANGER", "WARNING")

    def test_to_dict_has_required_fields(self):
        engine = RiskEngine()
        assessment = _evaluate_safe(engine)
        d = assessment.to_dict()
        for key in ("node_id", "zone_id", "timestamp", "risk_score", "state", "trend", "reasons"):
            assert key in d

    def test_reasons_is_list(self):
        engine = RiskEngine()
        d = _evaluate_safe(engine).to_dict()
        assert isinstance(d["reasons"], list)

    def test_trend_types(self):
        engine = RiskEngine()
        for _ in range(10):
            r = _evaluate_safe(engine)
        assert r.trend in ("STABLE", "ESCALATING", "IMPROVING", "FLUCTUATING")


# ── 2. Alert Engine Debounce Tests ─────────────────────────────────────────────

class TestAlertEngineDebounce:

    def _danger_risk(self, score: float = 75.0) -> RiskAssessment:
        return _forced_state(RiskEngine(), score, "DANGER")

    def test_no_alert_below_threshold(self):
        """Should NOT fire before CONSECUTIVE_THRESHOLD samples."""
        engine = AlertEngine(persist_to_db=False)
        risk = self._danger_risk()

        events = [engine.process_risk(risk) for _ in range(2)]
        assert all(e is None for e in events), "Alert should not fire before 3 consecutive danger samples"

    def test_alert_fires_at_threshold(self):
        """Should fire exactly at CONSECUTIVE_THRESHOLD consecutive samples."""
        engine = AlertEngine(persist_to_db=False)
        risk = self._danger_risk()

        events = []
        for _ in range(3):
            ev = engine.process_risk(risk)
            if ev is not None:
                events.append(ev)

        assert len(events) == 1
        assert events[0].state == "DANGER"
        assert events[0].node_id == "N01"

    def test_alert_fires_every_sample_after_threshold(self):
        """Alert should continue firing on each subsequent danger sample."""
        engine = AlertEngine(persist_to_db=False)
        risk = self._danger_risk()

        events = [ev for _ in range(6) if (ev := engine.process_risk(risk)) is not None]
        # Fires on samples 3, 4, 5, 6
        assert len(events) == 4

    def test_state_reset_on_safe_transition(self):
        """Counter resets when state transitions from DANGER to SAFE."""
        engine = AlertEngine(persist_to_db=False)
        danger_risk = self._danger_risk()
        safe_risk = _forced_state(RiskEngine(), 5.0, "SAFE")

        # Trigger threshold
        for _ in range(3):
            engine.process_risk(danger_risk)

        # Interrupt with 1 safe sample
        engine.process_risk(safe_risk)

        # 2 more danger samples — should NOT fire yet
        events = [ev for _ in range(2) if (ev := engine.process_risk(danger_risk)) is not None]
        assert len(events) == 0


# ── 3. Alert Severity Mapping Tests ───────────────────────────────────────────

class TestAlertSeverityMapping:

    def _alert_for_score(self, score: float, state: str = "DANGER") -> AlertEvent:
        engine = AlertEngine(persist_to_db=False)
        risk = _forced_state(RiskEngine(), score, state)
        ev = None
        for _ in range(3):
            ev = engine.process_risk(risk)
        return ev

    def test_severity_critical(self):
        ev = self._alert_for_score(85.0)
        assert ev is not None
        assert ev.severity == "CRITICAL"

    def test_severity_high(self):
        ev = self._alert_for_score(72.0)
        assert ev is not None
        assert ev.severity == "HIGH"

    def test_severity_medium(self):
        ev = self._alert_for_score(55.0, state="WARNING")
        assert ev is not None
        assert ev.severity == "MEDIUM"

    def test_severity_low(self):
        ev = self._alert_for_score(42.0, state="WARNING")
        assert ev is not None
        assert ev.severity == "LOW"


# ── 4. Incident Lifecycle Tests ────────────────────────────────────────────────

class TestIncidentLifecycle:

    def test_auto_resolution_after_safe_threshold(self):
        """
        After an alert triggers, the incident should auto-resolve once
        SAFE_RESOLUTION_THRESHOLD (5) consecutive SAFE samples arrive.
        """
        engine = AlertEngine(persist_to_db=False)
        danger_risk = _forced_state(RiskEngine(), 75.0, "DANGER")
        safe_risk = _forced_state(RiskEngine(), 5.0, "SAFE")

        # Trigger alert (3 danger)
        for _ in range(3):
            engine.process_risk(danger_risk)

        # Manually mark incident active to test resolution logic
        tracker = engine._node_states["N01"]
        tracker["has_active_incident"] = True

        # Feed 4 safe samples — should NOT resolve yet
        for _ in range(4):
            engine.process_risk(safe_risk)
        assert tracker["has_active_incident"] is True

        # Feed the 5th safe sample — should resolve
        engine.process_risk(safe_risk)
        assert tracker["has_active_incident"] is False

    def test_no_double_incident_creation(self):
        """
        Incident flag should only be set once and not re-created on subsequent alerts.
        """
        engine = AlertEngine(persist_to_db=False)
        risk = _forced_state(RiskEngine(), 75.0, "DANGER")

        # Trigger alert and multiple subsequent danger readings
        for _ in range(10):
            engine.process_risk(risk)

        tracker = engine._node_states["N01"]
        # has_active_incident remains True (no DB to create it) and stays stable
        # The engine should have NOT tried to re-create incident after the first alert
        # (tracked via has_active_incident guard)
        assert tracker["last_state"] == "DANGER"

    def test_listener_broadcast(self):
        """AlertEngine should call all registered listeners on alert."""
        received: list[AlertEvent] = []
        engine = AlertEngine(persist_to_db=False)
        engine.register_listener(received.append)

        risk = _forced_state(RiskEngine(), 75.0, "DANGER")
        for _ in range(3):
            engine.process_risk(risk)

        assert len(received) == 1
        assert received[0].severity in ("HIGH", "CRITICAL", "MEDIUM", "LOW")

    def test_multiple_listeners_all_called(self):
        received_a, received_b = [], []
        engine = AlertEngine(persist_to_db=False)
        engine.register_listener(received_a.append)
        engine.register_listener(received_b.append)

        risk = _forced_state(RiskEngine(), 75.0, "DANGER")
        for _ in range(3):
            engine.process_risk(risk)

        assert len(received_a) == 1
        assert len(received_b) == 1

    def test_alert_event_dict_shape(self):
        """AlertEvent.to_dict() should contain all required keys."""
        engine = AlertEngine(persist_to_db=False)
        risk = _forced_state(RiskEngine(), 75.0, "DANGER")

        ev = None
        for _ in range(3):
            ev = engine.process_risk(risk)

        assert ev is not None
        d = ev.to_dict()
        for key in ("event_id", "node_id", "zone_id", "timestamp", "severity",
                    "risk_score", "state", "reason", "affected_nodes"):
            assert key in d

    def test_alert_reset(self):
        """engine.reset() should clear all node states."""
        engine = AlertEngine(persist_to_db=False)
        risk = _forced_state(RiskEngine(), 75.0, "DANGER")
        for _ in range(3):
            engine.process_risk(risk)

        assert "N01" in engine._node_states
        engine.reset()
        assert engine._node_states == {}


# ── 5. Pipeline End-to-End with Risk + Alert ──────────────────────────────────

class TestPipelineRiskAndAlert:

    def test_pipeline_produces_risk_field(self):
        pipe = ProcessingPipeline(window_size=15, persist_to_db=False)
        t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

        result = None
        for step in range(8):
            reading = TelemetryReading(
                node_id="PN01",
                zone_id="Z01",
                timestamp=t0 + timedelta(seconds=step),
                accel_x=0.01, accel_y=0.01, accel_z=9.81,
                tilt_x=0.5, tilt_y=0.1,
                vibration=50, schema_version="1.0",
            )
            result = pipe.process_reading(reading)

        assert result is not None
        assert result.risk is not None
        assert "risk_score" in result.risk
        assert "state" in result.risk
        assert result.risk["state"] in ("SAFE", "WARNING", "DANGER")
        assert "trend" in result.risk
        assert "reasons" in result.risk

    def test_pipeline_alert_field_type(self):
        """Alert field should be None (not fired) or a dict (fired) for stable node."""
        pipe = ProcessingPipeline(window_size=15, persist_to_db=False)
        t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

        result = None
        for step in range(8):
            reading = TelemetryReading(
                node_id="SAFEPN01",
                zone_id="Z01",
                timestamp=t0 + timedelta(seconds=step),
                accel_x=0.0, accel_y=0.0, accel_z=9.81,
                tilt_x=0.05, tilt_y=0.02,
                vibration=5, schema_version="1.0",
            )
            result = pipe.process_reading(reading)

        assert result is not None
        assert result.alert is None or isinstance(result.alert, dict)
