"""
Tests — TelemetryReading Schema Validation

Verifies that the Pydantic schema correctly:
1. Accepts valid payloads
2. Rejects out-of-range physical values
3. Rejects missing required fields
4. Rejects impossible tilt values
5. Detects all-zero accelerometer (soft warning)
6. Accepts an optional 'scenario' field

These tests can run without MQTT, database, or any external service.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.ingestion.schemas import TelemetryReading


# ── Fixture: a valid baseline payload ────────────────────────────────────────

@pytest.fixture
def valid_payload() -> dict:
    return {
        "schema_version": "1.0",
        "node_id": "N01",
        "zone_id": "Z01",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "accel_x": 0.18,
        "accel_y": 0.14,
        "accel_z": 9.78,
        "tilt_x": 1.20,
        "tilt_y": 0.80,
        "vibration": 0,
    }


# ── Happy-path tests ─────────────────────────────────────────────────────────

def test_valid_payload_accepted(valid_payload):
    reading = TelemetryReading(**valid_payload)
    assert reading.node_id == "N01"
    assert reading.zone_id == "Z01"
    assert reading.vibration == 0


def test_scenario_field_optional(valid_payload):
    """Real ESP32 nodes don't send 'scenario'; it should default to None."""
    valid_payload.pop("scenario", None)
    reading = TelemetryReading(**valid_payload)
    assert reading.scenario is None


def test_scenario_field_accepted(valid_payload):
    valid_payload["scenario"] = "gradual_tilt"
    reading = TelemetryReading(**valid_payload)
    assert reading.scenario == "gradual_tilt"


def test_max_valid_vibration(valid_payload):
    valid_payload["vibration"] = 1023
    reading = TelemetryReading(**valid_payload)
    assert reading.vibration == 1023


def test_schema_version_defaults(valid_payload):
    valid_payload.pop("schema_version", None)
    reading = TelemetryReading(**valid_payload)
    assert reading.schema_version == "1.0"


# ── Rejection tests ──────────────────────────────────────────────────────────

def test_rejects_impossible_tilt_x(valid_payload):
    valid_payload["tilt_x"] = 999.9   # impossible: exceeds ±90°
    with pytest.raises(ValidationError):
        TelemetryReading(**valid_payload)


def test_rejects_negative_impossible_tilt(valid_payload):
    valid_payload["tilt_y"] = -91.0
    with pytest.raises(ValidationError):
        TelemetryReading(**valid_payload)


def test_rejects_accel_overflow(valid_payload):
    valid_payload["accel_z"] = 250.0  # impossible: >20g
    with pytest.raises(ValidationError):
        TelemetryReading(**valid_payload)


def test_rejects_vibration_out_of_range(valid_payload):
    valid_payload["vibration"] = 1024  # ADC is 10-bit → max 1023
    with pytest.raises(ValidationError):
        TelemetryReading(**valid_payload)


def test_rejects_negative_vibration(valid_payload):
    valid_payload["vibration"] = -1
    with pytest.raises(ValidationError):
        TelemetryReading(**valid_payload)


def test_rejects_missing_node_id(valid_payload):
    del valid_payload["node_id"]
    with pytest.raises(ValidationError):
        TelemetryReading(**valid_payload)


def test_rejects_missing_zone_id(valid_payload):
    del valid_payload["zone_id"]
    with pytest.raises(ValidationError):
        TelemetryReading(**valid_payload)


def test_rejects_missing_timestamp(valid_payload):
    del valid_payload["timestamp"]
    with pytest.raises(ValidationError):
        TelemetryReading(**valid_payload)


def test_rejects_invalid_node_id_pattern(valid_payload):
    """node_id must match ^[A-Z0-9_-]+$ (uppercase only)."""
    valid_payload["node_id"] = "node 01"   # spaces not allowed
    with pytest.raises(ValidationError):
        TelemetryReading(**valid_payload)


def test_rejects_lowercase_node_id(valid_payload):
    valid_payload["node_id"] = "n01"       # lowercase not allowed
    with pytest.raises(ValidationError):
        TelemetryReading(**valid_payload)


# ── Sensor-health soft warnings ──────────────────────────────────────────────

def test_zero_accel_sets_internal_flag(valid_payload):
    """
    All-zero accelerometer should be accepted (not a hard rejection)
    but should set an internal _zero_accel_warning flag so the
    message handler can route it to sensor-health tracking.
    """
    valid_payload.update({"accel_x": 0.0, "accel_y": 0.0, "accel_z": 0.0})
    reading = TelemetryReading(**valid_payload)
    # Accepted — not rejected
    assert reading.accel_x == 0.0
    # Internal warning flag set
    assert getattr(reading, "_zero_accel_warning", False) is True
