"""
SUBSENSE — Incidents API Routes (Phase 13)

Endpoints:
  GET  /api/incidents          → List incidents (filterable by status/zone)
  GET  /api/incidents/{id}     → Single incident detail
  POST /api/incidents/{id}/resolve  → Manually resolve an active incident
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict

from app.db.session import DbSession, SessionLocal
from app.db.repositories.incidents import (
    get_incidents,
    get_active_incident_for_node,
    resolve_incident_safe,
)
from app.db.models import Incident
from sqlalchemy import select

router = APIRouter(prefix="/incidents", tags=["Incidents"])


class IncidentResponse(BaseModel):
    id: int
    node_id: str
    zone_id: str
    created_at: datetime
    severity: str
    risk_score: float
    reason: str
    status: str
    resolved_at: Optional[datetime] = None
    affected_nodes: Optional[str] = None  # JSON list as string

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "",
    response_model=list[IncidentResponse],
    summary="List incidents",
    description="Returns incidents filtered by status and/or zone, newest first.",
)
def list_incidents(
    db: DbSession,
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by incident status: ACTIVE | RESOLVED",
    ),
    zone_id: Optional[str] = Query(default=None, description="Filter by zone"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
) -> list[IncidentResponse]:
    try:
        rows = get_incidents(session=db, status=status_filter, zone_id=zone_id, limit=limit)
        return [IncidentResponse.model_validate(r) for r in rows]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list incidents: {str(exc)}",
        )


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident by ID",
    description="Returns full detail for a single incident.",
)
def get_incident(
    db: DbSession,
    incident_id: int = Path(..., description="Incident primary key"),
) -> IncidentResponse:
    row = db.get(Incident, incident_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return IncidentResponse.model_validate(row)


@router.post(
    "/{incident_id}/resolve",
    response_model=IncidentResponse,
    summary="Manually resolve an incident",
    description="Marks an ACTIVE incident as RESOLVED immediately.",
)
def resolve_incident(
    db: DbSession,
    incident_id: int = Path(..., description="Incident primary key"),
) -> IncidentResponse:
    row = db.get(Incident, incident_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    if row.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Incident {incident_id} is already {row.status}",
        )
    row.status = "RESOLVED"
    row.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return IncidentResponse.model_validate(row)
