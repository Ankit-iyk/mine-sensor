"""
Tests — Phase 2: PostgreSQL + TimescaleDB + Real Telemetry Persistence

Covers all 9 requirements specified in Phase 2:
1. Valid telemetry is stored in sensor_readings
2. Invalid telemetry is rejected and discarded without storing
3. GET /api/readings/latest returns newest records with limits/filters
4. GET /api/readings/{node_id} returns node history
5. Time-range query filters readings between start and end timestamps
6. Database unavailable behaviour (safe return, logged, no listener crash)
7. Health & system status endpoints (GET /api/health, GET /api/system/status)
8. MQTT message reaches the database via handle_message
9. Simulator output → MQTT handler → backend → database integration
"""

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.models import Base, SensorReading
from app.db.session import get_db
from app.db.repositories.sensor_readings import (
    insert_reading,
    get_latest_reading,
    get_latest_readings,
    get_node_readings,
    get_readings_in_range,
    save_reading_safe,
    count_readings,
)
from app.ingestion.schemas import TelemetryReading
from app.ingestion.message_handler import handle_message
from simulator.node import SensorNode


@pytest.fixture
def test_engine():
    """Create a fresh in-memory SQLite database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_session(test_engine):
    """Provide a transactional session for testing."""
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_session, test_engine):
    """FastAPI TestClient wired to the test database session."""
    def override_get_db():
        try:
            yield test_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _valid_reading(node_id="N01", zone_id="Z01", offset_s=0, tilt_x=1.2, vib=120) -> TelemetryReading:
    return TelemetryReading(
        node_id=node_id,
        zone_id=zone_id,
        timestamp=datetime(2026, 9, 19, 11, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_s),
        accel_x=0.02,
        accel_y=0.04,
        accel_z=9.80,
        tilt_x=tilt_x,
        tilt_y=0.85,
        vibration=vib,
        schema_version="1.0",
        scenario="normal",
    )


# ── Test 1: Valid telemetry is stored ─────────────────────────────────────────

def test_valid_telemetry_stored(test_session):
    reading = _valid_reading()
    row = insert_reading(test_session, reading)
    test_session.commit()

    assert row.id is not None
    assert row.node_id == "N01"
    assert row.zone_id == "Z01"
    assert row.tilt_x == 1.2
    assert row.vibration == 120
    assert row.schema_version == "1.0"
    assert count_readings(test_session) == 1

    latest = get_latest_reading(test_session)
    assert latest is not None
    assert latest.node_id == "N01"


# ── Test 2: Invalid telemetry is rejected ─────────────────────────────────────

def test_invalid_telemetry_rejected(test_session):
    # Invalid: tilt_x exceeds physically possible sensor range (> 90 degrees)
    invalid_raw = {
        "node_id": "N01",
        "zone_id": "Z01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "accel_x": 0.0,
        "accel_y": 0.0,
        "accel_z": 9.8,
        "tilt_x": 195.0,  # Invalid
        "tilt_y": 0.0,
        "vibration": 50,
    }

    initial_count = count_readings(test_session)

    # Dispatch malformed payload to MQTT handler
    handle_message("mine/Z01/N01/telemetry", json.dumps(invalid_raw).encode("utf-8"))

    # Nothing should have been persisted
    assert count_readings(test_session) == initial_count


# ── Test 3: Latest reading endpoint ──────────────────────────────────────────

def test_api_readings_latest(client, test_session):
    for i in range(5):
        insert_reading(test_session, _valid_reading(node_id=f"N0{i+1}", offset_s=i * 10))
    test_session.commit()

    resp = client.get("/api/readings/latest?limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    # Ordered newest first
    assert data[0]["node_id"] == "N05"
    assert "tilt_x" in data[0]
    assert "created_at" in data[0] or "received_at" in data[0]

    # Filter by node
    resp_node = client.get("/api/readings/latest?node_id=N02")
    assert resp_node.status_code == 200
    node_data = resp_node.json()
    assert len(node_data) == 1
    assert node_data[0]["node_id"] == "N02"


# ── Test 4: Node history endpoint ────────────────────────────────────────────

def test_api_readings_node_history(client, test_session):
    insert_reading(test_session, _valid_reading(node_id="N01", offset_s=10))
    insert_reading(test_session, _valid_reading(node_id="N01", offset_s=20))
    insert_reading(test_session, _valid_reading(node_id="N02", offset_s=30))
    test_session.commit()

    resp = client.get("/api/readings/N01?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(r["node_id"] == "N01" for r in data)


# ── Test 5: Time-range query ─────────────────────────────────────────────────

def test_time_range_query(client, test_session):
    t0 = datetime(2026, 9, 19, 11, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=10)
    t2 = t0 + timedelta(minutes=20)
    t3 = t0 + timedelta(minutes=30)

    insert_reading(test_session, _valid_reading(node_id="N01", offset_s=0))
    insert_reading(test_session, _valid_reading(node_id="N01", offset_s=600))   # +10 min
    insert_reading(test_session, _valid_reading(node_id="N01", offset_s=1200))  # +20 min
    insert_reading(test_session, _valid_reading(node_id="N01", offset_s=1800))  # +30 min
    test_session.commit()

    # Query repository directly
    in_range = get_readings_in_range(test_session, "N01", start=t1, end=t2)
    assert len(in_range) == 2

    # Query via REST API
    resp = client.get(
        "/api/readings/N01",
        params={"start_time": t1.isoformat(), "end_time": t2.isoformat()},
    )
    assert resp.status_code == 200
    api_data = resp.json()
    assert len(api_data) == 2


# ── Test 6: Database unavailable behaviour ───────────────────────────────────

def test_database_unavailable_behavior():
    reading = _valid_reading()

    # Mock SessionLocal to simulate database disconnect/error
    with patch("app.db.session.SessionLocal") as mock_session_factory:
        mock_db = MagicMock()
        mock_db.flush.side_effect = Exception("OperationalError: connection lost")
        mock_session_factory.return_value = mock_db

        # Must not raise an unhandled exception or crash
        success = save_reading_safe(reading)
        assert success is False
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()


# ── Test 7: Health endpoint still works & System status ───────────────────────

def test_health_and_system_status_endpoints(client):
    # Liveness health check
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "ok"
    assert "mqtt_connected" in health_data
    assert "db_connected" in health_data

    # System operational status
    status_resp = client.get("/api/system/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["backend"] == "online"
    assert "mqtt" in status_data
    assert "database" in status_data


# ── Test 8: MQTT message still reaches the database ──────────────────────────

def test_mqtt_message_reaches_database(test_session, test_engine):
    payload = {
        "schema_version": "1.0",
        "node_id": "N01",
        "zone_id": "Z01",
        "timestamp": "2026-09-19T11:20:00+00:00",
        "accel_x": 0.05,
        "accel_y": 0.10,
        "accel_z": 9.79,
        "tilt_x": 1.45,
        "tilt_y": 0.92,
        "vibration": 150,
        "scenario": "normal",
    }
    raw = json.dumps(payload).encode("utf-8")

    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Patch SessionLocal used by save_reading_safe to use our test engine
    with patch("app.db.session.SessionLocal", side_effect=TestingSession):
        handle_message("mine/Z01/N01/telemetry", raw)

    # Verify directly from database
    readings = get_latest_readings(test_session, node_id="N01")
    assert len(readings) >= 1
    assert readings[0].node_id == "N01"
    assert readings[0].tilt_x == 1.45
    assert readings[0].vibration == 150


# ── Test 9: Simulator → MQTT → backend → database integration ────────────────

def test_simulator_to_backend_database_integration(test_session, test_engine):
    # Use real SensorNode from the simulator
    node = SensorNode(node_id="N09", zone_id="Z09")

    # Generate real telemetry reading from simulator
    telemetry_dict = node.generate_reading()
    assert telemetry_dict["node_id"] == "N09"
    assert "tilt_x" in telemetry_dict

    raw_payload = json.dumps(telemetry_dict).encode("utf-8")
    topic = f"mine/{telemetry_dict['zone_id']}/{telemetry_dict['node_id']}/telemetry"

    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    with patch("app.db.session.SessionLocal", side_effect=TestingSession):
        handle_message(topic, raw_payload)

    # Query database and verify persistence
    node_readings = get_latest_readings(test_session, node_id="N09")
    assert len(node_readings) == 1
    stored = node_readings[0]
    assert stored.node_id == "N09"
    assert stored.zone_id == "Z09"
    assert stored.vibration == telemetry_dict["vibration"]
