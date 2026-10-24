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
)
EVENT_SCENARIOS = set(SCENARIOS) - {"normal", "baseline_drift"}
NOISE_MODELS = ("simulator", "distribution_shift")
NODE_IDS = ("N01", "N02", "N03")
ZONE_ID = "Z01"
EPISODE_SECONDS = 120
EVENT_ONSET_STEP = 30


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
    for step in range(EPISODE_SECONDS):
        for node_index, node_id in enumerate(NODE_IDS):
            node = nodes[node_id]
            affected = _is_affected(scenario, node_id)
            event_active = affected and _event_active(scenario, step)
            if scenario == "gradual_tilt" and node_id == "N01" and step == EVENT_ONSET_STEP:
                node.set_scenario("gradual_tilt")
            if scenario == "multi_node_regional" and node_id in NODE_IDS and step == EVENT_ONSET_STEP:
                node.set_scenario("multi_node_event")
            if scenario == "persistent_offset" and event_active:
                raw = _build_offset_reading(node, severity)
            elif scenario == "step_tilt" and event_active:
                raw = _build_step_reading(node, severity)
            elif scenario == "sensor_failure" and event_active:
                raw = _build_failure_reading(node, last_good[node_id])
            elif scenario == "baseline_drift":
                raw = _build_drift_reading(node, step)
            elif scenario == "vibration_bursts" and node_id == "N01":
                raw = _build_burst_reading(node, step, severity)
            else:
                raw = node.generate_reading()

            interval = rng.uniform(0.8, 1.2) if noise_model == "distribution_shift" else 1.0
            clock_seconds[node_id] += interval
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
                "event_type": scenario if scenario in EVENT_SCENARIOS else (
                    "baseline_drift_nuisance" if scenario == "baseline_drift" else "none"
                ),
                "event_id": event_id,
                "step": step,
                "seed": seed,
                "scenario": scenario,
                "noise_model": noise_model,
                "severity": severity,
            })
    return rows


def _is_affected(scenario: str, node_id: str) -> bool:
    if scenario == "multi_node_regional":
        return node_id in ("N01", "N02", "N03")
    return scenario in EVENT_SCENARIOS and node_id == "N01"


def _event_active(scenario: str, step: int) -> bool:
    if step < EVENT_ONSET_STEP:
        return False
    if scenario == "step_tilt":
        return step < EVENT_ONSET_STEP + 20
    if scenario == "vibration_bursts":
        return any(start <= step < start + 16 for start in (EVENT_ONSET_STEP, 75))
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


def _build_drift_reading(node: SensorNode, step: int) -> dict[str, Any]:
    raw = node.generate_reading()
    drift = 0.002 * step
    return _set_tilt(raw, raw["tilt_x"] + drift, raw["tilt_y"] + drift * 0.7)


def _build_burst_reading(node: SensorNode, step: int, severity: float) -> dict[str, Any]:
    raw = node.generate_reading()
    if any(start <= step < start + 16 for start in (EVENT_ONSET_STEP, 75)):
        raw["vibration"] = min(1023, int(random.randint(200, 800) * severity))
        raw["scenario"] = "vibration_bursts"
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
