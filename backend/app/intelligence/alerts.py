"""
SUBSENSE — Alert Engine & Debounced Incident Lifecycle (Phase 12 & 13)

Responsibilities:
1. Anti-Flicker Debounce: Requires consecutive anomalous evaluations (default: 3)
   before firing an active alert or creating an incident.
2. Severity Mapping:
   - Risk >= 80  → CRITICAL
   - Risk >= 70  → HIGH
   - Risk >= 50  → MEDIUM
   - Risk >= 40  → LOW
3. Automated Incident Lifecycle:
   - Opens persistent Incidents in database when persistent warning/danger occurs.
   - Auto-resolves incidents when ground stabilizes in SAFE for >= 5 consecutive samples.
4. Broadcast Dispatcher: Delivers alerts to real-time subscribers (WebSockets).
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional
import structlog

from app.intelligence.risk_engine import RiskAssessment
from app.db.repositories.incidents import create_incident_safe, resolve_incident_safe

logger = structlog.get_logger(__name__)


@dataclass
class AlertEvent:
    """Dispatched alert event payload."""
    event_id: str
    node_id: str
    zone_id: str
    timestamp: datetime
    severity: str          # LOW | MEDIUM | HIGH | CRITICAL
    risk_score: float
    state: str             # WARNING | DANGER
    reason: str
    affected_nodes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "node_id": self.node_id,
            "zone_id": self.zone_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "risk_score": self.risk_score,
            "state": self.state,
            "reason": self.reason,
            "affected_nodes": self.affected_nodes,
        }


class AlertEngine:
    """
    Stateful alert debouncer and incident tracker.
    """

    CONSECUTIVE_THRESHOLD: int = 3   # 3 consecutive samples to trigger an alert
    SAFE_RESOLUTION_THRESHOLD: int = 5  # 5 consecutive safe samples to resolve incident

    def __init__(self, persist_to_db: bool = True) -> None:
        self.persist_to_db = persist_to_db
        # Node consecutive state tracker: node_id -> {"state": str, "count": int, "has_active_alert": bool}
        self._node_states: dict[str, dict[str, Any]] = {}
        # Subscribers for real-time dispatch (e.g. WebSocket manager)
        self._listeners: list[Callable[[AlertEvent], None]] = []

    def register_listener(self, callback: Callable[[AlertEvent], None]) -> None:
        self._listeners.append(callback)

    def process_risk(
        self,
        risk: RiskAssessment,
        affected_nodes: Optional[list[str]] = None,
    ) -> Optional[AlertEvent]:
        node_id = risk.node_id
        current_state = risk.state

        if node_id not in self._node_states:
            self._node_states[node_id] = {
                "last_state": "SAFE",
                "consecutive_count": 0,
                "has_active_incident": False,
            }

        tracker = self._node_states[node_id]

        if current_state == tracker["last_state"]:
            tracker["consecutive_count"] += 1
        else:
            tracker["last_state"] = current_state
            tracker["consecutive_count"] = 1

        # ── 1. Alert Trigger (Persistent WARNING / DANGER) ──
        if current_state in ("WARNING", "DANGER"):
            if tracker["consecutive_count"] >= self.CONSECUTIVE_THRESHOLD:
                # Severity determination
                if risk.risk_score >= 80.0:
                    severity = "CRITICAL"
                elif risk.risk_score >= 70.0:
                    severity = "HIGH"
                elif risk.risk_score >= 50.0:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"

                primary_reason = risk.reasons[0] if risk.reasons else f"Elevated {current_state} risk"
                nodes_list = affected_nodes or [node_id]

                event = AlertEvent(
                    event_id=f"alert-{node_id}-{int(risk.timestamp.timestamp())}",
                    node_id=node_id,
                    zone_id=risk.zone_id,
                    timestamp=risk.timestamp,
                    severity=severity,
                    risk_score=risk.risk_score,
                    state=current_state,
                    reason=primary_reason,
                    affected_nodes=nodes_list,
                )

                # Persist incident to DB if not already open
                if not tracker["has_active_incident"] and self.persist_to_db:
                    create_incident_safe(
                        node_id=node_id,
                        zone_id=risk.zone_id,
                        severity=severity,
                        risk_score=risk.risk_score,
                        reason=primary_reason,
                        affected_nodes=nodes_list,
                    )
                    tracker["has_active_incident"] = True

                logger.warning(
                    "alert_dispatched",
                    node_id=node_id,
                    severity=severity,
                    risk_score=risk.risk_score,
                    state=current_state,
                    reason=primary_reason,
                )

                # Broadcast to subscribers
                for listener in self._listeners:
                    try:
                        listener(event)
                    except Exception as exc:
                        logger.error("alert_listener_failed", error=str(exc))

                return event

        # ── 2. Auto-Resolution (Persistent SAFE) ────────────
        elif current_state == "SAFE":
            if tracker["has_active_incident"] and tracker["consecutive_count"] >= self.SAFE_RESOLUTION_THRESHOLD:
                if self.persist_to_db:
                    resolve_incident_safe(node_id)
                tracker["has_active_incident"] = False
                logger.info("incident_auto_resolved", node_id=node_id)

        return None

    def reset(self) -> None:
        self._node_states.clear()


# Global singleton instance
alert_engine = AlertEngine()
