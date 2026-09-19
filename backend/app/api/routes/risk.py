"""
SUBSENSE — Risk API Routes (Phase 11)

Endpoints:
  GET /api/risk/latest    → Most recent risk scores per node
  GET /api/risk/range     → Risk history for a node over a time window
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.db.session import DbSession
from app.db.repositories import risk as risk_repo

router = APIRouter(prefix="/risk", tags=["Risk"])


class RiskResponse(BaseModel):
    id: int
    node_id: str
    zone_id: str
    timestamp: datetime
    risk_score: float
    state: str
    trend: str
    reasons: Optional[str] = None  # JSON-encoded list

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/latest",
    response_model=list[RiskResponse],
    summary="Get latest risk scores",
    description="Returns the newest composite risk assessments, optionally filtered by node or zone.",
)
def get_latest_risk(
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=500, description="Max records to return"),
    node_id: Optional[str] = Query(default=None, description="Optional node filter"),
    zone_id: Optional[str] = Query(default=None, description="Optional zone filter"),
) -> list[RiskResponse]:
    try:
        rows = risk_repo.get_latest_risks(session=db, limit=limit, node_id=node_id, zone_id=zone_id)
        return [RiskResponse.model_validate(r) for r in rows]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch risk data: {str(exc)}",
        )


@router.get(
    "/range",
    response_model=list[RiskResponse],
    summary="Get risk scores in time range",
    description="Returns risk history for a node between start and end timestamps.",
)
def get_risk_range(
    db: DbSession,
    node_id: str = Query(..., description="Node ID"),
    start: datetime = Query(..., description="Start timestamp (ISO-8601)"),
    end: datetime = Query(..., description="End timestamp (ISO-8601)"),
) -> list[RiskResponse]:
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start timestamp cannot be greater than end timestamp",
        )
    try:
        rows = risk_repo.get_risk_in_range(session=db, node_id=node_id, start=start, end=end)
        return [RiskResponse.model_validate(r) for r in rows]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch risk range: {str(exc)}",
        )
