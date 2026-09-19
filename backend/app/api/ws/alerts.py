"""
SUBSENSE — WebSocket Alert Stream (Phase 14)

Endpoint:
  WS /ws/alerts   → Subscribe to real-time alert events

Clients receive JSON-encoded AlertEvent dicts whenever the Alert Engine
fires an alert (severity LOW/MEDIUM/HIGH/CRITICAL).

Example message:
{
  "event_id": "alert-N01-1726123456",
  "node_id": "N01",
  "zone_id": "Z01",
  "timestamp": "2026-09-19T10:00:00+00:00",
  "severity": "HIGH",
  "risk_score": 74.3,
  "state": "DANGER",
  "reason": "Accelerating angular displacement detected",
  "affected_nodes": ["N01", "N02"]
}
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

from app.api.ws.manager import ws_manager

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time alert streaming.
    Dashboard clients connect here to receive live AlertEvent payloads.
    """
    await ws_manager.connect(websocket)
    try:
        # Keep the connection alive; server pushes alerts proactively
        while True:
            # We still receive pings / client messages to detect disconnects
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("ws_alerts_client_left")
    except Exception as exc:
        ws_manager.disconnect(websocket)
        logger.warning("ws_alerts_unexpected_close", error=str(exc))
