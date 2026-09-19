"""
SUBSENSE — Risk Results Repository (Phase 11)

Database persistence and query methods for the risk_results table.
"""

from datetime import datetime
import json
from typing import Any, Optional
import structlog
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.db.models import RiskResult

logger = structlog.get_logger(__name__)


def save_risk(
    session: Session,
    node_id: str,
    zone_id: str,
    timestamp: datetime,
    risk_score: float,
    state: str,
    trend: str = "STABLE",
    reasons: Optional[list[str]] = None,
) -> RiskResult:
    """Persist a computed risk result to the database."""
    reasons_json = json.dumps(reasons or [])
    row = RiskResult(
        node_id=node_id,
        zone_id=zone_id,
        timestamp=timestamp,
        risk_score=round(float(risk_score), 2),
        state=state,
        trend=trend,
        reasons=reasons_json,
    )
    session.add(row)
    session.flush()
    return row


def save_risk_safe(
    node_id: str,
    zone_id: str,
    timestamp: datetime,
    risk_score: float,
    state: str,
    trend: str = "STABLE",
    reasons: Optional[list[str]] = None,
) -> bool:
    """Thread-safe write in its own transaction for ingestion/pipeline worker."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        save_risk(
            session=db,
            node_id=node_id,
            zone_id=zone_id,
            timestamp=timestamp,
            risk_score=risk_score,
            state=state,
            trend=trend,
            reasons=reasons,
        )
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        logger.error("db_save_risk_failed", node_id=node_id, error=str(exc))
        return False
    finally:
        db.close()


def get_latest_risks(
    session: Session,
    limit: int = 50,
    node_id: Optional[str] = None,
    zone_id: Optional[str] = None,
) -> list[RiskResult]:
    """Return latest risk results, newest first."""
    stmt = select(RiskResult).order_by(desc(RiskResult.timestamp))
    if node_id:
        stmt = stmt.where(RiskResult.node_id == node_id)
    if zone_id:
        stmt = stmt.where(RiskResult.zone_id == zone_id)
    stmt = stmt.limit(min(limit, 500))
    return list(session.execute(stmt).scalars().all())


def get_risk_in_range(
    session: Session,
    node_id: str,
    start: datetime,
    end: datetime,
) -> list[RiskResult]:
    """Return risk records for a node in a given time interval."""
    stmt = (
        select(RiskResult)
        .where(
            RiskResult.node_id == node_id,
            RiskResult.timestamp >= start,
            RiskResult.timestamp <= end,
        )
        .order_by(RiskResult.timestamp)
    )
    return list(session.execute(stmt).scalars().all())
