"""In-process telemetry-to-risk path using the production pipeline components."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.processing.pipeline import ProcessingPipeline
from app.ingestion.source_tracker import telemetry_source_tracker


@pytest.mark.asyncio
async def test_telemetry_api_reaches_production_risk_pipeline(monkeypatch):
    telemetry_source_tracker.clear()
    pipeline = ProcessingPipeline(window_size=10, persist_to_db=False)
    completed = []
    original_process = pipeline.process_reading

    def capture_result(reading):
        result = original_process(reading)
        if result is not None:
            completed.append(result)
        return result

    monkeypatch.setattr("app.api.routes.telemetry.pipeline", pipeline)
    monkeypatch.setattr("app.api.routes.telemetry.save_reading_safe", lambda reading: True)
    monkeypatch.setattr(pipeline, "process_reading", capture_result)

    timestamp = datetime.now(timezone.utc)
    responses = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for index in range(12):
            response = await client.post(
                "/api/telemetry",
                json={
                    "source": "simulator",
                    "node_id": "N_E2E",
                    "zone_id": "Z_E2E",
                    "timestamp": (timestamp + timedelta(seconds=index)).isoformat(),
                    "accel_x": 0.0,
                    "accel_y": 0.0,
                    "accel_z": 9.81,
                    "tilt_x": 1.0 + index * 0.01,
                    "tilt_y": 0.8,
                    "vibration": 0,
                },
            )
            assert response.status_code == 200
            responses.append(response.json())
            if completed:
                break

        assert completed, "the feature window never produced a risk result"
        result = completed[-1]
        assert responses[-1] == {"accepted": True, "processed": True}
        assert result.node_id == "N_E2E"
        assert "risk_score" in result.risk
        assert result.anomaly["detector_mode"] in {"model", "mock"}
        status = await client.get("/api/system/status")
        assert status.status_code == 200
        assert status.json()["mode"] == "SIMULATED"

    telemetry_source_tracker.clear()
