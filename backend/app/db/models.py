"""
SUBSENSE — Database Models (Phase 4)

SQLAlchemy 2.0-style ORM models for all five tables:

  sensor_readings   → raw validated telemetry (TimescaleDB hypertable)
  sensor_features   → extracted features per node per window
  anomaly_results   → ML inference output
  risk_results      → risk engine output
  incidents         → persisted alert records

Design decisions
----------------
- All timestamp columns are timezone-aware (TIMESTAMPTZ in PostgreSQL).
- sensor_readings uses BigInteger PK so it survives years of 1-Hz data
  across 6 nodes (~189 million rows/year) without wrapping.
- received_at records when the backend actually received the message,
  separate from the sensor's own timestamp. Useful for latency tracking.
- The hypertable conversion happens in the Alembic migration, not here.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Float, Index, Integer,
    String, Text, DateTime, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared base for all SUBSENSE ORM models."""
    pass


# ── 1. sensor_readings ───────────────────────────────────────────────────────

class SensorReading(Base):
    """
    Raw validated telemetry from one node at one point in time.

    This is the primary data store. TimescaleDB turns it into a hypertable
    partitioned by 'timestamp' (chunks by day at 1-Hz ingestion rate).

    Write path:  MQTT → message_handler → readings repository
    Read path:   REST API → readings repository
    """
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    node_id: Mapped[str] = mapped_column(String(20), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # MPU6050 acceleration (m/s²)
    accel_x: Mapped[float] = mapped_column(Float, nullable=False)
    accel_y: Mapped[float] = mapped_column(Float, nullable=False)
    accel_z: Mapped[float] = mapped_column(Float, nullable=False)

    # Tilt angles (degrees)
    tilt_x: Mapped[float] = mapped_column(Float, nullable=False)
    tilt_y: Mapped[float] = mapped_column(Float, nullable=False)

    # Vibration (ADC counts 0–1023)
    vibration: Mapped[int] = mapped_column(Integer, nullable=False)

    # Metadata
    schema_version: Mapped[str] = mapped_column(String(10), default="1.0")
    scenario: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False
    )


    __table_args__ = (
        # Composite index: node queries filtered by time are the hot path
        Index("ix_sensor_readings_node_time", "node_id", "timestamp"),
        Index("ix_sensor_readings_zone_time", "zone_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<SensorReading node={self.node_id} ts={self.timestamp} "
            f"tilt=({self.tilt_x:.2f}, {self.tilt_y:.2f})>"
        )


# ── 2. sensor_features ───────────────────────────────────────────────────────

class SensorFeature(Base):
    """
    Extracted feature vector for one node at one window boundary.

    Written by the feature extraction pipeline (Phase 6).
    Read by the ML inference adapter (Phase 8).
    """
    __tablename__ = "sensor_features"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    node_id: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Tilt features
    tilt_deviation: Mapped[float] = mapped_column(Float, nullable=False)
    tilt_rate: Mapped[float] = mapped_column(Float, nullable=False)

    # Vibration features
    vibration_intensity: Mapped[float] = mapped_column(Float, nullable=False)
    vibration_frequency: Mapped[float] = mapped_column(Float, nullable=False)

    # Rolling statistics
    rolling_mean_tilt: Mapped[float] = mapped_column(Float, nullable=False)
    rolling_std_tilt: Mapped[float] = mapped_column(Float, nullable=False)
    rolling_mean_vib: Mapped[float] = mapped_column(Float, nullable=False)
    rolling_std_vib: Mapped[float] = mapped_column(Float, nullable=False)

    # Temporal features
    persistence: Mapped[float] = mapped_column(Float, nullable=False)
    trend_slope: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("ix_sensor_features_node_time", "node_id", "timestamp"),
    )


# ── 3. anomaly_results ───────────────────────────────────────────────────────

class AnomalyResult(Base):
    """
    ML model inference output for one node at one point in time.

    Written by the ML adapter (Phase 8).
    anomaly_score: 0.0–1.0, higher = more anomalous.
    state: NORMAL | MICRO_ANOMALY | ANOMALOUS
    """
    __tablename__ = "anomaly_results"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    node_id: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_anomaly_results_node_time", "node_id", "timestamp"),
    )


# ── 4. risk_results ──────────────────────────────────────────────────────────

class RiskResult(Base):
    """
    Risk engine output for one node at one point in time (Phase 11).

    risk_score:  0–100 composite score
    state:       SAFE | WARNING | DANGER
    trend:       STABLE | IMPROVING | FLUCTUATING | ESCALATING
    reasons:     JSON-encoded list of explanation strings
    """
    __tablename__ = "risk_results"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    node_id: Mapped[str] = mapped_column(String(20), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    trend: Mapped[str] = mapped_column(String(20), nullable=False, default="STABLE")
    reasons: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list

    __table_args__ = (
        Index("ix_risk_results_node_time", "node_id", "timestamp"),
        Index("ix_risk_results_zone_time", "zone_id", "timestamp"),
    )


# ── 5. incidents ─────────────────────────────────────────────────────────────

class Incident(Base):
    """
    A persisted alert record created when anomalous behaviour persists
    beyond a configured threshold (Phase 13).

    status:      ACTIVE | RESOLVED
    severity:    LOW | MEDIUM | HIGH | CRITICAL
    """
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    node_id: Mapped[str] = mapped_column(String(20), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    affected_nodes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list

    __table_args__ = (
        Index("ix_incidents_node", "node_id"),
        Index("ix_incidents_zone_status", "zone_id", "status"),
    )
