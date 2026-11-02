import asyncio
from datetime import datetime, timedelta, timezone
import json
import secrets
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.ingestion.source_tracker import TelemetrySourceTracker, telemetry_source_tracker
from app.ingestion.device_auth import sign_telemetry_payload
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
    assert tracker.status(now)["mode"] == "SIMULATED"
    tracker.record("hardware", now, signed_hardware=True)
    assert tracker.status(now)["mode"] == "LIVE"
    assert tracker.status(now + timedelta(seconds=31))["mode"] == "OFFLINE"


def test_simulator_readings_are_source_tagged():
    from simulator.main import create_nodes
    from simulator.publisher import SimulatorPublisher

    reading = create_nodes("normal")[0].generate_reading()
    assert reading["source"] == "simulator"
    assert "signature" not in reading

    class FakePublisher:
        def publish(self, topic, payload, qos):
            self.topic = topic
            self.payload = payload
            return SimpleNamespace(rc=0)

    publisher = object.__new__(SimulatorPublisher)
    publisher._connected = True
    publisher._client = FakePublisher()
    publisher.publish(
        "Z01",
        "N01",
        {**reading, "source": "hardware", "signature": "forged", "nonce": "forged"},
    )
    sent = json.loads(publisher._client.payload)
    assert sent["source"] == "simulator"
    assert "signature" not in sent
    assert "nonce" not in sent


@pytest.mark.asyncio
async def test_system_mode_tracks_telemetry_post(monkeypatch):
    telemetry_source_tracker.clear()
    original_freshness = telemetry_source_tracker.freshness
    telemetry_source_tracker.freshness = timedelta(seconds=1)
    monkeypatch.setattr("app.api.routes.telemetry.pipeline.process_reading", lambda reading: None)
    monkeypatch.setattr("app.api.routes.telemetry.save_reading_safe", lambda reading: True)
    monkeypatch.setattr("app.api.routes.health.check_db_connection", lambda: False)
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
            unauthenticated_status = (await client.get("/api/system/status")).json()
            assert unauthenticated_status["mode"] == "SIMULATED"
            assert unauthenticated_status["last_hardware_seen"] is None

            monkeypatch.setattr(
                "app.config.settings.hardware_device_keys",
                {"N01": "test-device-secret-0123456789abcdef"},
            )
            invalid_payload = {
                **payload,
                "source": "hardware",
                "nonce": secrets.token_hex(16),
            }
            invalid_payload["signature"] = sign_telemetry_payload(
                invalid_payload,
                "wrong-device-secret-0123456789abcdef",
            )
            invalid_key_response = await client.post(
                "/api/telemetry",
                json=invalid_payload,
            )
            assert invalid_key_response.status_code == 200
            invalid_key_status = (await client.get("/api/system/status")).json()
            assert invalid_key_status["mode"] == "SIMULATED"
            assert invalid_key_status["last_hardware_seen"] is None

            signed_payload = {
                **payload,
                "source": "hardware",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "nonce": secrets.token_hex(16),
            }
            signed_payload["signature"] = sign_telemetry_payload(
                signed_payload,
                "test-device-secret-0123456789abcdef",
            )
            authenticated_response = await client.post(
                "/api/telemetry",
                json=signed_payload,
            )
            assert authenticated_response.status_code == 200
            live_status = (await client.get("/api/system/status")).json()
            assert live_status["mode"] == "LIVE"
            assert live_status["last_hardware_seen"] is not None
            assert live_status["last_simulator_seen"] is not None
            await asyncio.sleep(1.05)
            offline_status = (await client.get("/api/system/status")).json()
            assert offline_status["mode"] == "OFFLINE"
    finally:
        telemetry_source_tracker.clear()
        telemetry_source_tracker.freshness = original_freshness
