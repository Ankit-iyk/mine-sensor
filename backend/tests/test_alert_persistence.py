from datetime import datetime, timezone

from app.intelligence import alerts
from app.intelligence.alerts import AlertEngine
from app.intelligence.risk_engine import RiskAssessment


def test_pipeline_persistence_override_prevents_incident_database_writes(monkeypatch):
    create_calls = []
    resolve_calls = []
    monkeypatch.setattr(
        alerts,
        "create_incident_safe",
        lambda **kwargs: create_calls.append(kwargs),
    )
    monkeypatch.setattr(
        alerts,
        "resolve_incident_safe",
        lambda node_id: resolve_calls.append(node_id),
    )
    engine = AlertEngine(persist_to_db=True)
    timestamp = datetime.now(timezone.utc)

    warning = RiskAssessment(
        node_id="N01",
        zone_id="Z01",
        timestamp=timestamp,
        risk_score=50.0,
        state="WARNING",
        trend="STABLE",
    )
    for _ in range(engine.CONSECUTIVE_THRESHOLD):
        engine.process_risk(warning, persist_to_db=False)

    assert create_calls == []

    tracker = engine._node_states["N01"]
    tracker["has_active_incident"] = True
    safe = RiskAssessment(
        node_id="N01",
        zone_id="Z01",
        timestamp=timestamp,
        risk_score=0.0,
        state="SAFE",
        trend="STABLE",
    )
    for _ in range(engine.SAFE_RESOLUTION_THRESHOLD):
        engine.process_risk(safe, persist_to_db=False)

    assert resolve_calls == []
