"""
Tests — Features REST API Endpoints (Phase 6)

Verifies:
1. GET /api/features/latest returns list of extracted features
2. GET /api/features/range returns features within the specified interval
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
from app.db.repositories.features import save_feature
from app.processing.extractor import FeatureVector


@pytest.fixture
def override_db_features():
    """Create in-memory SQLite DB and seed test features."""
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
        fv = FeatureVector(
            node_id="N01",
            timestamp=base_time + timedelta(seconds=i * 10),
            tilt_x=1.0 + i * 0.05,
            tilt_y=0.5,
            tilt_deviation=0.05 * i,
            tilt_rate=0.01,
            vibration_raw=120,
            vibration_intensity=0.12,
            vibration_frequency=0.02,
            rolling_mean_tilt=1.1,
            rolling_std_tilt=0.05,
            rolling_mean_vib=0.12,
            rolling_std_vib=0.01,
            persistence=0.1,
            trend_slope=0.005,
        )
        save_feature(db, fv)
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_api_latest_features(override_db_features):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/features/latest?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["node_id"] == "N01"
    assert "tilt_deviation" in data[0]
    assert "trend_slope" in data[0]


@pytest.mark.asyncio
async def test_api_range_features(override_db_features):
    start = "2026-09-19T10:00:05Z"
    end = "2026-09-19T10:00:35Z"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/features/range?node_id=N01&start={start}&end={end}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # timestamps at 10, 20, 30s
