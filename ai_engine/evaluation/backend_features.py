"""Run evaluation telemetry through the backend's production feature stages."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.config import settings
from app.processing.baseline import NodeBaselineTracker
from app.processing.buffer import NodeBuffer, ProcessedSample
from app.processing.calibration import calculate_accel_magnitude
from app.processing.features import FeatureExtractor
from app.processing.filters import NodeTiltFilter


def extract_backend_features(readings: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract features using the same filter, buffer, baseline and extractor.

    The evaluation deliberately stops after the backend feature extractor:
    detector predictions are computed separately so every compared method
    receives identical feature dictionaries and cannot mutate global engines.
    """
    states: dict[str, tuple[NodeTiltFilter, NodeBuffer, NodeBaselineTracker]] = {}
    extractor = FeatureExtractor()
    output: list[dict[str, Any]] = []
    for reading in readings:
        node_id = str(reading["node_id"])
        state = states.get(node_id)
        if state is None:
            state = (
                NodeTiltFilter(
                    node_id=node_id,
                    q_angle=settings.kalman_q_angle,
                    q_rate=settings.kalman_q_rate,
                    r_measure=settings.kalman_r_measure,
                ),
                NodeBuffer(node_id=node_id, max_size=settings.feature_window_size),
                NodeBaselineTracker(node_id=node_id),
            )
            states[node_id] = state
        tilt_filter, buffer, baseline = state
        timestamp = reading["timestamp"]
        if isinstance(timestamp, str):
            from datetime import datetime
            timestamp = datetime.fromisoformat(timestamp)
        estimate_x, estimate_y = tilt_filter.filter_sample(
            raw_tilt_x=float(reading["tilt_x"]),
            raw_tilt_y=float(reading["tilt_y"]),
            timestamp=timestamp,
        )
        tilt_magnitude = math.sqrt(estimate_x.angle**2 + estimate_y.angle**2)
        vibration = int(reading["vibration"])
        vibration_norm = min(1.0, max(0.0, vibration / 1023.0))
        accel_x = float(reading["accel_x"])
        accel_y = float(reading["accel_y"])
        accel_z = float(reading["accel_z"])
        accel_magnitude = calculate_accel_magnitude(accel_x, accel_y, accel_z)
        sample = ProcessedSample(
            timestamp=timestamp,
            raw_tilt_x=float(reading["tilt_x"]),
            raw_tilt_y=float(reading["tilt_y"]),
            tilt_x=estimate_x.angle,
            tilt_y=estimate_y.angle,
            rate_x=estimate_x.rate,
            rate_y=estimate_y.rate,
            tilt_magnitude=tilt_magnitude,
            vibration=vibration,
            vibration_norm=vibration_norm,
            accel_x=accel_x,
            accel_y=accel_y,
            accel_z=accel_z,
            accel_magnitude=accel_magnitude,
        )
        buffer.add_sample(sample)
        baseline.observe(estimate_x.angle, estimate_y.angle, float(vibration))
        feature_vector = extractor.extract(buffer, baseline_tracker=baseline, zone_id=str(reading["zone_id"]))
        if feature_vector is None:
            continue
        output.append({
            **feature_vector.to_dict(),
            "is_event": bool(reading.get("is_event", False)),
            "event_onset_time": reading.get("event_onset_time"),
            "event_type": reading.get("event_type", "none"),
            "event_id": reading.get("event_id"),
            "label": reading.get("label", ""),
            "target_angle_deg": reading.get("target_angle_deg"),
            "vibration_input": reading.get("vibration_input", vibration / 1023.0),
            "node_id": node_id,
            "zone_id": str(reading["zone_id"]),
            "timestamp": timestamp,
            "step": int(reading.get("step", 0)),
            "seed": reading.get("seed"),
            "scenario": reading.get("scenario", "real_data"),
            "noise_model": reading.get("noise_model", "real_data"),
            "severity": reading.get("severity", 1.0),
            "origin": reading.get("origin", "unspecified"),
            "event_onset_step": reading.get("event_onset_step"),
            "event_duration_steps": reading.get("event_duration_steps"),
            "event_duration_seconds": reading.get("event_duration_seconds"),
            "data_gap_before": bool(reading.get("data_gap_before", False)),
            "data_gap_start_step": reading.get("data_gap_start_step"),
            "data_gap_duration_steps": reading.get("data_gap_duration_steps"),
            "data_gap_start_time": reading.get("data_gap_start_time"),
            "data_gap_duration_seconds": reading.get("data_gap_duration_seconds"),
        })
    return output
