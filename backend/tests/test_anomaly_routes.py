"""
Tests — Anomaly REST API Endpoints (Phase 8)

Verifies:
1. GET /api/anomalies/latest returns list of anomaly records
2. GET /api/anomalies/range returns anomaly records within the specified interval
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
from app.db.repositories.anomalies import save_anomaly


@pytest.fixture
def override_db_anomalies():
    """Create in-memory SQLite DB and seed test anomalies."""
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
        inference = {
            "anomaly_score": 0.1 * i,
            "state": "NORMAL" if i < 3 else "MICRO_ANOMALY",
            "model_version": "mock-0.1.0",
            "confidence": 0.95,
            "raw_score": 0.1 * i,
        }
        save_anomaly(db, "N01", base_time + timedelta(seconds=i * 10), inference)
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_api_latest_anomalies(override_db_anomalies):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/anomalies/latest?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["node_id"] == "N01"
    assert "anomaly_score" in data[0]
    assert "state" in data[0]


@pytest.mark.asyncio
async def test_api_range_anomalies(override_db_anomalies):
    start = "2026-09-19T10:00:05Z"
    end = "2026-09-19T10:00:35Z"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/anomalies/range?node_id=N01&start={start}&end={end}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # timestamps at 10, 20, 30s
