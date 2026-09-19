"""
Tests — Phase 4 Database Layer & Repository Operations

Uses SQLite in-memory database for isolated, lightning-fast testing
without requiring an active PostgreSQL/TimescaleDB container.
"""

from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import (
    Base,
    SensorReading,
    SensorFeature,
    AnomalyResult,
    RiskResult,
    Incident,
)
from app.db.repositories.readings import (
    save_reading,
    get_latest_readings,
    get_readings_in_range,
    get_node_summary,
    count_readings,
)
from app.ingestion.schemas import TelemetryReading


@pytest.fixture
def test_db_session():
    """Create a pristine in-memory SQLite database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _make_reading(node_id="N01", zone_id="Z01", offset_seconds=0, tilt_x=1.5, vibration=120):
    return TelemetryReading(
        node_id=node_id,
        zone_id=zone_id,
        timestamp=datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_seconds),
        accel_x=0.05,
        accel_y=0.12,
        accel_z=9.81,
        tilt_x=tilt_x,
        tilt_y=2.3,
        vibration=vibration,
        schema_version="1.0",
        scenario="normal",
    )


def test_save_and_retrieve_reading(test_db_session):
    reading = _make_reading()
    saved = save_reading(test_db_session, reading)
    test_db_session.commit()

    assert saved.id is not None
    assert saved.node_id == "N01"
    assert saved.zone_id == "Z01"
    assert saved.tilt_x == 1.5
    assert saved.vibration == 120

    # Retrieve and verify
    readings = get_latest_readings(test_db_session, limit=10)
    assert len(readings) == 1
    assert readings[0].node_id == "N01"
    assert count_readings(test_db_session) == 1


def test_get_latest_readings_filtering(test_db_session):
    r1 = _make_reading(node_id="N01", zone_id="Z01", offset_seconds=10)
    r2 = _make_reading(node_id="N02", zone_id="Z01", offset_seconds=20)
    r3 = _make_reading(node_id="N03", zone_id="Z02", offset_seconds=30)

    save_reading(test_db_session, r1)
    save_reading(test_db_session, r2)
    save_reading(test_db_session, r3)
    test_db_session.commit()

    # Total count
    assert count_readings(test_db_session) == 3

    # Filter by node
    n1_readings = get_latest_readings(test_db_session, node_id="N01")
    assert len(n1_readings) == 1
    assert n1_readings[0].node_id == "N01"

    # Filter by zone
    z1_readings = get_latest_readings(test_db_session, zone_id="Z01")
    assert len(z1_readings) == 2

    # Limit
    limited = get_latest_readings(test_db_session, limit=2)
    assert len(limited) == 2


def test_get_readings_in_range(test_db_session):
    for sec in range(0, 60, 10):
        r = _make_reading(node_id="N01", offset_seconds=sec)
        save_reading(test_db_session, r)
    test_db_session.commit()

    start = datetime(2026, 9, 19, 10, 0, 15, tzinfo=timezone.utc)
    end = datetime(2026, 9, 19, 10, 0, 45, tzinfo=timezone.utc)

    range_readings = get_readings_in_range(test_db_session, node_id="N01", start=start, end=end)
    assert len(range_readings) == 3  # 20, 30, 40 seconds


def test_get_node_summary(test_db_session):
    r1 = _make_reading(node_id="N01", offset_seconds=10, tilt_x=1.0)
    r2 = _make_reading(node_id="N01", offset_seconds=20, tilt_x=2.5)
    r3 = _make_reading(node_id="N02", offset_seconds=15, tilt_x=0.8)

    save_reading(test_db_session, r1)
    save_reading(test_db_session, r2)
    save_reading(test_db_session, r3)
    test_db_session.commit()

    summary = get_node_summary(test_db_session)
    assert len(summary) == 2
    nodes = {s["node_id"]: s for s in summary}
    assert "N01" in nodes
    assert "N02" in nodes
    assert nodes["N01"]["latest_tilt_x"] == 2.5


def test_all_models_instantiation(test_db_session):
    now = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)

    feature = SensorFeature(
        node_id="N01",
        timestamp=now,
        tilt_deviation=0.05,
        tilt_rate=0.02,
        vibration_intensity=12.4,
        vibration_frequency=4.5,
        rolling_mean_tilt=1.5,
        rolling_std_tilt=0.1,
        rolling_mean_vib=120.0,
        rolling_std_vib=5.0,
        persistence=0.9,
        trend_slope=0.01,
    )
    test_db_session.add(feature)

    anomaly = AnomalyResult(
        node_id="N01",
        timestamp=now,
        anomaly_score=0.85,
        state="ANOMALOUS",
        model_version="v1.0.0",
        confidence=0.95,
        raw_score=0.85,
    )
    test_db_session.add(anomaly)

    risk = RiskResult(
        node_id="N01",
        zone_id="Z01",
        timestamp=now,
        risk_score=78.5,
        state="WARNING",
        trend="ESCALATING",
        reasons='["Tilt exceeds threshold", "Persistent vibration"]',
    )
    test_db_session.add(risk)

    incident = Incident(
        node_id="N01",
        zone_id="Z01",
        severity="HIGH",
        risk_score=85.0,
        reason="Rapid tilt rate detected",
        status="ACTIVE",
    )
    test_db_session.add(incident)

    test_db_session.commit()

    assert feature.id is not None
    assert anomaly.id is not None
    assert risk.id is not None
    assert incident.id is not None
