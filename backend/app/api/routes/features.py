"""
SUBSENSE — Features API Routes (Phase 6)

Endpoints:
  GET /api/features/latest    → Most recent extracted features
  GET /api/features/range     → Extracted features for a node over a time window
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.db.session import DbSession
from app.db.repositories import features as features_repo

router = APIRouter(prefix="/features", tags=["Features"])


class FeatureResponse(BaseModel):
    id: int
    node_id: str
    timestamp: datetime
    tilt_deviation: float
    tilt_rate: float
    vibration_intensity: float
    vibration_frequency: float
    rolling_mean_tilt: float
    rolling_std_tilt: float
    rolling_mean_vib: float
    rolling_std_vib: float
    persistence: float
    trend_slope: float

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/latest",
    response_model=list[FeatureResponse],
    summary="Get latest extracted features",
    description="Returns the newest feature vectors computed by the signal processing pipeline.",
)
def get_latest_features(
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=500, description="Max records to return"),
    node_id: Optional[str] = Query(default=None, description="Optional node filter"),
) -> list[FeatureResponse]:
    try:
        rows = features_repo.get_latest_features(session=db, limit=limit, node_id=node_id)
        return [FeatureResponse.model_validate(r) for r in rows]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch features: {str(exc)}",
        )


@router.get(
    "/range",
    response_model=list[FeatureResponse],
    summary="Get features in time range",
    description="Returns features for a node between start and end timestamps.",
)
def get_features_range(
    db: DbSession,
    node_id: str = Query(..., description="Node ID"),
    start: datetime = Query(..., description="Start timestamp (ISO-8601)"),
    end: datetime = Query(..., description="End timestamp (ISO-8601)"),
) -> list[FeatureResponse]:
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start timestamp cannot be greater than end timestamp",
        )
    try:
        rows = features_repo.get_features_in_range(session=db, node_id=node_id, start=start, end=end)
        return [FeatureResponse.model_validate(r) for r in rows]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch features range: {str(exc)}",
        )
