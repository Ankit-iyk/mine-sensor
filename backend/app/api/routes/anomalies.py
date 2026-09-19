"""
SUBSENSE — Anomaly API Routes (Phase 8)

Endpoints:
  GET /api/anomalies/latest    → Most recent ML anomaly detection results
  GET /api/anomalies/range     → Anomaly results for a node over a time window
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.db.session import DbSession
from app.db.repositories import anomalies as anomalies_repo

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


class AnomalyResponse(BaseModel):
    id: int
    node_id: str
    timestamp: datetime
    anomaly_score: float
    state: str
    model_version: str
    confidence: Optional[float] = None
    raw_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/latest",
    response_model=list[AnomalyResponse],
    summary="Get latest anomaly results",
    description="Returns the newest ML inference outputs and anomaly states.",
)
def get_latest_anomalies(
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=500, description="Max records to return"),
    node_id: Optional[str] = Query(default=None, description="Optional node filter"),
) -> list[AnomalyResponse]:
    try:
        rows = anomalies_repo.get_latest_anomalies(session=db, limit=limit, node_id=node_id)
        return [AnomalyResponse.model_validate(r) for r in rows]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch anomalies: {str(exc)}",
        )


@router.get(
    "/range",
    response_model=list[AnomalyResponse],
    summary="Get anomalies in time range",
    description="Returns anomaly outputs for a node between start and end timestamps.",
)
def get_anomalies_range(
    db: DbSession,
    node_id: str = Query(..., description="Node ID"),
    start: datetime = Query(..., description="Start timestamp (ISO-8601)"),
    end: datetime = Query(..., description="End timestamp (ISO-8601)"),
) -> list[AnomalyResponse]:
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start timestamp cannot be greater than end timestamp",
        )
    try:
        rows = anomalies_repo.get_anomalies_in_range(session=db, node_id=node_id, start=start, end=end)
        return [AnomalyResponse.model_validate(r) for r in rows]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch anomalies range: {str(exc)}",
        )
