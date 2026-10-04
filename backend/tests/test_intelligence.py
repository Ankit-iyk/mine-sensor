"""
Tests — Phase 9 Temporal Precursor Analysis & Phase 10 Spatial Correlation Engine

Verifies:
1. Temporal analysis identifies angular acceleration and micro-tremor clustering
2. Spatial correlation distinguishes isolated single-node noise from multi-node subsidence
3. Zone topology and neighborhood constraints are strictly respected
4. Integrated pipeline produces complete spatial and temporal assessments
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.processing.schemas import FeatureVector
from app.intelligence.temporal import NodeTemporalTracker, TemporalAnalysisEngine
from app.intelligence.spatial import SpatialCorrelationEngine
from app.processing.pipeline import ProcessingPipeline
from app.ingestion.schemas import TelemetryReading


# ── 1. Temporal Precursor Tests ──────────────────────────────────────────────

def test_temporal_tracker_nominal_steady():
    tracker = NodeTemporalTracker(node_id="N01")
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    # Feed steady readings with zero acceleration
    for i in range(10):
        fv = FeatureVector(
            node_id="N01",
            timestamp=t0 + timedelta(seconds=i),
            tilt_x=0.01, tilt_y=0.01, tilt_deviation=0.01,
            tilt_rate=0.002, vibration_raw=50, vibration_intensity=0.05,
            vibration_frequency=0.0, rolling_mean_tilt=0.01, rolling_std_tilt=0.001,
            rolling_mean_vib=0.05, rolling_std_vib=0.005, persistence=0.0, trend_slope=0.0,
        )
        assessment = tracker.update(fv)

    assert assessment.node_id == "N01"
    assert assessment.stage == "NONE"
    assert assessment.precursor_score < 0.20
    assert abs(assessment.tilt_acceleration) < 0.001


def test_temporal_tracker_accelerating_subsidence():
    tracker = NodeTemporalTracker(node_id="N01")
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    # Accelerating tilt rate: 0.01, 0.02, 0.04, 0.07, 0.11 deg/s
    rates = [0.01, 0.02, 0.04, 0.07, 0.11, 0.16]
    for i, r in enumerate(rates):
        fv = FeatureVector(
            node_id="N01",
            timestamp=t0 + timedelta(seconds=i),
            tilt_x=float(i * 0.2), tilt_y=0.0, tilt_deviation=float(i * 0.2),
            tilt_rate=r, vibration_raw=400, vibration_intensity=0.40,
            vibration_frequency=0.1, rolling_mean_tilt=0.5, rolling_std_tilt=0.2,
            rolling_mean_vib=0.4, rolling_std_vib=0.1, persistence=0.7, trend_slope=0.03,
        )
        assessment = tracker.update(fv)

    assert assessment.tilt_acceleration > 0.01
    assert assessment.stage in ("ACCELERATING_PRECURSOR", "IMMINENT_COLLAPSE_WARNING")
    assert assessment.precursor_score > 0.40
    assert len(assessment.explanations) > 0


def test_temporal_micro_tremor_clustering():
    tracker = NodeTemporalTracker(node_id="N01")
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    # Feed 8 micro-tremor events (vibration_intensity >= 0.30)
    for i in range(8):
        fv = FeatureVector(
            node_id="N01",
            timestamp=t0 + timedelta(seconds=i * 2),
            tilt_x=0.1, tilt_y=0.1, tilt_deviation=0.1,
            tilt_rate=0.01, vibration_raw=500, vibration_intensity=0.55,
            vibration_frequency=0.2, rolling_mean_tilt=0.1, rolling_std_tilt=0.01,
            rolling_mean_vib=0.5, rolling_std_vib=0.1, persistence=0.2, trend_slope=0.001,
        )
        assessment = tracker.update(fv)

    assert assessment.tremor_cluster_density >= 0.80


# ── 2. Spatial Correlation Tests ─────────────────────────────────────────────

def test_spatial_isolated_disturbance():
    engine = SpatialCorrelationEngine()
    now = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    # Node N02 and N03 in Z01 are NORMAL
    engine.update_node_state("N02", "Z01", now, anomaly_score=0.05, state="NORMAL", tilt_x=0.0, tilt_y=0.0)
    engine.update_node_state("N03", "Z01", now, anomaly_score=0.05, state="NORMAL", tilt_x=0.0, tilt_y=0.0)

    # Node N01 has elevated anomaly (e.g. truck passed by)
    assessment = engine.update_node_state(
        "N01", "Z01", now, anomaly_score=0.85, state="ANOMALOUS", tilt_x=0.5, tilt_y=0.1
    )

    assert assessment.node_id == "N01"
    assert assessment.is_multi_node_event is False
    assert assessment.event_scope == "ISOLATED_DISTURBANCE"
    assert assessment.spatial_correlation_index <= 0.20
    assert len(assessment.affected_neighbors) == 0


def test_spatial_local_cluster():
    engine = SpatialCorrelationEngine()
    now = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    # N02 is anomalous, N03 is quiet
    engine.update_node_state("N02", "Z01", now, anomaly_score=0.65, state="ANOMALOUS", tilt_x=0.8, tilt_y=0.2)
    engine.update_node_state("N03", "Z01", now, anomaly_score=0.05, state="NORMAL", tilt_x=0.0, tilt_y=0.0)

    # N01 also exhibits anomaly
    assessment = engine.update_node_state(
        "N01", "Z01", now, anomaly_score=0.75, state="ANOMALOUS", tilt_x=0.9, tilt_y=0.2
    )

    assert assessment.is_multi_node_event is True
    assert assessment.event_scope == "LOCAL_CLUSTER"
    assert "N02" in assessment.affected_neighbors
    assert assessment.spatial_correlation_index >= 0.50


def test_spatial_zone_wide_subsidence():
    engine = SpatialCorrelationEngine()
    now = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    # All nodes in Z01 (N01, N02, N03) are anomalous
    engine.update_node_state("N02", "Z01", now, anomaly_score=0.75, state="ANOMALOUS", tilt_x=1.2, tilt_y=0.4)
    engine.update_node_state("N03", "Z01", now, anomaly_score=0.70, state="ANOMALOUS", tilt_x=1.1, tilt_y=0.3)

    assessment = engine.update_node_state(
        "N01", "Z01", now, anomaly_score=0.85, state="ANOMALOUS", tilt_x=1.5, tilt_y=0.5
    )

    assert assessment.is_multi_node_event is True
    assert assessment.event_scope == "ZONE_WIDE_SUBSIDENCE"
    assert assessment.spatial_correlation_index >= 0.85
    assert len(assessment.affected_neighbors) == 2


def test_spatial_cross_zone_isolation():
    engine = SpatialCorrelationEngine()
    # N01 is in Z01; N04 is in Z02 (100 meters away)
    neighbors_n1 = engine.get_neighbors("N01")
    assert "N02" in neighbors_n1
    assert "N03" in neighbors_n1
    assert "N04" not in neighbors_n1  # different zone and too far


# ── 3. Pipeline Integration with Spatial & Temporal ─────────────────────────

def test_pipeline_integrates_temporal_and_spatial():
    pipe = ProcessingPipeline(window_size=15, persist_to_db=False)
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    res = None
    for step in range(8):
        reading = TelemetryReading(
            node_id="N01",
            zone_id="Z01",
            timestamp=t0 + timedelta(seconds=step),
            accel_x=0.01, accel_y=0.01, accel_z=9.81,
            tilt_x=0.5 + step * 0.02, tilt_y=0.1,
            vibration=100, schema_version="1.0",
        )
        res = pipe.process_reading(reading)

    assert res is not None
    assert res.temporal is not None
    assert "tilt_acceleration" in res.temporal
    assert "precursor_score" in res.temporal
    assert res.spatial is not None
    assert "spatial_correlation_index" in res.spatial
    assert "event_scope" in res.spatial
