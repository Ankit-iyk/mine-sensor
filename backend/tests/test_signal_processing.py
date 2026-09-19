"""
Tests — Phase 5 Signal Processing & Phase 6 Feature Extraction

Verifies:
1. Kalman Filter 2D state estimation (noise reduction, rate estimation)
2. NodeBuffer sliding window & baseline calibration
3. FeatureExtractor compliance with ML integration contract
4. Unified ProcessingPipeline end-to-end processing
"""

from datetime import datetime, timezone, timedelta
import math
import numpy as np
import pytest

from app.ingestion.schemas import TelemetryReading
from app.processing.filters import KalmanFilter2D, NodeTiltFilter
from app.processing.buffer import NodeBuffer, ProcessedSample
from app.processing.extractor import FeatureExtractor, FeatureVector
from app.processing.pipeline import ProcessingPipeline


# ── 1. Kalman Filter Tests ───────────────────────────────────────────────────

def test_kalman_filter_noise_smoothing():
    kf = KalmanFilter2D(initial_angle=0.0, q_angle=0.001, q_rate=0.003, r_measure=0.05)
    
    # Feed constant 2.0 degrees with random noise
    np.random.seed(42)
    measurements = 2.0 + np.random.normal(0, 0.2, size=30)
    
    estimates = [kf.update(m, dt=1.0) for m in measurements]
    
    # Last estimate should be close to 2.0 and have lower variance than raw measurements
    final_angle = estimates[-1].angle
    assert abs(final_angle - 2.0) < 0.1
    # Rate should be close to 0.0 for constant signal
    assert abs(estimates[-1].rate) < 0.05


def test_kalman_filter_rate_tracking():
    kf = KalmanFilter2D(initial_angle=0.0, q_angle=0.001, q_rate=0.01, r_measure=0.01)
    
    # Constant velocity ramp: 0.1 deg/s
    true_rate = 0.1
    for step in range(1, 25):
        m = step * true_rate
        est = kf.update(m, dt=1.0)
    
    # Filter should track positive velocity
    assert est.rate > 0.05
    assert abs(est.rate - true_rate) < 0.04


def test_node_tilt_filter_dual_axis():
    node_filter = NodeTiltFilter(node_id="N01")
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=1)

    est_x0, est_y0 = node_filter.filter_sample(1.0, 2.0, t0)
    assert est_x0.angle == 1.0
    assert est_y0.angle == 2.0

    est_x1, est_y1 = node_filter.filter_sample(1.05, 2.08, t1)
    assert est_x1.rate is not None
    assert est_y1.rate is not None


# ── 2. Buffer & Baseline Calibration Tests ───────────────────────────────────

def test_node_buffer_window_eviction():
    buffer = NodeBuffer(node_id="N01", max_size=5)
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    for i in range(10):
        s = ProcessedSample(
            timestamp=t0 + timedelta(seconds=i),
            raw_tilt_x=float(i),
            raw_tilt_y=0.0,
            tilt_x=float(i),
            tilt_y=0.0,
            rate_x=0.0,
            rate_y=0.0,
            tilt_magnitude=float(i),
            vibration=100,
            vibration_norm=0.1,
        )
        buffer.add_sample(s)

    assert buffer.size == 5
    # The oldest samples (0..4) should have been evicted
    assert buffer.get_latest().tilt_x == 9.0


def test_node_buffer_baseline_calibration():
    buffer = NodeBuffer(node_id="N01", max_size=30, baseline_init_samples=10)
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    for i in range(12):
        s = ProcessedSample(
            timestamp=t0 + timedelta(seconds=i),
            raw_tilt_x=1.5,
            raw_tilt_y=2.5,
            tilt_x=1.5,
            tilt_y=2.5,
            rate_x=0.0,
            rate_y=0.0,
            tilt_magnitude=math.sqrt(1.5**2 + 2.5**2),
            vibration=100,
            vibration_norm=0.1,
        )
        buffer.add_sample(s)

    assert buffer.baseline_calibrated is True
    assert buffer.baseline_tilt_x == 1.5
    assert buffer.baseline_tilt_y == 2.5

    # Deviation of a 1.5, 2.5 sample should be 0.0
    assert buffer.calculate_deviation(1.5, 2.5) == 0.0
    # Deviation of 2.5, 2.5 should be 1.0
    assert pytest.approx(buffer.calculate_deviation(2.5, 2.5), 0.001) == 1.0


# ── 3. Feature Extractor Tests ───────────────────────────────────────────────

def test_feature_extractor_returns_none_when_buffer_not_ready():
    buffer = NodeBuffer(node_id="N01", max_size=60)
    extractor = FeatureExtractor()
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    # 3 samples < 5 minimum
    for i in range(3):
        buffer.add_sample(ProcessedSample(
            timestamp=t0 + timedelta(seconds=i),
            raw_tilt_x=1.0, raw_tilt_y=1.0,
            tilt_x=1.0, tilt_y=1.0, rate_x=0.0, rate_y=0.0,
            tilt_magnitude=1.414, vibration=50, vibration_norm=0.05
        ))

    assert extractor.extract(buffer) is None


def test_feature_extractor_contract_fields_and_trend_slope():
    buffer = NodeBuffer(node_id="N01", max_size=60, baseline_init_samples=5)
    extractor = FeatureExtractor()
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    # Climbing tilt sequence: 0.1 deg increase per second
    for i in range(15):
        val = 1.0 + i * 0.1
        buffer.add_sample(ProcessedSample(
            timestamp=t0 + timedelta(seconds=i),
            raw_tilt_x=val, raw_tilt_y=0.0,
            tilt_x=val, tilt_y=0.0, rate_x=0.1, rate_y=0.0,
            tilt_magnitude=val, vibration=200, vibration_norm=0.2
        ))

    features = extractor.extract(buffer)
    assert features is not None
    assert features.node_id == "N01"
    assert features.tilt_rate > 0.0
    assert features.trend_slope > 0.0  # Upward trend detected!
    assert features.rolling_mean_tilt > 1.0

    # Test dictionary export matching ml-contract
    d = features.to_dict()
    assert "node_id" in d
    assert "tilt_deviation" in d
    assert "tilt_rate" in d
    assert "vibration_intensity" in d
    assert "vibration_frequency" in d
    assert "rolling_mean_tilt" in d
    assert "rolling_std_tilt" in d
    assert "rolling_mean_vib" in d
    assert "rolling_std_vib" in d
    assert "persistence" in d
    assert "trend_slope" in d


# ── 4. End-to-End ProcessingPipeline Tests ───────────────────────────────────

def test_processing_pipeline_stream():
    pipe = ProcessingPipeline(window_size=20, persist_to_db=False)
    t0 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    features_list = []
    for sec in range(10):
        reading = TelemetryReading(
            node_id="N01",
            zone_id="Z01",
            timestamp=t0 + timedelta(seconds=sec),
            accel_x=0.05,
            accel_y=0.05,
            accel_z=9.81,
            tilt_x=1.0 + sec * 0.05,
            tilt_y=0.5,
            vibration=150,
            schema_version="1.0",
        )
        f = pipe.process_reading(reading)
        if f is not None:
            features_list.append(f)

    # First 4 readings were buffering; readings 5-10 produce features
    assert len(features_list) == 6
    assert features_list[-1].tilt_rate >= 0.0
    assert features_list[-1].trend_slope > 0.0
