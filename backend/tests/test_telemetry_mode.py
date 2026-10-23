from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.ingestion.source_tracker import TelemetrySourceTracker, telemetry_source_tracker
from app.main import app


def test_tracker_reports_only_recent_known_sources():
    tracker = TelemetrySourceTracker(freshness_seconds=30)
    now = datetime(2026, 10, 23, 1, 0, tzinfo=timezone.utc)

    assert tracker.status(now)["mode"] == "OFFLINE"
    tracker.record("unknown", now)
    assert tracker.status(now)["mode"] == "OFFLINE"

    tracker.record("simulator", now)
    assert tracker.status(now)["mode"] == "SIMULATED"
    tracker.record("hardware", now)
    assert tracker.status(now)["mode"] == "LIVE"
    assert tracker.status(now + timedelta(seconds=31))["mode"] == "OFFLINE"


def test_simulator_readings_are_source_tagged():
    from simulator.main import create_nodes

    reading = create_nodes("normal")[0].generate_reading()
    assert reading["source"] == "simulator"


@pytest.mark.asyncio
async def test_system_mode_tracks_telemetry_post(monkeypatch):
    telemetry_source_tracker.clear()
    monkeypatch.setattr("app.api.routes.telemetry.pipeline.process_reading", lambda reading: None)
    monkeypatch.setattr("app.api.routes.telemetry.save_reading_safe", lambda reading: True)
    payload = {
        "node_id": "N01",
        "zone_id": "Z01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "accel_x": 0.18,
        "accel_y": 0.14,
        "accel_z": 9.78,
        "tilt_x": 1.2,
        "tilt_y": 0.8,
        "vibration": 0,
    }

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            offline = await client.get("/api/system/status")
            assert offline.status_code == 200
            assert offline.json()["mode"] == "OFFLINE"
            assert offline.json()["last_hardware_seen"] is None
            assert offline.json()["last_simulator_seen"] is None

            unknown_response = await client.post("/api/telemetry", json=payload)
            assert unknown_response.status_code == 200
            assert (await client.get("/api/system/status")).json()["mode"] == "OFFLINE"

            simulator_response = await client.post(
                "/api/telemetry",
                json={**payload, "source": "simulator"},
            )
            assert simulator_response.status_code == 200
            assert (await client.get("/api/system/status")).json()["mode"] == "SIMULATED"

            hardware_response = await client.post(
                "/api/telemetry",
                json={**payload, "source": "hardware"},
            )
            assert hardware_response.status_code == 200
            live_status = (await client.get("/api/system/status")).json()
            assert live_status["mode"] == "LIVE"
            assert live_status["last_hardware_seen"] is not None
            assert live_status["last_simulator_seen"] is not None
    finally:
        telemetry_source_tracker.clear()
