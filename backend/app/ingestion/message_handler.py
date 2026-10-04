"""
SUBSENSE — MQTT Message Handler (Phase 3)

Responsibilities
----------------
1. Decode raw MQTT payload (JSON bytes → dict)
2. Validate against TelemetryReading schema
3. Distinguish sensor anomalies from bad messages
4. Log every outcome with structured fields
5. Route valid readings to the processing pipeline (stubbed in Phase 3)

IMPORTANT: A validation failure means the MESSAGE is malformed.
It does NOT mean ground instability. These two failure modes must
always remain distinct in code and in logs.
"""

import json
import structlog
from typing import Any

from app.ingestion.schemas import TelemetryReading, ValidationResult

logger = structlog.get_logger(__name__)

# ── Duplicate-message guard ──────────────────────────────────────────────────
# In Phase 3 we use a simple in-memory LRU set. Phase 4 will move this
# to TimescaleDB for persistence across restarts.
_RECENT_MESSAGES: dict[str, str] = {}   # topic → last raw payload hash
_MAX_RECENT = 500


def handle_message(topic: str, raw_payload: bytes) -> None:
    """
    Entry point called by mqtt_client.on_message for every received message.

    Parameters
    ----------
    topic       MQTT topic string, e.g. "mine/Z01/N01/telemetry"
    raw_payload Raw bytes from the MQTT broker
    """
    # ── Step 1: JSON decode ──────────────────────────
    try:
        payload: dict[str, Any] = json.loads(raw_payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning(
            "mqtt_malformed_json",
            topic=topic,
            error=str(exc),
            raw_preview=raw_payload[:120],
        )
        return

    # ── Step 2: Duplicate detection ──────────────────
    msg_hash = _quick_hash(raw_payload)
    if _is_duplicate(topic, msg_hash):
        logger.debug("mqtt_duplicate_skipped", topic=topic)
        return
    _record_message(topic, msg_hash)

    # ── Step 3: Schema validation ────────────────────
    result = _validate(topic, payload)

    if not result.valid:
        logger.warning(
            "mqtt_validation_failed",
            topic=topic,
            validation="FAILED",
            errors=result.errors,
            # Log only the first 200 chars of raw payload to avoid log spam
            raw_preview=str(payload)[:200],
        )
        # Sensor failure is NOT treated as ground instability.
        return

    reading: TelemetryReading = result.reading  # type: ignore[assignment]

    # ── Step 4: Soft sensor-health check ────────────
    if getattr(reading, "_zero_accel_warning", False):
        logger.warning(
            "sensor_zero_accel_detected",
            node_id=reading.node_id,
            zone_id=reading.zone_id,
            note="All accelerometer axes are zero — possible sensor disconnect.",
        )

    # ── Step 5: Log receipt ──────────────────────────
    logger.info(
        "telemetry_received",
        node_id=reading.node_id,
        zone_id=reading.zone_id,
        validation="OK",
        timestamp=reading.timestamp.isoformat(),
        tilt_x=round(reading.tilt_x, 4),
        tilt_y=round(reading.tilt_y, 4),
        vibration=reading.vibration,
        scenario=reading.scenario,
    )

    # ── Step 6: Route to processing pipeline ─────────
    _dispatch(reading)


# ── Internal helpers ────────────────────────────────────────────────────────

def _validate(topic: str, payload: dict) -> ValidationResult:
    """Attempt Pydantic validation and return a structured result."""
    from pydantic import ValidationError
    try:
        reading = TelemetryReading(**payload)
        return ValidationResult(valid=True, reading=reading, raw_topic=topic)
    except ValidationError as exc:
        return ValidationResult(valid=False, errors=exc.errors(), raw_topic=topic)


def _dispatch(reading: TelemetryReading) -> None:
    """
    Route valid telemetry to database and processing pipeline.
    Persist raw reading to TimescaleDB / PostgreSQL.
    """
    from app.db.repositories.sensor_readings import save_reading_safe
    from app.processing.pipeline import pipeline

    # 1. Raw persistence
    saved = save_reading_safe(reading)
    if saved:
        logger.info(
            "database_insert_ok",
            node_id=reading.node_id,
            zone_id=reading.zone_id,
        )
    else:
        logger.error(
            "database_insert_failed",
            node_id=reading.node_id,
            zone_id=reading.zone_id,
        )

    # 2. Full intelligence pipeline: Kalman → Features → Fingerprint →
    #    ML Anomaly → Temporal → Spatial → Risk → Alert (Phases 5–13)
    try:
        pipeline.process_reading(reading)
    except Exception as exc:
        logger.error("processing_pipeline_failed", node_id=reading.node_id, error=str(exc))


def _quick_hash(data: bytes) -> str:
    """Fast non-cryptographic hash for duplicate detection."""
    import hashlib
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def _is_duplicate(topic: str, msg_hash: str) -> bool:
    """Return True if this exact payload was just seen on this topic."""
    return _RECENT_MESSAGES.get(topic) == msg_hash


def _record_message(topic: str, msg_hash: str) -> None:
    """Record the latest message hash per topic."""
    if len(_RECENT_MESSAGES) >= _MAX_RECENT:
        # Evict the oldest entry (Python dicts preserve insertion order)
        oldest = next(iter(_RECENT_MESSAGES))
        del _RECENT_MESSAGES[oldest]
    _RECENT_MESSAGES[topic] = msg_hash
