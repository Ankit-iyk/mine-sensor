"""Versioned simulation episodes for the frozen v2 event-discrimination protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


SCENARIOS_V2 = (
    "normal",
    "phone_like_vibration",
    "nonblast_impulse",
    "accel_vibration_without_tilt",
    "stuck_sensor",
    "progressive_correlated",
    "blast_tilt_recovery",
    "blast_impulse",
    "progressive_single",
)
SCENARIO_INDEX_V2 = {name: index for index, name in enumerate(SCENARIOS_V2)}
CLASS_NAMES_V2 = (
    "BLAST_TRANSIENT",
    "PROGRESSIVE_TILT_PROXY",
    "OTHER_TRANSIENT_OR_NORMAL",
)
EPISODE_MINUTES_V2 = 360
INFERENCE_INTERVAL_MINUTES_V2 = 15
EVENT_ONSET_MINUTE_V2 = 60
SLOW_SAMPLE_INTERVAL_SECONDS_V2 = 60
TRANSIENT_SAMPLE_RATE_HZ_V2 = 100
TRANSIENT_WINDOW_SECONDS_V2 = 5


@dataclass(frozen=True)
class EpisodeV2:
    scenario: str
    seed: int
    condition_index: int
    minutes: np.ndarray
    tilt_degrees: np.ndarray
    tilt_ground_truth_degrees: np.ndarray
    acceleration_m_s2: np.ndarray
    repeated_sample: np.ndarray
    waveform_time_seconds: np.ndarray
    waveform_acceleration: np.ndarray
    vibration: np.ndarray
    event_minute: int | None
    parameters: dict[str, Any]
    node_count: int
    origin: str = "simulation"


def generate_episode_v2(
    scenario: str,
    seed: int,
    condition_index: int = 0,
    *,
    training: bool = False,
) -> EpisodeV2:
    """Generate one deterministic episode using the frozen v2 seed streams."""
    if scenario not in SCENARIO_INDEX_V2:
        raise ValueError(f"Unknown v2 scenario: {scenario}")
    if condition_index not in range(14):
        raise ValueError(f"Unknown v2 condition index: {condition_index}")

    scenario_index = SCENARIO_INDEX_V2[scenario]
    generators = [
        np.random.default_rng(
            np.random.SeedSequence([int(seed), scenario_index, condition_index, stream_index])
        )
        for stream_index in range(4)
    ]
    tilt_rng, acceleration_rng, vibration_rng, event_rng = generators
    parameters = _draw_parameters(event_rng, training)
    _apply_condition(parameters, condition_index)

    node_count = 3 if scenario == "progressive_correlated" else 1
    minutes = np.arange(EPISODE_MINUTES_V2 + 1, dtype=np.int16)
    tilt_noise_sigma = 0.10 if condition_index == 13 else 0.05
    accel_noise_sigma = 0.04 if condition_index == 13 else 0.02

    baseline = np.asarray([1.0, 0.8], dtype=np.float64)
    tilt_noise = tilt_rng.normal(
        0.0, tilt_noise_sigma, size=(len(minutes), node_count, 2)
    )
    tilt = np.broadcast_to(baseline, (len(minutes), node_count, 2)).copy()

    progressive = scenario in {"progressive_correlated", "progressive_single"}
    if progressive:
        elapsed_hours = np.maximum(0.0, minutes.astype(np.float64) - EVENT_ONSET_MINUTE_V2) / 60.0
        drift = float(parameters["progressive_rate_deg_per_hour"]) * elapsed_hours
        tilt[:, :, 0] += drift[:, None]
        tilt[:, :, 1] += 0.7 * drift[:, None]

    blast = scenario in {"blast_tilt_recovery", "blast_impulse"}
    if scenario == "blast_tilt_recovery":
        elapsed_seconds = np.maximum(
            0.0, (minutes.astype(np.float64) - EVENT_ONSET_MINUTE_V2) * 60.0
        )
        recovery = np.exp(-elapsed_seconds / float(parameters["tilt_recovery_seconds"]))
        direction = int(parameters["event_polarity"])
        tilt[:, :, 0] += (
            direction * float(parameters["tilt_offset_degrees"]) * recovery
        )[:, None]
        tilt[:, :, 1] += (
            direction * 0.7 * float(parameters["tilt_offset_degrees"]) * recovery
        )[:, None]

    tilt_ground_truth = tilt.copy()
    tilt += tilt_noise
    repeated = np.zeros((len(minutes), node_count), dtype=bool)
    if scenario == "stuck_sensor":
        stuck_start = EVENT_ONSET_MINUTE_V2
        tilt[stuck_start:, :, :] = tilt[stuck_start - 1, :, :]
        tilt_ground_truth[stuck_start:, :, :] = tilt_ground_truth[stuck_start - 1, :, :]
        repeated[stuck_start:, :] = True

    acceleration_noise = acceleration_rng.normal(
        0.0, accel_noise_sigma, size=(len(minutes), node_count, 3)
    )
    accel = np.zeros((len(minutes), node_count, 3), dtype=np.float64)
    theta_x = np.deg2rad(tilt[:, :, 0])
    theta_y = np.deg2rad(tilt[:, :, 1])
    accel[:, :, 0] = 9.807 * np.sin(theta_x)
    accel[:, :, 1] = 9.807 * np.sin(theta_y)
    accel[:, :, 2] = 9.807 * np.cos(theta_x) * np.cos(theta_y)
    accel += acceleration_noise

    transient_seconds = TRANSIENT_WINDOW_SECONDS_V2
    if scenario == "phone_like_vibration":
        transient_seconds = 6
    waveform_time = np.arange(
        transient_seconds * TRANSIENT_SAMPLE_RATE_HZ_V2, dtype=np.float64
    ) / TRANSIENT_SAMPLE_RATE_HZ_V2
    waveform_accel, vibration = _make_waveform(
        scenario,
        waveform_time,
        acceleration_rng,
        vibration_rng,
        parameters,
        accel_noise_sigma,
    )

    return EpisodeV2(
        scenario=scenario,
        seed=int(seed),
        condition_index=condition_index,
        minutes=minutes,
        tilt_degrees=tilt.astype(np.float32),
        tilt_ground_truth_degrees=tilt_ground_truth.astype(np.float32),
        acceleration_m_s2=accel.astype(np.float32),
        repeated_sample=repeated,
        waveform_time_seconds=waveform_time.astype(np.float32),
        waveform_acceleration=waveform_accel.astype(np.float32),
        vibration=vibration.astype(np.float32),
        event_minute=None if scenario == "normal" else EVENT_ONSET_MINUTE_V2,
        parameters=parameters,
        node_count=node_count,
    )


def class_at_inference_v2(
    episode: EpisodeV2, start_minute: int, end_minute: int
) -> tuple[str, bool]:
    """Return the frozen class target and whether an injected event is active."""
    scenario = episode.scenario
    if scenario in {"progressive_single", "progressive_correlated"}:
        active = end_minute >= EVENT_ONSET_MINUTE_V2
        return (
            "PROGRESSIVE_TILT_PROXY" if active else "OTHER_TRANSIENT_OR_NORMAL",
            active,
        )
    if scenario in {"blast_tilt_recovery", "blast_impulse"}:
        active = start_minute < EVENT_ONSET_MINUTE_V2 <= end_minute
        return (
            "BLAST_TRANSIENT" if active else "OTHER_TRANSIENT_OR_NORMAL",
            active,
        )
    if scenario == "normal":
        return "OTHER_TRANSIENT_OR_NORMAL", False
    if scenario == "stuck_sensor":
        return (
            "OTHER_TRANSIENT_OR_NORMAL",
            end_minute >= EVENT_ONSET_MINUTE_V2,
        )
    active = start_minute < EVENT_ONSET_MINUTE_V2 <= end_minute
    return "OTHER_TRANSIENT_OR_NORMAL", active


def _draw_parameters(rng: np.random.Generator, training: bool) -> dict[str, Any]:
    uniform = rng.uniform if training else None
    if training:
        peak = float(uniform(0.25, 0.75))
        frequency = rng.uniform(5.0, 30.0, size=3)
        decay = float(uniform(0.10, 0.80))
        aftershock_count = int(rng.integers(0, 3))
        aftershock_ratios = rng.uniform(0.10, 0.30, size=2)
        aftershock_delays = rng.uniform(0.15, 1.00, size=2)
        tilt_offset = float(uniform(0.0, 0.10))
        recovery_seconds = float(uniform(1.0, 10.0))
        drift_rate = float(uniform(0.01, 0.10))
    else:
        peak = 0.50
        frequency = np.asarray([15.0, 18.0, 20.0], dtype=np.float64)
        decay = 0.30
        aftershock_count = 1
        aftershock_ratios = np.asarray([0.20, 0.20], dtype=np.float64)
        aftershock_delays = np.asarray([0.50, 0.75], dtype=np.float64)
        tilt_offset = 0.05
        recovery_seconds = 2.0
        drift_rate = 0.05
    return {
        "blast_peak_normalized": peak,
        "frequency_hz": np.asarray(frequency, dtype=np.float64).tolist(),
        "decay_seconds": decay,
        "aftershock_count": aftershock_count,
        "aftershock_amplitude_ratios": np.asarray(aftershock_ratios).tolist(),
        "aftershock_delays_seconds": np.asarray(aftershock_delays).tolist(),
        "tilt_offset_degrees": tilt_offset,
        "tilt_recovery_seconds": recovery_seconds,
        "progressive_rate_deg_per_hour": drift_rate,
        "event_polarity": int(rng.choice([-1, 1])),
        "tilt_noise_sigma_degrees": 0.05,
        "acceleration_noise_sigma_m_s2": 0.02,
    }


def _apply_condition(parameters: dict[str, Any], condition_index: int) -> None:
    if condition_index == 0:
        return
    if condition_index in (1, 2, 3):
        parameters["decay_seconds"] = (0.10, 0.30, 0.80)[condition_index - 1]
    elif condition_index in (4, 5, 6):
        parameters["tilt_offset_degrees"] = (0.0, 0.05, 0.10)[condition_index - 4]
    elif condition_index in (7, 8, 9):
        parameters["blast_peak_normalized"] = (0.25, 0.50, 0.75)[condition_index - 7]
    elif condition_index in (10, 11, 12):
        parameters["progressive_rate_deg_per_hour"] = (0.01, 0.05, 0.10)[condition_index - 10]
    else:
        parameters.update({
            "decay_seconds": 1.20,
            "tilt_offset_degrees": 0.15,
            "blast_peak_normalized": 1.00,
            "progressive_rate_deg_per_hour": 0.005,
            "tilt_noise_sigma_degrees": 0.10,
            "acceleration_noise_sigma_m_s2": 0.04,
        })


def _make_waveform(
    scenario: str,
    time_seconds: np.ndarray,
    acceleration_rng: np.random.Generator,
    vibration_rng: np.random.Generator,
    parameters: dict[str, Any],
    acceleration_noise_sigma: float,
) -> tuple[np.ndarray, np.ndarray]:
    sample_count = len(time_seconds)
    accel = np.zeros((sample_count, 3), dtype=np.float64)
    vibration = vibration_rng.normal(0.0, 0.02, size=sample_count)

    if scenario in {"blast_tilt_recovery", "blast_impulse"}:
        delays = [0.0] + list(parameters["aftershock_delays_seconds"][:parameters["aftershock_count"]])
        ratios = [1.0] + list(parameters["aftershock_amplitude_ratios"][:parameters["aftershock_count"]])
        frequencies = np.asarray(parameters["frequency_hz"], dtype=np.float64)
        phases = acceleration_rng.uniform(0.0, 2.0 * np.pi, size=(len(delays), 3))
        axis_ratios = np.asarray([1.0, 0.7, 0.5])
        polarity = int(parameters["event_polarity"])
        for pulse_index, (delay, ratio) in enumerate(zip(delays, ratios)):
            elapsed = time_seconds - delay
            active = elapsed >= 0.0
            envelope = np.zeros_like(time_seconds)
            envelope[active] = np.exp(
                -elapsed[active] / float(parameters["decay_seconds"])
            )
            for axis in range(3):
                accel[:, axis] += (
                    polarity
                    * float(parameters["blast_peak_normalized"])
                    * float(ratio)
                    * axis_ratios[axis]
                    * envelope
                    * np.sin(2.0 * np.pi * frequencies[axis] * np.maximum(elapsed, 0.0) + phases[pulse_index, axis])
                )
        accel += acceleration_rng.normal(
            0.0, acceleration_noise_sigma, size=accel.shape
        )
        vibration_signal = np.sqrt(np.sum(accel**2, axis=1))
        vibration = np.clip(vibration_signal + vibration, 0.0, 1.0)
    elif scenario in {"phone_like_vibration", "nonblast_impulse", "accel_vibration_without_tilt"}:
        amplitude = {
            "phone_like_vibration": 0.35,
            "nonblast_impulse": 0.50,
            "accel_vibration_without_tilt": 0.50,
        }[scenario]
        frequency_hz = 20.0
        if scenario == "phone_like_vibration":
            active = ((time_seconds >= 0.0) & (time_seconds < 0.5)) | (
                (time_seconds >= 5.0) & (time_seconds < 5.5)
            )
            elapsed = np.where(time_seconds < 0.5, time_seconds, time_seconds - 5.0)
            signal = amplitude * active * np.sin(2.0 * np.pi * 25.0 * elapsed)
        else:
            duration = 0.10 if scenario == "nonblast_impulse" else 0.50
            active = (time_seconds >= 0.0) & (time_seconds < duration)
            tau = 0.03 if scenario == "nonblast_impulse" else 0.15
            signal = amplitude * np.exp(-time_seconds / tau) * active * np.sin(
                2.0 * np.pi * frequency_hz * time_seconds
            )
            signal_peak = float(np.max(np.abs(signal))) if np.any(active) else 0.0
            if signal_peak > 0.0:
                signal *= amplitude / signal_peak
        accel[:, 0] = signal
        accel += acceleration_rng.normal(
            0.0, acceleration_noise_sigma, size=accel.shape
        )
        vibration = np.clip(np.abs(signal) + vibration, 0.0, 1.0)
    else:
        accel += acceleration_rng.normal(
            0.0, acceleration_noise_sigma, size=accel.shape
        )
    return accel, vibration
