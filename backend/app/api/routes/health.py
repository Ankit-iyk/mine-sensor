"""
SUBSENSE — Health Check & System Status Routes (Phase 1 & Phase 2)

Endpoints:
  GET /api/health         → Liveness probe and connection flags
  GET /api/system/status  → High-level operational readiness probe
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.ingestion.mqtt_client import mqtt_client
from app.db.session import check_db_connection

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    mqtt_connected: bool
    db_connected: bool


class SystemStatusResponse(BaseModel):
    backend: str
    mqtt: str
    database: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns service identity, MQTT and database connection status.",
)
async def get_health() -> HealthResponse:
    db_ok = check_db_connection()
    return HealthResponse(
        status="ok",
        service="subsense-backend",
        version=settings.app_version,
        mqtt_connected=mqtt_client.is_connected,
        db_connected=db_ok,
    )


@router.get(
    "/system/status",
    response_model=SystemStatusResponse,
    summary="System operational status",
    description="Reports connectivity for backend, MQTT broker, and TimescaleDB.",
)
async def get_system_status() -> SystemStatusResponse:
    db_ok = check_db_connection()
    return SystemStatusResponse(
        backend="online",
        mqtt="connected" if mqtt_client.is_connected else "disconnected",
        database="connected" if db_ok else "disconnected",
    )
