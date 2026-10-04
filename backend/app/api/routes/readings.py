"""
SUBSENSE — Sensor Readings API Routes (Phase 2)

Endpoints:
  GET /api/readings/latest    → Most recent readings (with limit, optional node_id, zone_id)
  GET /api/readings/{node_id} → Recent readings for a specific node (with limit, start_time, end_time)
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, Path, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.db.session import DbSession
from app.db.repositories import sensor_readings as readings_repo

router = APIRouter(prefix="/readings", tags=["Readings"])


class ReadingResponse(BaseModel):
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
    created_at: Optional[datetime] = None
    received_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/latest",
    response_model=list[ReadingResponse],
    summary="Get latest sensor readings",
    description="Returns the most recent sensor readings, newest first. Supports limit and filtering.",
)
def get_latest_readings(
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=1000, description="Max records to return"),
    node_id: Optional[str] = Query(default=None, description="Filter by node ID"),
    zone_id: Optional[str] = Query(default=None, description="Filter by zone ID"),
) -> list[ReadingResponse]:
    try:
        rows = readings_repo.get_latest_readings(
            session=db, limit=limit, node_id=node_id, zone_id=zone_id
        )
        return [ReadingResponse.model_validate(r) for r in rows]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch latest readings: {str(exc)}",
        )


@router.get(
    "/{node_id}",
    response_model=list[ReadingResponse],
    summary="Get node readings history",
    description="Returns recent readings for a specific node, optionally bounded by start_time and end_time.",
)
def get_node_readings(
    db: DbSession,
    node_id: str = Path(..., min_length=1, max_length=20, description="Node identifier"),
    limit: int = Query(default=50, ge=1, le=1000, description="Max records to return"),
    start_time: Optional[datetime] = Query(default=None, description="Start time filter (UTC ISO-8601)"),
    end_time: Optional[datetime] = Query(default=None, description="End time filter (UTC ISO-8601)"),
) -> list[ReadingResponse]:
    if start_time and end_time and start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time cannot be greater than end_time",
        )
    try:
        rows = readings_repo.get_node_readings(
            session=db,
            node_id=node_id,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
        return [ReadingResponse.model_validate(r) for r in rows]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch readings for node {node_id}: {str(exc)}",
        )
