"""
SUBSENSE — Sensor Features Repository (Phase 6)

Database persistence and queries for the sensor_features table.
"""

from datetime import datetime
from typing import Optional
import structlog
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.db.models import SensorFeature
from app.processing.schemas import FeatureVector

logger = structlog.get_logger(__name__)


def save_feature(session: Session, feat: FeatureVector) -> SensorFeature:
    """Persist a FeatureVector to the sensor_features table."""
    row = SensorFeature(
        node_id=feat.node_id,
        timestamp=feat.timestamp,
        tilt_deviation=feat.tilt_deviation,
        tilt_rate=feat.tilt_rate,
        vibration_intensity=feat.vibration_intensity,
        vibration_frequency=feat.vibration_frequency,
        rolling_mean_tilt=feat.rolling_mean_tilt,
        rolling_std_tilt=feat.rolling_std_tilt,
        rolling_mean_vib=feat.rolling_mean_vib,
        rolling_std_vib=feat.rolling_std_vib,
        persistence=feat.persistence,
        trend_slope=feat.trend_slope,
    )
    session.add(row)
    session.flush()
    return row


def save_feature_safe(feat: FeatureVector) -> bool:
    """Thread-safe write in its own transaction for ingestion/pipeline worker."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        save_feature(db, feat)
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        logger.error("db_save_feature_failed", node_id=feat.node_id, error=str(exc))
        return False
    finally:
        db.close()


def get_latest_features(
    session: Session,
    limit: int = 50,
    node_id: Optional[str] = None,
) -> list[SensorFeature]:
    """Return latest extracted features, newest first."""
    stmt = select(SensorFeature).order_by(desc(SensorFeature.timestamp))
    if node_id:
        stmt = stmt.where(SensorFeature.node_id == node_id)
    stmt = stmt.limit(min(limit, 500))
    return list(session.execute(stmt).scalars().all())


def get_features_in_range(
    session: Session,
    node_id: str,
    start: datetime,
    end: datetime,
) -> list[SensorFeature]:
    """Return features for a node in a given time interval."""
    stmt = (
        select(SensorFeature)
        .where(
            SensorFeature.node_id == node_id,
            SensorFeature.timestamp >= start,
            SensorFeature.timestamp <= end,
        )
        .order_by(SensorFeature.timestamp)
    )
    return list(session.execute(stmt).scalars().all())
