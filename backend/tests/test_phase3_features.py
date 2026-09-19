"""
Tests — Phase 3: Runtime Signal Processing + Feature Extraction

Verifies:
1. FeatureExtractor produces a valid FeatureVector with all ML-contract fields
2. NodeBaselineTracker anti-corruption: abnormal readings do NOT update baseline
3. Rolling window statistics are computed correctly (mean, std, peak, trend)
4. ProcessingPipeline correctly wires baseline_tracker + zone_id into extraction
5. Integration: pipeline -> sensor_features (in-memory DB persistence)
6. Calibration utilities: accel/tilt magnitude, failure detection
7. Windowing functions: rolling_mean, rolling_std, rolling_peak, rate_of_change
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import math
import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, SensorFeature
from app.db.repositories.features import save_feature, get_latest_features
from app.ingestion.schemas import TelemetryReading
from app.processing.baseline import NodeBaselineTracker
from app.processing.buffer import NodeBuffer, ProcessedSample
from app.processing.calibration import (
    calculate_accel_magnitude,
    calculate_tilt_magnitude,
    is_sensor_failure,
)
from app.processing.features import FeatureExtractor as DirectFeatureExtractor
from app.processing.pipeline import ProcessingPipeline
from app.processing.windows import rolling_mean, rolling_std, rolling_peak, rate_of_change


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def in_memory_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(in_memory_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=in_memory_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _make_sample(
    t0: datetime,
    offset_s: int,
    tilt_x: float = 1.0,
    tilt_y: float = 0.5,
    vib: int = 100,
    accel_z: float = 9.81,
) -> ProcessedSample:
    tilt_mag = math.sqrt(tilt_x**2 + tilt_y**2)
    return ProcessedSample(
        timestamp=t0 + timedelta(seconds=offset_s),
        raw_tilt_x=tilt_x,
        raw_tilt_y=tilt_y,
        tilt_x=tilt_x,
        tilt_y=tilt_y,
        rate_x=0.05,
        rate_y=0.02,
        tilt_magnitude=tilt_mag,
        vibration=vib,
        vibration_norm=min(1.0, vib / 1023.0),
        accel_x=0.01,
        accel_y=0.02,
        accel_z=accel_z,
        accel_magnitude=math.sqrt(0.01**2 + 0.02**2 + accel_z**2),
    )


def _filled_buffer(n: int = 20, tilt_x: float = 1.0, tilt_y: float = 0.5) -> NodeBuffer:
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    buf = NodeBuffer(node_id="N01", max_size=60, baseline_init_samples=10)
    for i in range(n):
        buf.add_sample(_make_sample(t0, i, tilt_x=tilt_x, tilt_y=tilt_y))
    return buf


# ── 1. FeatureVector ML-Contract Compliance ───────────────────────────────────

def test_feature_vector_has_all_ml_contract_fields():
    """All ML-contract fields must be present in to_dict() output."""
    buf = _filled_buffer(20)
    extractor = DirectFeatureExtractor()
    fv = extractor.extract(buf)

    assert fv is not None, "Buffer should be ready with 20 samples"

    d = fv.to_dict()
    required_fields = [
        "node_id", "timestamp",
        "tilt_x", "tilt_y", "tilt_deviation", "tilt_rate",
        "vibration_raw", "vibration_intensity", "vibration_frequency",
        "rolling_mean_tilt", "rolling_std_tilt",
        "rolling_mean_vib", "rolling_std_vib",
        "persistence", "trend_slope",
        # Phase 3 extensions
        "tilt_magnitude", "accel_magnitude",
        "accel_mean", "accel_std", "accel_peak",
        "vibration_mean", "vibration_std",
        "vibration_event_count", "vibration_persistence",
        "baseline_deviation",
    ]
    for field in required_fields:
        assert field in d, f"ML-contract field missing: {field}"


def test_feature_vector_types_are_correct():
    """Key fields must be float/int, not None or NaN."""
    buf = _filled_buffer(20)
    fv = DirectFeatureExtractor().extract(buf)
    assert fv is not None
    assert isinstance(fv.tilt_deviation, float)
    assert isinstance(fv.tilt_rate, float)
    assert isinstance(fv.vibration_raw, int)
    assert isinstance(fv.rolling_mean_tilt, float)
    assert isinstance(fv.trend_slope, float)
    assert not math.isnan(fv.tilt_deviation)
    assert not math.isnan(fv.trend_slope)


# ── 2. NodeBaselineTracker ────────────────────────────────────────────────────

def test_baseline_calibrates_after_init_samples():
    tracker = NodeBaselineTracker(node_id="N01", init_samples=10)
    for i in range(10):
        tracker.observe(tilt_x=1.5, tilt_y=2.5, vibration=80.0)
    assert tracker.state.calibrated is True
    assert abs(tracker.state.baseline_mean_x - 1.5) < 0.01
    assert abs(tracker.state.baseline_mean_y - 2.5) < 0.01


def test_baseline_anti_corruption_blocks_abnormal_samples():
    """
    After calibration with stable tilt ~1.5 deg, an abnormal spike (tilt >10 deg)
    must NOT shift the baseline mean.
    """
    tracker = NodeBaselineTracker(
        node_id="N01",
        init_samples=10,
        max_stable_tilt_deviation=0.5,
        max_stable_vibration=200.0,
    )
    for _ in range(10):
        tracker.observe(tilt_x=1.5, tilt_y=2.5, vibration=80.0)

    baseline_x_before = tracker.state.baseline_mean_x
    baseline_y_before = tracker.state.baseline_mean_y

    for _ in range(50):
        tracker.observe(tilt_x=15.0, tilt_y=12.0, vibration=900.0)

    assert abs(tracker.state.baseline_mean_x - baseline_x_before) < 0.05, \
        "Baseline X must NOT shift on abnormal readings"
    assert abs(tracker.state.baseline_mean_y - baseline_y_before) < 0.05, \
        "Baseline Y must NOT shift on abnormal readings"


def test_baseline_allows_slow_stable_drift():
    """Stable readings within threshold should slowly shift baseline via EMA."""
    tracker = NodeBaselineTracker(
        node_id="N01",
        init_samples=10,
        max_stable_tilt_deviation=5.0,
        update_alpha=0.1,
    )
    for _ in range(10):
        tracker.observe(tilt_x=1.0, tilt_y=1.0, vibration=50.0)
    for _ in range(100):
        tracker.observe(tilt_x=2.0, tilt_y=2.0, vibration=50.0)
    assert tracker.state.baseline_mean_x > 1.05, "EMA should allow slow drift on stable data"


def test_baseline_deviation_zero_at_baseline():
    tracker = NodeBaselineTracker(node_id="N01", init_samples=10)
    for _ in range(10):
        tracker.observe(tilt_x=3.0, tilt_y=4.0, vibration=60.0)
    assert tracker.state.calibrated
    dev = tracker.calculate_deviation(3.0, 4.0)
    assert abs(dev) < 0.01


# ── 3. Rolling Window Functions ───────────────────────────────────────────────

def test_rolling_mean_constant_series():
    arr = np.array([5.0] * 10)
    assert abs(rolling_mean(arr) - 5.0) < 1e-9


def test_rolling_std_constant_series():
    arr = np.array([3.0] * 20)
    assert rolling_std(arr) == 0.0


def test_rolling_peak_is_max():
    arr = np.array([1.0, 5.0, 2.0, 4.0, 0.5])
    assert rolling_peak(arr) == 5.0


def test_rate_of_change_linear_ramp():
    arr = np.array([i * 0.1 for i in range(10)])
    roc = rate_of_change(arr, dt_seconds=1.0)
    assert abs(roc - 0.1) < 0.02


def test_rate_of_change_flat():
    arr = np.array([2.5] * 15)
    roc = rate_of_change(arr, dt_seconds=1.0)
    assert abs(roc) < 0.001


# ── 4. Calibration Utilities ──────────────────────────────────────────────────

def test_accel_magnitude_stationary():
    mag = calculate_accel_magnitude(0.0, 0.0, 9.81)
    assert abs(mag - 9.81) < 0.01


def test_tilt_magnitude():
    mag = calculate_tilt_magnitude(3.0, 4.0)
    assert abs(mag - 5.0) < 0.001


def test_sensor_failure_nan():
    assert is_sensor_failure(float("nan"), 0.0, 0.0, 0, 0.0, 0.0) is True


def test_sensor_failure_inf():
    assert is_sensor_failure(0.0, float("inf"), 0.0, 0, 0.0, 0.0) is True


def test_sensor_failure_out_of_range_tilt():
    assert is_sensor_failure(200.0, 0.0, 9.81, 100, 0.0, 0.0) is True


def test_sensor_no_failure_normal():
    assert is_sensor_failure(1.5, 0.5, 9.81, 150, 2.0, 0.5) is False


# ── 5. ProcessingPipeline Wiring: baseline_tracker + zone_id ─────────────────

def test_pipeline_passes_zone_id_to_feature_vector():
    """FeatureVector.zone_id must match the reading's zone_id."""
    pipe = ProcessingPipeline(window_size=20, persist_to_db=False)
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    results = []
    for i in range(10):
        r = TelemetryReading(
            node_id="N03", zone_id="Z99",
            timestamp=t0 + timedelta(seconds=i),
            accel_x=0.01, accel_y=0.01, accel_z=9.81,
            tilt_x=1.0, tilt_y=0.5, vibration=80,
            schema_version="1.0",
        )
        result = pipe.process_reading(r)
        if result:
            results.append(result)

    assert len(results) > 0
    assert results[-1].features.zone_id == "Z99"


def test_pipeline_creates_per_node_baselines():
    """Two different nodes must maintain independent baselines."""
    pipe = ProcessingPipeline(window_size=30, persist_to_db=False)
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    # Feed 25 readings so NodeBaselineTracker (default init_samples=20) calibrates
    for i in range(25):
        pipe.process_reading(TelemetryReading(
            node_id="N01", zone_id="ZA",
            timestamp=t0 + timedelta(seconds=i),
            accel_x=0.0, accel_y=0.0, accel_z=9.81,
            tilt_x=1.0, tilt_y=1.0, vibration=50,
            schema_version="1.0",
        ))
        pipe.process_reading(TelemetryReading(
            node_id="N02", zone_id="ZA",
            timestamp=t0 + timedelta(seconds=i),
            accel_x=0.0, accel_y=0.0, accel_z=9.81,
            tilt_x=8.0, tilt_y=8.0, vibration=50,
            schema_version="1.0",
        ))

    assert "N01" in pipe._baselines
    assert "N02" in pipe._baselines
    # Both trackers should have calibrated by now
    assert pipe._baselines["N01"].state.calibrated, "N01 baseline should be calibrated"
    assert pipe._baselines["N02"].state.calibrated, "N02 baseline should be calibrated"
    b1 = pipe._baselines["N01"].state.baseline_mean_x
    b2 = pipe._baselines["N02"].state.baseline_mean_x
    assert abs(b1 - b2) > 0.5


def test_pipeline_reset_node_clears_baseline():
    pipe = ProcessingPipeline(window_size=20, persist_to_db=False)
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(5):
        pipe.process_reading(TelemetryReading(
            node_id="NX", zone_id="ZX",
            timestamp=t0 + timedelta(seconds=i),
            accel_x=0.0, accel_y=0.0, accel_z=9.81,
            tilt_x=1.0, tilt_y=0.5, vibration=80,
            schema_version="1.0",
        ))
    assert "NX" in pipe._baselines
    pipe.reset_node("NX")
    assert "NX" not in pipe._baselines
    assert "NX" not in pipe._filters
    assert "NX" not in pipe._buffers


# ── 6. Integration: Pipeline -> sensor_features Table ────────────────────────

def test_pipeline_persists_features_to_sensor_features_table(db_session, in_memory_engine):
    """
    End-to-end: telemetry flows through the processing pipeline; after the buffer
    fills, FeatureVectors are persisted in the sensor_features table.
    """
    pipe = ProcessingPipeline(window_size=15, persist_to_db=False)
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    features_saved = []

    for i in range(12):
        r = TelemetryReading(
            node_id="N01", zone_id="Z01",
            timestamp=t0 + timedelta(seconds=i),
            accel_x=0.02, accel_y=0.04, accel_z=9.80,
            tilt_x=1.0 + i * 0.02, tilt_y=0.5,
            vibration=120, schema_version="1.0",
        )
        result = pipe.process_reading(r)
        if result is not None:
            row = save_feature(db_session, result.features)
            db_session.flush()
            features_saved.append(row)

    db_session.commit()

    assert len(features_saved) > 0, "Pipeline must produce at least one FeatureVector"

    stored = get_latest_features(db_session, node_id="N01")
    assert len(stored) == len(features_saved)

    latest = stored[0]
    assert latest.node_id == "N01"
    assert isinstance(latest.tilt_deviation, float)
    assert isinstance(latest.rolling_mean_tilt, float)
    assert isinstance(latest.trend_slope, float)
    assert isinstance(latest.vibration_intensity, float)
    assert isinstance(latest.persistence, float)


def test_feature_repository_roundtrip(db_session):
    """
    save_feature followed by get_latest_features must return the same record
    with all fields intact. Validates the repository layer directly.
    """
    buf = _filled_buffer(20)
    fv = DirectFeatureExtractor().extract(buf)
    assert fv is not None

    row = save_feature(db_session, fv)
    db_session.commit()

    assert row.id is not None
    assert row.node_id == "N01"

    rows = get_latest_features(db_session, node_id="N01")
    assert len(rows) == 1
    stored = rows[0]
    assert abs(stored.tilt_deviation - fv.tilt_deviation) < 1e-6
    assert abs(stored.rolling_mean_tilt - fv.rolling_mean_tilt) < 1e-6
    assert abs(stored.trend_slope - fv.trend_slope) < 1e-6
    assert abs(stored.vibration_intensity - fv.vibration_intensity) < 1e-6
    assert abs(stored.persistence - fv.persistence) < 1e-6



# ── 7. Trend Detection ────────────────────────────────────────────────────────

def test_pipeline_detects_increasing_tilt_trend():
    """
    Rising tilt must produce a positive trend_slope in FeatureVectors.
    Uses only the extractor (no full pipeline) to avoid triggering the alert
    engine which has a transitive dependency on fastapi.
    """
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    buf = NodeBuffer(node_id="NT", max_size=60, baseline_init_samples=10)
    slopes = []
    extractor = DirectFeatureExtractor()

    for i in range(20):
        # Gentle 0.05 deg/s ramp
        val = 1.0 + i * 0.05
        sample = _make_sample(t0, i, tilt_x=val, tilt_y=0.0, vib=80)
        buf.add_sample(sample)
        fv = extractor.extract(buf)
        if fv is not None:
            slopes.append(fv.trend_slope)

    assert len(slopes) > 0
    assert sum(slopes) / len(slopes) > 0.01, "Rising tilt must produce positive trend_slope"
