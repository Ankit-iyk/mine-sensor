"""
SUBSENSE — Telemetry API Routes (Phase 4)

Endpoints:
  GET /api/telemetry/latest    → Most recent readings (filterable by node/zone)
  GET /api/telemetry/range     → Readings within a time range for a specific node
  GET /api/telemetry/summary   → Summary state across all known nodes
  GET /api/telemetry/count     → Total count of stored readings
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.db.session import DbSession
from app.db.repositories import readings as readings_repo

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


# ── Response Schemas ─────────────────────────────────────────────────────────

class SensorReadingResponse(BaseModel):
    id: int
    node_id: str
    zone_id: str
    timestamp: datetime
    accel_x: float
    accel_y: float
    accel_z: float
    tilt_x: float
    tilt_y: float
    vibration: int
    schema_version: str
    scenario: Optional[str] = None
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NodeSummaryResponse(BaseModel):
    node_id: str
    zone_id: str
    latest_timestamp: str
    latest_tilt_x: float
    latest_tilt_y: float
    latest_vibration: int


class CountResponse(BaseModel):
    node_id: Optional[str] = None
    count: int


# ── Route Handlers ───────────────────────────────────────────────────────────

@router.get(
    "/latest",
    response_model=list[SensorReadingResponse],
    summary="Get latest telemetry readings",
    description="Returns the newest telemetry readings, newest first. Supports filtering by node and zone.",
)
def get_latest(
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=1000, description="Max number of readings"),
    node_id: Optional[str] = Query(default=None, description="Filter by node ID"),
    zone_id: Optional[str] = Query(default=None, description="Filter by zone ID"),
) -> list[SensorReadingResponse]:
    try:
        readings = readings_repo.get_latest_readings(
            session=db, limit=limit, node_id=node_id, zone_id=zone_id
        )
        return [SensorReadingResponse.model_validate(r) for r in readings]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch telemetry readings: {str(exc)}",
        )


@router.get(
    "/range",
    response_model=list[SensorReadingResponse],
    summary="Get telemetry readings in a time range",
    description="Returns all readings for a node between start and end timestamps.",
)
def get_range(
    db: DbSession,
    node_id: str = Query(..., description="Node ID"),
    start: datetime = Query(..., description="Start timestamp (ISO-8601)"),
    end: datetime = Query(..., description="End timestamp (ISO-8601)"),
) -> list[SensorReadingResponse]:
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start timestamp cannot be greater than end timestamp",
        )
    try:
        readings = readings_repo.get_readings_in_range(
            session=db, node_id=node_id, start=start, end=end
        )
        return [SensorReadingResponse.model_validate(r) for r in readings]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch telemetry range: {str(exc)}",
        )


@router.get(
    "/summary",
    response_model=list[NodeSummaryResponse],
    summary="Get summary for all nodes",
    description="Returns the latest status and readings for each known node.",
)
def get_summary(db: DbSession) -> list[NodeSummaryResponse]:
    try:
        summaries = readings_repo.get_node_summary(session=db)
        return [NodeSummaryResponse(**s) for s in summaries]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch node summaries: {str(exc)}",
        )


@router.get(
    "/count",
    response_model=CountResponse,
    summary="Get reading count",
    description="Returns total number of telemetry records in database.",
)
def get_count(
    db: DbSession,
    node_id: Optional[str] = Query(default=None, description="Optional node ID filter"),
) -> CountResponse:
    try:
        total = readings_repo.count_readings(session=db, node_id=node_id)
        return CountResponse(node_id=node_id, count=total)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to count readings: {str(exc)}",
        )
