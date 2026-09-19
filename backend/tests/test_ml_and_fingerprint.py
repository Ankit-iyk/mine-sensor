"""
Tests — Phase 7 Ground Stability Fingerprint & Phase 8 ML Model Integration

Verifies:
1. MockAnomalyDetector adheres to ml-contract interface
2. Anomaly score thresholds correctly classify NORMAL, MICRO_ANOMALY, ANOMALOUS
3. GroundStabilityEngine computes multi-axis stability indices and grades
4. ProcessingPipeline integrates signal processing -> features -> fingerprint -> ML inference
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.ml.interface import AnomalyDetector
from app.ml.mock_model import MockAnomalyDetector
from app.ml.loader import get_detector
from app.processing.schemas import FeatureVector
from app.processing.fingerprint import GroundStabilityEngine
from app.processing.pipeline import ProcessingPipeline
from app.ingestion.schemas import TelemetryReading


# ── 1. ML Interface & Mock Model Tests ───────────────────────────────────────

def test_mock_detector_static_mode():
    detector = MockAnomalyDetector(dynamic_heuristic=False)
    features = {"node_id": "N01", "tilt_rate": 0.0, "persistence": 0.0}

    out = detector.predict(features)
    assert out["anomaly_score"] == 0.05
    assert out["state"] == "NORMAL"
    assert out["model_version"] == "mock-0.1.0"


def test_mock_detector_dynamic_mode_anomalous():
    detector = MockAnomalyDetector(dynamic_heuristic=True)
    # High precursor features indicating ground instability
    features = {
        "node_id": "N01",
        "tilt_rate": 0.12,        # severe rate
        "tilt_deviation": 1.6,    # high deviation
        "persistence": 0.85,      # prolonged event
        "vibration_intensity": 0.6,
        "trend_slope": 0.04,
    }

    out = detector.predict(features)
    assert out["anomaly_score"] >= 0.60
    assert out["state"] == "ANOMALOUS"


def test_anomaly_detector_thresholds():
    detector = MockAnomalyDetector()
    assert detector.classify_score(0.15) == "NORMAL"
    assert detector.classify_score(0.45) == "MICRO_ANOMALY"
    assert detector.classify_score(0.85) == "ANOMALOUS"


def test_detector_factory():
    detector = get_detector()
    assert isinstance(detector, AnomalyDetector)
    assert detector.version is not None


# ── 2. Ground Stability Fingerprint Tests ────────────────────────────────────

def test_ground_stability_nominal_stable():
    engine = GroundStabilityEngine()
    now = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    # Undisturbed ground feature vector
    features = FeatureVector(
        node_id="N01",
        timestamp=now,
        tilt_x=0.01,
        tilt_y=0.02,
        tilt_deviation=0.01,
        tilt_rate=0.001,
        vibration_raw=80,
        vibration_intensity=0.08,
        vibration_frequency=0.0,
        rolling_mean_tilt=0.02,
        rolling_std_tilt=0.005,
        rolling_mean_vib=0.08,
        rolling_std_vib=0.01,
        persistence=0.0,
        trend_slope=0.0001,
    )

    fingerprint = engine.compute_fingerprint(features)
    assert fingerprint.node_id == "N01"
    assert fingerprint.stability_index >= 0.85
    assert fingerprint.stability_grade == "STABLE"
    assert fingerprint.tilt_stability > 0.90
    assert fingerprint.creep_stability > 0.90


def test_ground_stability_unstable_subsidence():
    engine = GroundStabilityEngine()
    now = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    # Active subsidence precursor feature vector
    features = FeatureVector(
        node_id="N01",
        timestamp=now,
        tilt_x=1.8,
        tilt_y=1.2,
        tilt_deviation=1.8,
        tilt_rate=0.09,
        vibration_raw=800,
        vibration_intensity=0.78,
        vibration_frequency=0.45,
        rolling_mean_tilt=1.5,
        rolling_std_tilt=0.25,
        rolling_mean_vib=0.75,
        rolling_std_vib=0.10,
        persistence=0.90,
        trend_slope=0.035,
    )

    fingerprint = engine.compute_fingerprint(features)
    assert fingerprint.stability_index < 0.40
    assert fingerprint.stability_grade in ("UNSTABLE", "CRITICAL")
    assert fingerprint.tilt_stability < 0.30

    d = fingerprint.to_dict()
    assert "tilt_stability" in d
    assert "vibration_stability" in d
    assert "creep_stability" in d
    assert "persistence_stability" in d


# ── 3. Pipeline End-to-End Stability Result Test ─────────────────────────────

def test_pipeline_produces_complete_stability_result():
    pipe = ProcessingPipeline(window_size=15, persist_to_db=False)
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    results = []
    for step in range(10):
        reading = TelemetryReading(
            node_id="N01",
            zone_id="Z01",
            timestamp=t0 + timedelta(seconds=step),
            accel_x=0.02,
            accel_y=0.02,
            accel_z=9.81,
            tilt_x=0.5 + step * 0.05,
            tilt_y=0.2,
            vibration=120,
            schema_version="1.0",
        )
        res = pipe.process_reading(reading)
        if res is not None:
            results.append(res)

    assert len(results) > 0
    latest = results[-1]
    assert latest.node_id == "N01"
    assert latest.features is not None
    assert "stability_index" in latest.fingerprint
    assert "anomaly_score" in latest.anomaly
    assert "state" in latest.anomaly
