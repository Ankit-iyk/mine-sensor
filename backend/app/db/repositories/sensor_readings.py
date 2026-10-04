"""
SUBSENSE — Sensor Readings Repository (Phase 2 & Phase 4)

Provides database access operations for the sensor_readings table:
- insert_reading / save_reading (persist validated telemetry)
- save_reading_safe (isolated thread-safe write for MQTT handler)
- get_latest_reading (single newest record, optionally per node)
- get_latest_readings (newest records, filterable by node/zone with limit)
- get_node_readings (node history with optional time range and limit)
- get_readings_in_range (readings between start and end timestamps)
- count_readings (total records count)
- get_node_summary (summary of all active nodes)
"""

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.db.models import SensorReading
from app.ingestion.schemas import TelemetryReading

logger = structlog.get_logger(__name__)


# ── Write operations ─────────────────────────────────────────────────────────

def insert_reading(session: Session, reading: TelemetryReading) -> SensorReading:
    """
    Persist a validated TelemetryReading to sensor_readings.

    Parameters
    ----------
    session : Session
        An open SQLAlchemy session.
    reading : TelemetryReading
        Validated Pydantic TelemetryReading instance.

    Returns
    -------
    SensorReading
        The persisted SensorReading ORM object.
    """
    row = SensorReading(
        node_id=reading.node_id,
        zone_id=reading.zone_id,
        timestamp=reading.timestamp,
        accel_x=reading.accel_x,
        accel_y=reading.accel_y,
        accel_z=reading.accel_z,
        tilt_x=reading.tilt_x,
        tilt_y=reading.tilt_y,
        vibration=reading.vibration,
        schema_version=reading.schema_version,
        scenario=reading.scenario,
    )
    session.add(row)
    session.flush()
    return row


# Alias matching Phase 4 convention
save_reading = insert_reading


def save_reading_safe(reading: TelemetryReading) -> bool:
    """
    Save a reading in its own session/transaction.
    Used by the MQTT message handler background thread.

    Returns True on success, False on failure.
    """
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        insert_reading(db, reading)
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        logger.error(
            "db_save_reading_failed",
            node_id=reading.node_id,
            error=str(exc),
        )
        return False
    finally:
        db.close()


# ── Read operations ──────────────────────────────────────────────────────────

def get_latest_reading(session: Session, node_id: Optional[str] = None) -> Optional[SensorReading]:
    """Return the single newest reading, optionally for a specific node."""
    stmt = select(SensorReading).order_by(desc(SensorReading.timestamp))
    if node_id:
        stmt = stmt.where(SensorReading.node_id == node_id)
    return session.execute(stmt.limit(1)).scalar_one_or_none()


def get_latest_readings(
    session: Session,
    limit: int = 100,
    node_id: Optional[str] = None,
    zone_id: Optional[str] = None,
) -> list[SensorReading]:
    """
    Return the most recent sensor readings, newest first.
    Optionally filter by node_id or zone_id with a hard cap to protect memory.
    """
    stmt = select(SensorReading).order_by(desc(SensorReading.timestamp))

    if node_id:
        stmt = stmt.where(SensorReading.node_id == node_id)
    if zone_id:
        stmt = stmt.where(SensorReading.zone_id == zone_id)

    stmt = stmt.limit(min(max(limit, 1), 1000))
    return list(session.execute(stmt).scalars().all())


def get_node_readings(
    session: Session,
    node_id: str,
    limit: int = 100,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> list[SensorReading]:
    """
    Return recent readings for a specific node, optionally bounded by start/end times.
    Results are sorted descending by timestamp.
    """
    stmt = select(SensorReading).where(SensorReading.node_id == node_id)

    if start_time:
        stmt = stmt.where(SensorReading.timestamp >= start_time)
    if end_time:
        stmt = stmt.where(SensorReading.timestamp <= end_time)

    stmt = stmt.order_by(desc(SensorReading.timestamp))
    stmt = stmt.limit(min(max(limit, 1), 1000))
    return list(session.execute(stmt).scalars().all())


def get_readings_in_range(
    session: Session,
    node_id: str,
    start: datetime,
    end: datetime,
) -> list[SensorReading]:
    """Return all readings for a node between two timestamps (inclusive)."""
    stmt = (
        select(SensorReading)
        .where(
            SensorReading.node_id == node_id,
            SensorReading.timestamp >= start,
            SensorReading.timestamp <= end,
        )
        .order_by(SensorReading.timestamp)
    )
    return list(session.execute(stmt).scalars().all())


def get_node_summary(session: Session) -> list[dict]:
    """
    Return one row per known node with:
    - node_id, zone_id
    - latest_timestamp
    - latest_tilt_x, latest_tilt_y, latest_vibration
    """
    latest_ts_subq = (
        select(
            SensorReading.node_id,
            func.max(SensorReading.timestamp).label("max_ts"),
        )
        .group_by(SensorReading.node_id)
        .subquery()
    )

    stmt = (
        select(SensorReading)
        .join(
            latest_ts_subq,
            (SensorReading.node_id == latest_ts_subq.c.node_id)
            & (SensorReading.timestamp == latest_ts_subq.c.max_ts),
        )
        .order_by(SensorReading.node_id)
    )
    rows = session.execute(stmt).scalars().all()

    return [
        {
            "node_id": r.node_id,
            "zone_id": r.zone_id,
            "latest_timestamp": r.timestamp.isoformat(),
            "latest_tilt_x": r.tilt_x,
            "latest_tilt_y": r.tilt_y,
            "latest_vibration": r.vibration,
        }
        for r in rows
    ]


def count_readings(session: Session, node_id: Optional[str] = None) -> int:
    """Return total count of readings, optionally filtered by node."""
    stmt = select(func.count()).select_from(SensorReading)
    if node_id:
        stmt = stmt.where(SensorReading.node_id == node_id)
    result = session.execute(stmt).scalar()
    return result or 0
