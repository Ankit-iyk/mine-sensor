"""
Tests — GET /api/health

Verifies:
1. Endpoint returns 200 OK
2. Response body matches HealthResponse schema
3. Service name and version are correct
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings


@pytest.mark.asyncio
async def test_health_returns_200():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_schema():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/health")

    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "subsense-backend"
    assert body["version"] == settings.app_version
    assert isinstance(body["mqtt_connected"], bool)
    assert isinstance(body["db_connected"], bool)
