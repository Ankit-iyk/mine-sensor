"""
Tests — Telemetry REST API Endpoints (Phase 4)

Verifies:
1. GET /api/telemetry/latest returns list of readings
2. GET /api/telemetry/range returns readings within the time window
3. GET /api/telemetry/summary returns node summaries
4. GET /api/telemetry/count returns reading counts
"""

from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.models import Base
from app.db.session import get_db
from app.db.repositories.readings import save_reading
from app.ingestion.schemas import TelemetryReading


@pytest.fixture
def override_db():
    """Create in-memory SQLite DB and override get_db dependency in FastAPI app."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _get_test_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_test_db

    # Seed data
    db = TestingSessionLocal()
    base_time = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(5):
        reading = TelemetryReading(
            node_id="N01",
            zone_id="Z01",
            timestamp=base_time + timedelta(seconds=i * 10),
            accel_x=0.01,
            accel_y=0.02,
            accel_z=9.8,
            tilt_x=1.0 + i * 0.1,
            tilt_y=0.5,
            vibration=100 + i * 5,
            schema_version="1.0",
        )
        save_reading(db, reading)
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_api_latest_readings(override_db):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/telemetry/latest?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["node_id"] == "N01"
    assert "timestamp" in data[0]


@pytest.mark.asyncio
async def test_api_range_readings(override_db):
    start = "2026-09-19T10:00:05Z"
    end = "2026-09-19T10:00:35Z"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/telemetry/range?node_id=N01&start={start}&end={end}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # timestamps at 10, 20, 30s


@pytest.mark.asyncio
async def test_api_summary(override_db):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/telemetry/summary")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["node_id"] == "N01"
    assert data[0]["latest_vibration"] == 120


@pytest.mark.asyncio
async def test_api_count(override_db):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/telemetry/count")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5
