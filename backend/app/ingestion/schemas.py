"""
SUBSENSE — Telemetry Ingestion Schemas (Phase 3)

TelemetryReading is the single source of truth for what the backend
accepts from sensor nodes (real or simulated).

Design decisions
----------------
- Schema is versioned (schema_version) so we can evolve the payload
  format without breaking deployed nodes.
- All physical ranges are enforced by pydantic Field constraints so
  invalid readings are rejected before they can pollute the ML pipeline.
- vibration is stored as a raw integer (0–1023) matching ESP32's 10-bit
  ADC resolution. Value 0 = no vibration detected.
- A ValidationError from pydantic results in a structured error, NOT a
  crash. The message handler logs it and discards the payload.
- The 'scenario' field is optional — the simulator uses it to tag
  readings; real ESP32 nodes omit it.
"""

from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Physical sensor constraints ─────────────────────────────────────────────
# These are intentionally generous for a prototype.
# The ML pipeline uses statistical deviation, not hard limits, for anomaly
# detection. Hard limits here only catch impossible sensor failures.

ACCEL_MIN, ACCEL_MAX = -20.0, 20.0      # m/s²  (MPU6050 ±16g range)
TILT_MIN, TILT_MAX   = -90.0, 90.0      # degrees
VIB_MIN,  VIB_MAX    =  0,    1023      # ADC counts (10-bit)


class TelemetryReading(BaseModel):
    """
    Validated sensor telemetry from one node at one point in time.

    Produced by: ESP32 nodes and the SUBSENSE simulator.
    Consumed by:  message_handler → validation → processing pipeline.
    """

    schema_version: str = Field(
        default="1.0",
        description="Payload schema version for forward compatibility.",
    )
    node_id: str = Field(
        ...,
        min_length=1,
        max_length=20,
        pattern=r"^[A-Z0-9_-]+$",
        description="Unique sensor node identifier (e.g. N01).",
        examples=["N01", "NODE_03"],
    )
    zone_id: str = Field(
        ...,
        min_length=1,
        max_length=20,
        pattern=r"^[A-Z0-9_-]+$",
        description="Mine zone this node belongs to (e.g. Z01).",
        examples=["Z01", "ZONE_A"],
    )
    timestamp: datetime = Field(
        ...,
        description="UTC ISO-8601 timestamp of the measurement.",
    )

    # ── MPU6050 acceleration (m/s²) ─────────────────
    accel_x: float = Field(..., ge=ACCEL_MIN, le=ACCEL_MAX)
    accel_y: float = Field(..., ge=ACCEL_MIN, le=ACCEL_MAX)
    accel_z: float = Field(..., ge=ACCEL_MIN, le=ACCEL_MAX)

    # ── Tilt angles (degrees) ────────────────────────
    tilt_x: float = Field(..., ge=TILT_MIN, le=TILT_MAX)
    tilt_y: float = Field(..., ge=TILT_MIN, le=TILT_MAX)

    # ── Vibration sensor (ADC counts, 0–1023) ────────
    vibration: int = Field(..., ge=VIB_MIN, le=VIB_MAX)

    # ── Optional simulator/debug fields ─────────────
    scenario: Optional[str] = Field(
        default=None,
        description="Scenario tag injected by the simulator (not from real nodes).",
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_timezone(cls, v: Any) -> Any:
        """
        Accept both timezone-aware and naive timestamps.
        For naive timestamps, assume they are already UTC.
        """
        if isinstance(v, str):
            # Pydantic will parse ISO strings; let it proceed
            return v
        if isinstance(v, datetime) and v.tzinfo is None:
            import warnings
            from datetime import timezone
            warnings.warn(
                "Received naive timestamp — treating as UTC. "
                "Nodes should always send timezone-aware timestamps.",
                UserWarning,
                stacklevel=2,
            )
        return v

    @model_validator(mode="after")
    def check_accel_z_gravity(self) -> "TelemetryReading":
        """
        Sanity check: accel_z should be near ±9.8 m/s² when the sensor
        is stationary. A value of 0.0 on all axes likely means the sensor
        is frozen or disconnected — flag it but do not reject the reading.
        This is a soft warning, not a hard rejection.
        """
        if self.accel_x == 0.0 and self.accel_y == 0.0 and self.accel_z == 0.0:
            # Will be caught by the message handler as a sensor health flag
            object.__setattr__(self, "_zero_accel_warning", True)
        return self


# ── Validation result container ─────────────────────────────────────────────

class ValidationResult(BaseModel):
    """Result of attempting to validate a raw MQTT payload."""
    valid: bool
    reading: Optional[TelemetryReading] = None
    errors: Optional[List[Any]] = None
    raw_topic: Optional[str] = None
