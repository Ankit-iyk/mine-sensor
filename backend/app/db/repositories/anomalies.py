"""
SUBSENSE — Anomaly Results Repository (Phase 8)

Database persistence and queries for the anomaly_results table.
"""

from datetime import datetime
from typing import Any, Optional
import structlog
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.db.models import AnomalyResult

logger = structlog.get_logger(__name__)


def save_anomaly(
    session: Session,
    node_id: str,
    timestamp: datetime,
    inference: dict[str, Any],
) -> AnomalyResult:
    """Persist an ML inference result to anomaly_results table."""
    row = AnomalyResult(
        node_id=node_id,
        timestamp=timestamp,
        anomaly_score=float(inference["anomaly_score"]),
        state=str(inference["state"]),
        model_version=str(inference["model_version"]),
        confidence=float(inference["confidence"]) if inference.get("confidence") is not None else None,
        raw_score=float(inference["raw_score"]) if inference.get("raw_score") is not None else None,
    )
    session.add(row)
    session.flush()
    return row


def save_anomaly_safe(
    node_id: str,
    timestamp: datetime,
    inference: dict[str, Any],
) -> bool:
    """Thread-safe write in its own transaction for ingestion/pipeline worker."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        save_anomaly(db, node_id, timestamp, inference)
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        logger.error("db_save_anomaly_failed", node_id=node_id, error=str(exc))
        return False
    finally:
        db.close()


def get_latest_anomalies(
    session: Session,
    limit: int = 50,
    node_id: Optional[str] = None,
) -> list[AnomalyResult]:
    """Return latest anomaly results, newest first."""
    stmt = select(AnomalyResult).order_by(desc(AnomalyResult.timestamp))
    if node_id:
        stmt = stmt.where(AnomalyResult.node_id == node_id)
    stmt = stmt.limit(min(limit, 500))
    return list(session.execute(stmt).scalars().all())


def get_anomalies_in_range(
    session: Session,
    node_id: str,
    start: datetime,
    end: datetime,
) -> list[AnomalyResult]:
    """Return anomalies for a node in a given time interval."""
    stmt = (
        select(AnomalyResult)
        .where(
            AnomalyResult.node_id == node_id,
            AnomalyResult.timestamp >= start,
            AnomalyResult.timestamp <= end,
        )
        .order_by(AnomalyResult.timestamp)
    )
    return list(session.execute(stmt).scalars().all())
