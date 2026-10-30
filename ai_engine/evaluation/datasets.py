"""Seeded labelled telemetry episodes built around the repository simulator."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
import random
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SIMULATOR_ROOT = _REPO_ROOT / "simulator"
if str(_SIMULATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(_SIMULATOR_ROOT))

from simulator.node import NodeBaseline, SensorNode


SCENARIOS = (
    "normal",
    "gradual_tilt",
    "step_tilt",
    "vibration_bursts",
    "persistent_offset",
    "multi_node_regional",
    "sensor_failure",
    "baseline_drift",
    "acceleration_only",
    "combined_vibration_acceleration",
    "correlated_multi_node_drift",
    "sensor_dropout",
    "sampling_jitter",
    "impulse_nuisance",
    "phone_vibration_nuisance",
    "mixed_overlapping_events",
)
EVENT_SCENARIOS = {
    "gradual_tilt", "step_tilt", "vibration_bursts", "persistent_offset",
    "multi_node_regional", "sensor_failure", "acceleration_only",
    "combined_vibration_acceleration", "correlated_multi_node_drift",
    "mixed_overlapping_events",
}
NUISANCE_SCENARIOS = {
    "baseline_drift", "sensor_dropout", "sampling_jitter",
    "impulse_nuisance", "phone_vibration_nuisance",
}
NOISE_MODELS = ("simulator", "distribution_shift")
NODE_IDS = ("N01", "N02", "N03")
ZONE_ID = "Z01"
EPISODE_SECONDS = 120
EVENT_ONSET_STEP = 30
EVENT_DURATION_STEPS = {
    "gradual_tilt": 90, "step_tilt": 20, "vibration_bursts": 32,
    "persistent_offset": 90, "multi_node_regional": 90,
    "sensor_failure": 90, "acceleration_only": 30,
    "combined_vibration_acceleration": 30, "correlated_multi_node_drift": 30,
    "mixed_overlapping_events": 30,
}


def generate_episode(
    scenario: str,
    seed: int,
    noise_model: str = "simulator",
    severity: float = 1.0,
) -> list[dict[str, Any]]:
    """Generate three-node telemetry and per-reading event truth.

    The default noise mechanics reuse the simulator's SensorNode for normal,
    gradual-tilt, vibration, persistent and regional scenarios. New event
    types use the same simulator baseline, gravity projection and noise scale.
    The shifted set adds independent sensor noise and irregular sampling.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown evaluation scenario: {scenario}")
    if noise_model not in NOISE_MODELS:
        raise ValueError(f"Unknown noise model: {noise_model}")
    if severity <= 0:
        raise ValueError("severity must be positive")

    saved_random_state = random.getstate()
    random.seed(seed)
    try:
        return _generate_episode(scenario, seed, noise_model, severity)
    finally:
        random.setstate(saved_random_state)


def _generate_episode(
    scenario: str,
    seed: int,
    noise_model: str,
    severity: float,
) -> list[dict[str, Any]]:
    rng = random.Random(seed ^ 0x5A17)
    nodes = {
        node_id: SensorNode(
            node_id=node_id,
            zone_id=ZONE_ID,
            baseline=NodeBaseline(tilt_x=1.0, tilt_y=0.8, vibration_prob=0.02),
        )
        for node_id in NODE_IDS
    }
    for node in nodes.values():
        node.set_scenario("normal")

    start = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=seed % 3650)
    clock_seconds = {node_id: 0.0 for node_id in NODE_IDS}
    last_good = {node_id: None for node_id in NODE_IDS}
    rows: list[dict[str, Any]] = []
    event_onsets: dict[str, str] = {}
    data_gap_onsets: dict[str, str] = {}
    for step in range(EPISODE_SECONDS):
        for node_index, node_id in enumerate(NODE_IDS):
            node = nodes[node_id]
            affected = _is_affected(scenario, node_id)
            event_active = affected and _event_active(scenario, step)
            if scenario in {"gradual_tilt", "mixed_overlapping_events"} and node_id == "N01" and step == EVENT_ONSET_STEP:
                node.set_scenario("gradual_tilt")
            if scenario == "multi_node_regional" and node_id in NODE_IDS and step == EVENT_ONSET_STEP:
                node.set_scenario("multi_node_event")
            if scenario in {"persistent_offset", "mixed_overlapping_events"} and event_active:
                raw = _build_offset_reading(node, severity)
                if scenario == "mixed_overlapping_events" and EVENT_ONSET_STEP + 5 <= step < EVENT_ONSET_STEP + 10:
                    raw["vibration"] = min(1023, int(700 * severity))
            elif scenario == "step_tilt" and event_active:
                raw = _build_step_reading(node, severity)
            elif scenario == "sensor_failure" and event_active:
                raw = _build_failure_reading(node, last_good[node_id])
            elif scenario == "acceleration_only" and event_active:
                raw = _build_acceleration_reading(node, severity)
            elif scenario == "combined_vibration_acceleration" and event_active:
                raw = _build_acceleration_reading(node, severity)
                raw["vibration"] = min(1023, int(500 * severity))
            elif scenario == "correlated_multi_node_drift" and event_active:
                raw = _build_drift_reading(node, step, rate=0.008 * severity)
            elif scenario == "baseline_drift":
                raw = _build_drift_reading(node, step)
            elif scenario == "vibration_bursts" and node_id == "N01":
                raw = _build_burst_reading(node, step, severity)
            elif scenario == "impulse_nuisance" and node_id == "N01":
                raw = _build_impulse_reading(node, step, severity)
            elif scenario == "phone_vibration_nuisance" and node_id == "N01":
                raw = _build_phone_vibration_reading(node, step, severity)
            else:
                raw = node.generate_reading()

            interval = (
                rng.uniform(0.5, 1.5) if scenario == "sampling_jitter"
                else rng.uniform(0.8, 1.2) if noise_model == "distribution_shift"
                else 1.0
            )
            clock_seconds[node_id] += interval
            if scenario == "sensor_dropout" and node_id == "N01" and 50 <= step < 65:
                # Model packet loss as absent observations; do not synthesize values.
                if step == 50:
                    data_gap_onsets[node_id] = (
                        start + timedelta(seconds=clock_seconds[node_id])
                    ).isoformat()
                continue
            raw["timestamp"] = (start + timedelta(seconds=clock_seconds[node_id])).isoformat()
            raw["node_id"] = node_id
            raw["zone_id"] = ZONE_ID
            if scenario in EVENT_SCENARIOS and affected and step == EVENT_ONSET_STEP:
                event_onsets[node_id] = raw["timestamp"]
            if noise_model == "distribution_shift":
                _apply_shifted_noise(raw, rng)

            if scenario != "sensor_failure" or not event_active:
                last_good[node_id] = dict(raw)
            actual_event = event_active
            event_time = event_onsets.get(node_id) if affected and scenario in EVENT_SCENARIOS else None
            event_id = f"{seed}:{scenario}:{node_id}" if affected and scenario in EVENT_SCENARIOS else None
            rows.append({
                **raw,
                "is_event": actual_event,
                "event_onset_time": event_time,
                "event_type": (
                    scenario if scenario in EVENT_SCENARIOS
                    else "baseline_drift_nuisance" if scenario == "baseline_drift"
                    else scenario if scenario in {"sensor_dropout", "sampling_jitter"}
                    else scenario if scenario in {"impulse_nuisance", "phone_vibration_nuisance"}
                    and raw.get("scenario") == scenario
                    else "none"
                ),
                "event_id": event_id,
                "step": step,
                "seed": seed,
                "scenario": scenario,
                "noise_model": noise_model,
                "severity": severity,
                "origin": "simulation",
                "event_onset_step": EVENT_ONSET_STEP if affected and scenario in EVENT_SCENARIOS else None,
                "event_duration_steps": EVENT_DURATION_STEPS.get(scenario),
                "event_duration_seconds": float(EVENT_DURATION_STEPS[scenario]) if scenario in EVENT_DURATION_STEPS else None,
                "data_gap_before": scenario == "sensor_dropout" and node_id == "N01" and step == 65,
                "data_gap_start_step": 50 if scenario == "sensor_dropout" and node_id == "N01" else None,
                "data_gap_duration_steps": 15 if scenario == "sensor_dropout" and node_id == "N01" else None,
                "data_gap_start_time": data_gap_onsets.get(node_id)
                if scenario == "sensor_dropout" and node_id == "N01" and step == 65 else None,
                "data_gap_duration_seconds": (
                    (clock_seconds[node_id] - 50.0)
                    if scenario == "sensor_dropout" and node_id == "N01" and step == 65
                    else None
                ),
            })
    return rows


def _is_affected(scenario: str, node_id: str) -> bool:
    if scenario in {"multi_node_regional", "correlated_multi_node_drift"}:
        return node_id in ("N01", "N02", "N03")
    return scenario in EVENT_SCENARIOS and node_id == "N01"


def _event_active(scenario: str, step: int) -> bool:
    if step < EVENT_ONSET_STEP:
        return False
    if scenario == "step_tilt":
        return step < EVENT_ONSET_STEP + 20
    if scenario == "vibration_bursts":
        return any(start <= step < start + 16 for start in (EVENT_ONSET_STEP, 75))
    if scenario in {"acceleration_only", "combined_vibration_acceleration", "correlated_multi_node_drift"}:
        return EVENT_ONSET_STEP <= step < EVENT_ONSET_STEP + 30
    if scenario == "mixed_overlapping_events":
        return EVENT_ONSET_STEP <= step < EVENT_ONSET_STEP + 30
    if scenario in NUISANCE_SCENARIOS:
        return False
    return scenario in EVENT_SCENARIOS


def _build_step_reading(node: SensorNode, severity: float) -> dict[str, Any]:
    raw = node.generate_reading()
    return _set_tilt(raw, raw["tilt_x"] + 1.0 * severity, raw["tilt_y"] + 0.7 * severity)


def _build_offset_reading(node: SensorNode, severity: float) -> dict[str, Any]:
    raw = node.generate_reading()
    return _set_tilt(raw, 1.0 + 2.5 * severity + random.gauss(0, 0.05),
                     0.8 + 1.2 * severity + random.gauss(0, 0.05))


def _build_failure_reading(node: SensorNode, last_good: dict[str, Any] | None) -> dict[str, Any]:
    raw = node.generate_reading()
    held = last_good or raw
    raw.update({
        "tilt_x": held["tilt_x"],
        "tilt_y": held["tilt_y"],
        "accel_x": 0.0,
        "accel_y": 0.0,
        "accel_z": 0.0,
        "vibration": 0,
        "scenario": "sensor_failure/stuck_or_disconnected",
    })
    return raw


def _build_drift_reading(node: SensorNode, step: int, rate: float = 0.002) -> dict[str, Any]:
    raw = node.generate_reading()
    drift = rate * step
    return _set_tilt(raw, raw["tilt_x"] + drift, raw["tilt_y"] + drift * 0.7)


def _build_acceleration_reading(node: SensorNode, severity: float) -> dict[str, Any]:
    """Add a translational acceleration disturbance without changing tilt."""
    raw = node.generate_reading()
    raw["accel_x"] += 1.5 * severity
    raw["scenario"] = "acceleration_disturbance"
    return raw


def _build_burst_reading(node: SensorNode, step: int, severity: float) -> dict[str, Any]:
    raw = node.generate_reading()
    if any(start <= step < start + 16 for start in (EVENT_ONSET_STEP, 75)):
        raw["vibration"] = min(1023, int(random.randint(200, 800) * severity))
        raw["scenario"] = "vibration_bursts"
    return raw


def _build_impulse_reading(node: SensorNode, step: int, severity: float) -> dict[str, Any]:
    raw = node.generate_reading()
    if step in {40, 41, 80}:
        raw["vibration"] = min(1023, int(700 * severity))
        raw["scenario"] = "impulse_nuisance"
    return raw


def _build_phone_vibration_reading(node: SensorNode, step: int, severity: float) -> dict[str, Any]:
    raw = node.generate_reading()
    if 45 <= step < 50 or 90 <= step < 95:
        phase = step % 5
        raw["vibration"] = min(1023, int((250 + 80 * phase) * severity))
        raw["scenario"] = "phone_vibration_nuisance"
    return raw


def _set_tilt(raw: dict[str, Any], tilt_x: float, tilt_y: float) -> dict[str, Any]:
    tx = math.radians(tilt_x)
    ty = math.radians(tilt_y)
    raw.update({
        "tilt_x": tilt_x,
        "tilt_y": tilt_y,
        "accel_x": 9.807 * math.sin(tx),
        "accel_y": 9.807 * math.sin(ty),
        "accel_z": 9.807 * math.cos(tx) * math.cos(ty),
    })
    return raw


def _apply_shifted_noise(raw: dict[str, Any], rng: random.Random) -> None:
    raw["tilt_x"] += rng.gauss(0, 0.12)
    raw["tilt_y"] += rng.gauss(0, 0.12)
    raw["accel_x"] += rng.gauss(0, 0.06)
    raw["accel_y"] += rng.gauss(0, 0.06)
    raw["accel_z"] += rng.gauss(0, 0.06)
