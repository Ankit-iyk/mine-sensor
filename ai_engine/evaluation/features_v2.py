"""Causal window features for v2 simulated tilt and transient episodes."""

from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np

from ai_engine.evaluation.datasets_v2 import (
    EVENT_ONSET_MINUTE_V2,
    EpisodeV2,
    INFERENCE_INTERVAL_MINUTES_V2,
    SLOW_SAMPLE_INTERVAL_SECONDS_V2,
    class_at_inference_v2,
)


FEATURE_NAMES_V2 = (
    "vibration_peak",
    "vibration_decay_seconds",
    "decay_missing",
    "residual_tilt_x_degrees",
    "residual_tilt_y_degrees",
    "residual_tilt_magnitude_degrees",
    "cumulative_tilt_x_degrees",
    "cumulative_tilt_y_degrees",
    "cumulative_tilt_magnitude_degrees",
    "drift_slope_degrees_per_hour",
    "persistence_fraction",
    "acceleration_peak_sim_units",
    "acceleration_rms_sim_units",
    "vibration_energy_sim_units",
    "vibration_event_duration_seconds",
    "tilt_monotonicity_fraction",
    "missing_fraction",
    "repeated_sample_fraction",
)

RULE_THRESHOLD_CANDIDATES_V2 = {
    "drift_slope": (0.005, 0.01, 0.05),
    "cumulative_tilt": (0.05, 0.10, 0.20),
    "persistence": (0.50, 0.75, 1.00),
    "vibration_peak": (0.25, 0.50, 0.75),
    "decay_seconds": (0.10, 0.30, 0.80),
    "residual_tilt": (0.05, 0.10, 0.20),
}

_PAIR_INDICES: dict[int, tuple[np.ndarray, np.ndarray]] = {}


def inference_minutes_v2() -> tuple[int, ...]:
    return tuple(
        range(
            INFERENCE_INTERVAL_MINUTES_V2,
            361,
            INFERENCE_INTERVAL_MINUTES_V2,
        )
    )


def extract_window_features_v2(
    episode: EpisodeV2,
    end_minute: int,
    *,
    node_index: int = 0,
    persistence_tilt_threshold_degrees: float = 0.05,
) -> dict[str, Any]:
    """Extract features using only episode samples at or before ``end_minute``."""
    if end_minute < 15 or end_minute > int(episode.minutes[-1]):
        raise ValueError("end_minute must be within the observed inference interval")

    if node_index < 0 or node_index >= episode.node_count:
        raise ValueError("node_index is outside the episode's node range")
    valid = episode.minutes <= end_minute
    minutes = episode.minutes[valid].astype(np.float64)
    tilt = episode.tilt_degrees[valid, node_index, :].astype(np.float64)
    repeated = episode.repeated_sample[valid, node_index]

    if episode.event_minute is not None:
        pre_event = minutes < episode.event_minute
        baseline = (
            np.median(tilt[pre_event], axis=0)
            if np.any(pre_event)
            else np.asarray([1.0, 0.8])
        )
        residual_samples = minutes >= episode.event_minute + 10
        if np.any(residual_samples):
            residual = np.median(tilt[residual_samples], axis=0) - baseline
            residual_window_type = "post_event"
        else:
            residual = np.zeros(2, dtype=np.float64)
            residual_window_type = "post_event_unavailable"
    else:
        baseline = np.median(tilt[: min(16, len(tilt))], axis=0)
        residual = tilt[-1] - baseline
        residual_window_type = "observed_prefix_end"

    cumulative = tilt[-1] - baseline
    cumulative_magnitude = float(np.linalg.norm(cumulative))
    baseline_deviation = np.linalg.norm(tilt - baseline, axis=1)

    drift_start = max(0, end_minute - 60)
    drift_mask = minutes >= drift_start
    drift_values = np.linalg.norm(tilt[drift_mask] - baseline, axis=1)
    drift_slope = (
        _theil_sen_degrees_per_hour(drift_values)
        if int(drift_mask.sum()) >= 30
        else 0.0
    )

    persistence_windows: list[float] = []
    for window_index in range(4):
        window_end = end_minute - 15 * (3 - window_index)
        window_start = window_end - 15
        in_window = (minutes > window_start) & (minutes <= window_end)
        if np.any(in_window):
            persistence_windows.append(
                float(np.median(baseline_deviation[in_window]))
            )
    persistence_by_threshold = {
        threshold: (
            float(np.mean(np.asarray(persistence_windows) > threshold))
            if persistence_windows
            else 0.0
        )
        for threshold in RULE_THRESHOLD_CANDIDATES_V2["cumulative_tilt"]
    }
    persistence_fraction = persistence_by_threshold[0.05]

    event_start = end_minute - INFERENCE_INTERVAL_MINUTES_V2
    event_is_in_window = (
        episode.event_minute is not None
        and event_start < episode.event_minute <= end_minute
    )
    waveform_time = episode.waveform_time_seconds.astype(np.float64)
    vibration = episode.vibration.astype(np.float64)
    acceleration = episode.waveform_acceleration.astype(np.float64)
    if event_is_in_window:
        envelope, envelope_time = _moving_rms_envelope(waveform_time, vibration)
        vibration_peak = float(np.max(envelope)) if len(envelope) else 0.0
        decay_seconds, decay_missing = _decay_time(envelope, envelope_time)
        acceleration_peak = float(np.max(np.abs(acceleration))) if acceleration.size else 0.0
        acceleration_rms = (
            float(np.sqrt(np.mean(acceleration**2))) if acceleration.size else 0.0
        )
        vibration_energy = (
            float(np.sum(vibration**2) / 100.0) if vibration.size else 0.0
        )
        active_threshold = max(0.02, vibration_peak * 0.10)
        vibration_event_duration = float(
            np.count_nonzero(envelope >= active_threshold) / 100.0
        )
    else:
        vibration_peak = 0.0
        decay_seconds = 0.0
        decay_missing = 1.0
        acceleration_peak = 0.0
        acceleration_rms = 0.0
        vibration_energy = 0.0
        vibration_event_duration = 0.0

    tilt_history_magnitude = np.linalg.norm(tilt - baseline, axis=1)
    recent_changes = np.diff(tilt_history_magnitude[-61:])
    monotonicity = (
        float(np.mean(recent_changes >= 0.0)) if len(recent_changes) else 0.0
    )
    repeated_fraction = float(np.mean(repeated[-60:])) if len(repeated) else 0.0
    label, event_active = class_at_inference_v2(
        episode, event_start, end_minute
    )

    features: dict[str, Any] = {
        "scenario": episode.scenario,
        "seed": episode.seed,
        "condition_index": episode.condition_index,
        "inference_minute": int(end_minute),
        "class_label": label,
        "is_event": bool(event_active),
        "origin": episode.origin,
        "residual_window_type": residual_window_type,
        "parameters": episode.parameters,
        "vibration_peak": vibration_peak,
        "vibration_decay_seconds": decay_seconds,
        "decay_missing": decay_missing,
        "residual_tilt_x_degrees": float(residual[0]),
        "residual_tilt_y_degrees": float(residual[1]),
        "residual_tilt_magnitude_degrees": float(np.linalg.norm(residual)),
        "cumulative_tilt_x_degrees": float(cumulative[0]),
        "cumulative_tilt_y_degrees": float(cumulative[1]),
        "cumulative_tilt_magnitude_degrees": cumulative_magnitude,
        "drift_slope_degrees_per_hour": drift_slope,
        "persistence_fraction": persistence_fraction,
        "persistence_by_cumulative_threshold": persistence_by_threshold,
        "acceleration_peak_sim_units": acceleration_peak,
        "acceleration_rms_sim_units": acceleration_rms,
        "vibration_energy_sim_units": vibration_energy,
        "vibration_event_duration_seconds": vibration_event_duration,
        "tilt_monotonicity_fraction": monotonicity,
        "missing_fraction": 0.0,
        "repeated_sample_fraction": repeated_fraction,
        "observed_exposure_hours": end_minute / 60.0,
    }
    return features


def _moving_rms_envelope(
    time_seconds: np.ndarray, signal: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    window_samples = int(round(0.10 * 100))
    if len(signal) < window_samples:
        return np.asarray([], dtype=np.float64), np.asarray([], dtype=np.float64)
    squared = np.square(signal)
    kernel = np.ones(window_samples, dtype=np.float64) / window_samples
    envelope = np.sqrt(np.convolve(squared, kernel, mode="valid"))
    envelope_time = time_seconds[window_samples - 1 :]
    return envelope, envelope_time


def _decay_time(
    envelope: np.ndarray, time_seconds: np.ndarray
) -> tuple[float, float]:
    if len(envelope) < 3 or not np.any(envelope > 0):
        return 0.0, 1.0
    peak_index = int(np.argmax(envelope))
    peak = float(envelope[peak_index])
    threshold = peak * 0.10
    after_peak = np.arange(peak_index + 1, len(envelope))
    below = after_peak[envelope[after_peak] <= threshold]
    stop = int(below[0]) if len(below) else len(envelope) - 1
    indices = np.arange(peak_index, stop + 1)
    indices = indices[envelope[indices] > max(threshold, 1e-12)]
    if len(indices) < 3:
        return 0.0, 1.0
    slope = float(np.polyfit(time_seconds[indices], np.log(envelope[indices]), 1)[0])
    if not np.isfinite(slope) or slope >= 0.0:
        return 0.0, 1.0
    return float(-1.0 / slope), 0.0


def _theil_sen_degrees_per_hour(values: np.ndarray) -> float:
    count = len(values)
    if count < 2:
        return 0.0
    pairs = _PAIR_INDICES.get(count)
    if pairs is None:
        pairs = tuple(
            np.asarray(indices, dtype=np.int16)
            for indices in zip(*combinations(range(count), 2))
        )
        _PAIR_INDICES[count] = pairs
    left, right = pairs
    slopes = (values[right] - values[left]) / (right - left)
    return float(np.median(slopes) * 60.0)


def feature_vector_v2(features: dict[str, Any]) -> np.ndarray:
    return np.asarray(
        [float(features[name]) for name in FEATURE_NAMES_V2],
        dtype=np.float64,
    )
