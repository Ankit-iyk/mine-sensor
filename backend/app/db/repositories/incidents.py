"""
SUBSENSE — Incidents Repository (Phase 13)

Database operations for the incidents table (alert tracking & lifecycle).
"""

from datetime import datetime, timezone
import json
from typing import Optional
import structlog
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.db.models import Incident

logger = structlog.get_logger(__name__)


def create_incident(
    session: Session,
    node_id: str,
    zone_id: str,
    severity: str,
    risk_score: float,
    reason: str,
    affected_nodes: Optional[list[str]] = None,
) -> Incident:
    """Create a new active incident record."""
    affected_json = json.dumps(affected_nodes or [node_id])
    incident = Incident(
        node_id=node_id,
        zone_id=zone_id,
        severity=severity,
        risk_score=round(float(risk_score), 2),
        reason=reason,
        status="ACTIVE",
        affected_nodes=affected_json,
    )
    session.add(incident)
    session.flush()
    return incident


def create_incident_safe(
    node_id: str,
    zone_id: str,
    severity: str,
    risk_score: float,
    reason: str,
    affected_nodes: Optional[list[str]] = None,
) -> Optional[int]:
    """Thread-safe incident creation in its own transaction."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        incident = create_incident(
            session=db,
            node_id=node_id,
            zone_id=zone_id,
            severity=severity,
            risk_score=risk_score,
            reason=reason,
            affected_nodes=affected_nodes,
        )
        db.commit()
        return incident.id
    except Exception as exc:
        db.rollback()
        logger.error("db_create_incident_failed", node_id=node_id, error=str(exc))
        return None
    finally:
        db.close()


def get_active_incident_for_node(session: Session, node_id: str) -> Optional[Incident]:
    """Find currently active incident for a node if one exists."""
    stmt = (
        select(Incident)
        .where(Incident.node_id == node_id, Incident.status == "ACTIVE")
        .order_by(desc(Incident.created_at))
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def resolve_incident_safe(node_id: str) -> bool:
    """Resolve any active incidents for a node when ground returns to SAFE."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        stmt = select(Incident).where(Incident.node_id == node_id, Incident.status == "ACTIVE")
        active_incidents = db.execute(stmt).scalars().all()
        now = datetime.now(timezone.utc)
        for inc in active_incidents:
            inc.status = "RESOLVED"
            inc.resolved_at = now
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        logger.error("db_resolve_incident_failed", node_id=node_id, error=str(exc))
        return False
    finally:
        db.close()


def get_incidents(
    session: Session,
    status: Optional[str] = None,
    zone_id: Optional[str] = None,
    limit: int = 50,
) -> list[Incident]:
    """Query incidents with optional filters."""
    stmt = select(Incident).order_by(desc(Incident.created_at))
    if status:
        stmt = stmt.where(Incident.status == status)
    if zone_id:
        stmt = stmt.where(Incident.zone_id == zone_id)
    stmt = stmt.limit(min(limit, 200))
    return list(session.execute(stmt).scalars().all())
