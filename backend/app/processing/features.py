"""
SUBSENSE — Feature Extraction Engine (Phase 3 & Phase 6)

Transforms windowed sensor signals into statistical, spectral, and temporal features
strictly compatible with both the ML Model Contract (ml-contract/README.md) and
the Phase 3 sensor_features storage requirements.
"""

import math
from datetime import datetime
from typing import Optional
import numpy as np

from app.config import settings
from app.processing.schemas import FeatureVector, ProcessedSample
from app.processing.buffer import NodeBuffer
from app.processing.baseline import NodeBaselineTracker
from app.processing.calibration import calculate_tilt_magnitude, calculate_accel_magnitude
from app.processing.windows import rolling_mean, rolling_std, rolling_peak, rate_of_change


class FeatureExtractor:
    """
    Computes statistical, physical, and temporal features from a NodeBuffer window
    and an optional NodeBaselineTracker.
    """

    def __init__(
        self,
        vibration_spike_threshold: float = settings.vibration_spike_threshold,
        persistence_tilt_threshold: float = settings.persistence_tilt_threshold,
        processing_version: str = "1.0",
    ) -> None:
        self.vibration_spike_threshold = vibration_spike_threshold
        self.persistence_tilt_threshold = persistence_tilt_threshold
        self.processing_version = processing_version

    def extract(
        self,
        buffer: NodeBuffer,
        baseline_tracker: Optional[NodeBaselineTracker] = None,
        zone_id: Optional[str] = None,
    ) -> Optional[FeatureVector]:
        """
        Extract feature vector from node buffer.
        Returns None if buffer has fewer than minimum required samples (is_ready is False).
        """
        if not buffer.is_ready:
            return None

        latest: Optional[ProcessedSample] = buffer.get_latest()
        if latest is None:
            return None

        # ── 1. Latest point features ─────────────────
        tilt_x = round(float(latest.tilt_x), 4)
        tilt_y = round(float(latest.tilt_y), 4)
        tilt_mag = calculate_tilt_magnitude(tilt_x, tilt_y)

        # Baseline deviation
        if baseline_tracker and baseline_tracker.state.calibrated:
            tilt_deviation = round(float(baseline_tracker.calculate_deviation(tilt_x, tilt_y)), 4)
            baseline_deviation = tilt_deviation
        else:
            tilt_deviation = round(float(buffer.calculate_deviation(tilt_x, tilt_y)), 4)
            baseline_deviation = tilt_deviation

        tilt_rate = round(float(math.sqrt(latest.rate_x**2 + latest.rate_y**2)), 4)

        # Acceleration point features
        accel_mag = calculate_accel_magnitude(latest.accel_x, latest.accel_y, latest.accel_z)

        # Vibration point features
        vibration_raw = int(latest.vibration)
        vibration_intensity = round(float(latest.vibration_norm), 4)

        # ── 2. Rolling window arrays ─────────────────
        tilt_series = buffer.get_tilt_magnitudes()
        vib_series = buffer.get_vibrations_norm()
        accel_series = buffer.get_accel_magnitudes()
        timestamps = buffer.get_timestamps()
        n_samples = len(tilt_series)

        # ── 3. Acceleration statistics ───────────────
        accel_mean = rolling_mean(accel_series) if len(accel_series) > 0 else accel_mag
        accel_std = rolling_std(accel_series) if len(accel_series) > 1 else 0.05
        accel_peak = rolling_peak(accel_series) if len(accel_series) > 0 else accel_mag

        # ── 4. Vibration statistics & event counts ───
        spike_count = int(np.sum(vib_series >= self.vibration_spike_threshold))
        vibration_event_count = spike_count

        if n_samples > 1 and len(timestamps) > 1:
            total_duration_sec = max(1.0, (timestamps[-1] - timestamps[0]).total_seconds())
            vibration_frequency = round(float(spike_count / total_duration_sec), 4)
        else:
            vibration_frequency = 0.0

        vibration_mean = rolling_mean(vib_series)
        vibration_std = rolling_std(vib_series)
        vibration_persistence = round(float(np.mean(vib_series >= self.vibration_spike_threshold)), 4)

        # ── 5. Tilt rolling statistics ───────────────
        rolling_mean_tilt = rolling_mean(tilt_series)
        rolling_std_tilt = rolling_std(tilt_series)
        rolling_mean_vib = vibration_mean
        rolling_std_vib = vibration_std

        # ── 6. Persistence (fraction of anomalous window) ─
        baseline_x = (
            baseline_tracker.state.baseline_mean_x
            if baseline_tracker and baseline_tracker.state.calibrated
            else (buffer.baseline_tilt_x if buffer.baseline_calibrated else latest.tilt_x)
        )
        baseline_y = (
            baseline_tracker.state.baseline_mean_y
            if baseline_tracker and baseline_tracker.state.calibrated
            else (buffer.baseline_tilt_y if buffer.baseline_calibrated else latest.tilt_y)
        )
        tilt_x_arr = buffer.get_tilt_x_series()
        tilt_y_arr = buffer.get_tilt_y_series()

        dev_arr = np.sqrt((tilt_x_arr - baseline_x)**2 + (tilt_y_arr - baseline_y)**2)
        anomalous_samples = (dev_arr >= self.persistence_tilt_threshold) | (vib_series >= self.vibration_spike_threshold)
        persistence = round(float(np.mean(anomalous_samples)), 4)

        # ── 7. Trend slope (rate of change in degrees/sec) ─
        dt = 1.0
        if n_samples > 1 and len(timestamps) > 1:
            dt = max(0.01, (timestamps[-1] - timestamps[0]).total_seconds() / (n_samples - 1))
        trend_slope = rate_of_change(tilt_series, dt_seconds=dt)

        return FeatureVector(
            node_id=buffer.node_id,
            timestamp=latest.timestamp,
            tilt_x=tilt_x,
            tilt_y=tilt_y,
            tilt_deviation=tilt_deviation,
            tilt_rate=tilt_rate,
            vibration_raw=vibration_raw,
            vibration_intensity=vibration_intensity,
            vibration_frequency=vibration_frequency,
            rolling_mean_tilt=rolling_mean_tilt,
            rolling_std_tilt=rolling_std_tilt,
            rolling_mean_vib=rolling_mean_vib,
            rolling_std_vib=rolling_std_vib,
            persistence=persistence,
            trend_slope=trend_slope,
            tilt_magnitude=tilt_mag,
            accel_magnitude=accel_mag,
            accel_mean=accel_mean,
            accel_std=accel_std,
            accel_peak=accel_peak,
            vibration_mean=vibration_mean,
            vibration_std=vibration_std,
            vibration_event_count=vibration_event_count,
            vibration_persistence=vibration_persistence,
            baseline_deviation=baseline_deviation,
            zone_id=zone_id,
            processing_version=self.processing_version,
        )
