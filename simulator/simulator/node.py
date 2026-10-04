"""
SUBSENSE Simulator — Sensor Node

A SensorNode models one ESP32 node.

It maintains internal state (current tilt, vibration level, scenario)
and generates realistic telemetry readings on demand.

Physical model
--------------
- Baseline tilt is established at construction.
- Small Gaussian noise is always present (σ = 0.05° tilt, σ = 0.01 m/s² accel).
- Scenarios layer additional signal on top of the noise model.
- accel_z ≈ 9.81 m/s² (gravity) when stationary.
  Slight deviation under tilt is modelled using sin/cos.

The node does not need to know about MQTT — it just produces dicts.
The publisher (publisher.py) serialises and sends them.
"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np


# ── Physical constants ───────────────────────────────────────────────────────
GRAVITY = 9.807          # m/s²
NOISE_TILT   = 0.05      # degrees (1-σ sensor noise)
NOISE_ACCEL  = 0.02      # m/s² (1-σ sensor noise)


@dataclass
class NodeBaseline:
    """The 'normal' state for this node — established at deployment."""
    tilt_x: float = 1.0      # degrees
    tilt_y: float = 0.8      # degrees
    vibration_prob: float = 0.02  # probability per reading of a noise pulse


@dataclass
class SensorNode:
    """
    Stateful representation of one ESP32 sensor node.

    Parameters
    ----------
    node_id     Unique node identifier (e.g. "N01")
    zone_id     Zone this node belongs to (e.g. "Z01")
    baseline    Normal operating values for this physical location
    """

    node_id: str
    zone_id: str
    baseline: NodeBaseline = field(default_factory=NodeBaseline)

    # Runtime state (modified by scenarios)
    _current_tilt_x: float = field(init=False)
    _current_tilt_y: float = field(init=False)
    _scenario: str = field(default="normal", init=False)
    _step: int = field(default=0, init=False)
    _frozen_reading: Optional[dict] = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._current_tilt_x = self.baseline.tilt_x
        self._current_tilt_y = self.baseline.tilt_y

    # ── Public interface ─────────────────────────────────────────────────────

    def set_scenario(self, scenario: str) -> None:
        """Switch this node to a named scenario. Resets step counter."""
        self._scenario = scenario
        self._step = 0
        self._frozen_reading = None
        # Reset tilt for gradual scenarios
        if scenario in ("normal", "vibration_event"):
            self._current_tilt_x = self.baseline.tilt_x
            self._current_tilt_y = self.baseline.tilt_y

    def generate_reading(self) -> dict:
        """Produce one telemetry payload as a plain dict."""
        self._step += 1
        scenario_fn = {
            "normal":            self._scenario_normal,
            "vibration_event":   self._scenario_vibration_event,
            "gradual_tilt":      self._scenario_gradual_tilt,
            "persistent_anomaly":self._scenario_persistent_anomaly,
            "multi_node_event":  self._scenario_multi_node_event,
            "sensor_failure":    self._scenario_sensor_failure,
        }.get(self._scenario, self._scenario_normal)

        return scenario_fn()

    # ── Scenario generators ──────────────────────────────────────────────────

    def _scenario_normal(self) -> dict:
        """
        Stable mine: Gaussian noise around baseline.
        Occasional low-level vibration pulse (p=2%).
        """
        tilt_x = self.baseline.tilt_x + random.gauss(0, NOISE_TILT)
        tilt_y = self.baseline.tilt_y + random.gauss(0, NOISE_TILT)
        vibration = self._noise_vibration()
        return self._build(tilt_x, tilt_y, vibration, "normal")

    def _scenario_vibration_event(self) -> dict:
        """
        Short vibration burst (steps 5–20), then returns to normal.
        Simulates a nearby blast, heavy machinery, or micro-seismic event.
        """
        IN_BURST = 5 <= self._step <= 20
        tilt_x = self.baseline.tilt_x + random.gauss(0, NOISE_TILT)
        tilt_y = self.baseline.tilt_y + random.gauss(0, NOISE_TILT)
        if IN_BURST:
            # Elevated vibration and accel noise during burst
            vibration = random.randint(200, 800)
        else:
            vibration = self._noise_vibration()
        return self._build(tilt_x, tilt_y, vibration, "vibration_event")

    def _scenario_gradual_tilt(self) -> dict:
        """
        Tilt_x slowly increases by 0.04°/reading (≈ 2.4°/minute at 1 Hz).
        Simulates ground creep or subsidence developing over time.
        Caps at baseline + 5° to keep values physical.
        """
        MAX_DRIFT = self.baseline.tilt_x + 5.0
        self._current_tilt_x = min(
            self._current_tilt_x + 0.04,
            MAX_DRIFT,
        )
        tilt_x = self._current_tilt_x + random.gauss(0, NOISE_TILT)
        tilt_y = self.baseline.tilt_y + random.gauss(0, NOISE_TILT)
        vibration = self._noise_vibration()
        return self._build(tilt_x, tilt_y, vibration, "gradual_tilt")

    def _scenario_persistent_anomaly(self) -> dict:
        """
        Sustained abnormal tilt AND elevated vibration.
        Represents an ongoing developing instability indicator.
        tilt_x = baseline + 2.5°  (well outside normal range)
        vibration: bursts with p=0.4
        """
        tilt_x = (self.baseline.tilt_x + 2.5) + random.gauss(0, NOISE_TILT)
        tilt_y = (self.baseline.tilt_y + 1.2) + random.gauss(0, NOISE_TILT)
        vibration = random.randint(300, 700) if random.random() < 0.4 else self._noise_vibration()
        return self._build(tilt_x, tilt_y, vibration, "persistent_anomaly")

    def _scenario_multi_node_event(self) -> dict:
        """
        Used when the orchestrator (main.py) sets multiple nearby nodes
        to this scenario. From a single node's perspective it looks like
        gradual_tilt + mild vibration.
        The spatial correlation engine (Phase 10) detects the pattern
        across nodes.
        """
        MAX_DRIFT = self.baseline.tilt_x + 3.0
        self._current_tilt_x = min(self._current_tilt_x + 0.02, MAX_DRIFT)
        tilt_x = self._current_tilt_x + random.gauss(0, NOISE_TILT)
        tilt_y = self.baseline.tilt_y + random.gauss(0, NOISE_TILT * 2)
        vibration = random.randint(50, 300) if random.random() < 0.25 else 0
        return self._build(tilt_x, tilt_y, vibration, "multi_node_event")

    def _scenario_sensor_failure(self) -> dict:
        """
        Rotates through several sensor failure modes to test the validator:
        1. All zeros (likely disconnected)
        2. Frozen reading (same values every cycle)
        3. Out-of-range tilt (impossible physical value — caught by validator)
        4. Missing fields (returned as-is; validator rejects)

        IMPORTANT: Sensor failure must NOT be confused with ground instability.
        The message handler must categorise these as sensor health events.
        """
        mode = self._step % 4
        if mode == 0:
            # All-zero accelerometer (sensor disconnect)
            return {
                "schema_version": "1.0",
                "node_id": self.node_id,
                "zone_id": self.zone_id,
                "timestamp": _utc_now(),
                "accel_x": 0.0, "accel_y": 0.0, "accel_z": 0.0,
                "tilt_x": 0.0, "tilt_y": 0.0,
                "vibration": 0,
                "scenario": "sensor_failure/zero_accel",
            }
        elif mode == 1:
            # Frozen reading (cache poisoning)
            if self._frozen_reading is None:
                self._frozen_reading = self._scenario_normal()
                self._frozen_reading["scenario"] = "sensor_failure/frozen"
            frozen = dict(self._frozen_reading)
            # Keep timestamp ticking so it's not rejected for staleness
            frozen["timestamp"] = _utc_now()
            return frozen
        elif mode == 2:
            # Impossible physical value — should be rejected by Pydantic
            return {
                "schema_version": "1.0",
                "node_id": self.node_id,
                "zone_id": self.zone_id,
                "timestamp": _utc_now(),
                "accel_x": 0.02, "accel_y": 0.04, "accel_z": 9.78,
                "tilt_x": 999.9,   # ← INVALID: exceeds ±90°
                "tilt_y": 0.8,
                "vibration": 0,
                "scenario": "sensor_failure/out_of_range",
            }
        else:
            # Missing required field — should be rejected by Pydantic
            return {
                "schema_version": "1.0",
                "node_id": self.node_id,
                # zone_id intentionally omitted
                "timestamp": _utc_now(),
                "accel_x": 0.02, "accel_y": 0.04, "accel_z": 9.78,
                "tilt_x": 1.2,
                "tilt_y": 0.8,
                "vibration": 0,
                "scenario": "sensor_failure/missing_field",
            }

    # ── Shared helpers ───────────────────────────────────────────────────────

    def _build(
        self,
        tilt_x: float,
        tilt_y: float,
        vibration: int,
        scenario: str,
    ) -> dict:
        """
        Construct a full telemetry dict given tilt and vibration.
        Derives acceleration from tilt using a physical model.
        Clamps to valid ranges to avoid accidental Pydantic rejections.
        """
        # Physical model: project gravity onto axes based on tilt
        tx_rad = math.radians(tilt_x)
        ty_rad = math.radians(tilt_y)
        ax = GRAVITY * math.sin(tx_rad) + random.gauss(0, NOISE_ACCEL)
        ay = GRAVITY * math.sin(ty_rad) + random.gauss(0, NOISE_ACCEL)
        az = GRAVITY * math.cos(tx_rad) * math.cos(ty_rad) + random.gauss(0, NOISE_ACCEL)

        return {
            "schema_version": "1.0",
            "node_id": self.node_id,
            "zone_id": self.zone_id,
            "timestamp": _utc_now(),
            "accel_x": _clamp(round(ax, 4), -20.0, 20.0),
            "accel_y": _clamp(round(ay, 4), -20.0, 20.0),
            "accel_z": _clamp(round(az, 4), -20.0, 20.0),
            "tilt_x":  _clamp(round(tilt_x, 4), -90.0, 90.0),
            "tilt_y":  _clamp(round(tilt_y, 4), -90.0, 90.0),
            "vibration": _clamp(int(vibration), 0, 1023),
            "scenario": scenario,
        }

    @staticmethod
    def _noise_vibration() -> int:
        """Low-level background vibration noise (p=2% of having a small pulse)."""
        return random.randint(1, 30) if random.random() < 0.02 else 0


# ── Module-level utilities ───────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
