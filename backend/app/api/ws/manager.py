"""
SUBSENSE — WebSocket Connection Manager (Phase 14)

Manages a pool of active WebSocket connections and broadcasts
JSON alert events to all subscribers in real time.

Usage:
    from app.api.ws.manager import ws_manager
    ws_manager.broadcast(alert_event.to_dict())
"""

import asyncio
import json
import structlog
from typing import Any

from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class WebSocketManager:
    """
    Thread-safe async manager for active WebSocket connections.

    broadcast() is called from the synchronous AlertEngine (MQTT thread)
    via asyncio.run_coroutine_threadsafe(), which safely schedules the
    coroutine on the main event loop.
    """

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called at startup to bind the running event loop."""
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info("ws_client_connected", total=len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections = [c for c in self._connections if c is not websocket]
        logger.info("ws_client_disconnected", total=len(self._connections))

    async def _broadcast_async(self, payload: dict[str, Any]) -> None:
        """Send payload JSON to all connected clients; remove broken connections."""
        dead: list[WebSocket] = []
        text = json.dumps(payload)
        for ws in list(self._connections):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def broadcast(self, payload: dict[str, Any]) -> None:
        """
        Thread-safe broadcast. Can be called from the MQTT/pipeline thread.
        If no event loop is bound yet, drops the message gracefully.
        """
        if self._loop is None or not self._loop.is_running():
            return
        asyncio.run_coroutine_threadsafe(self._broadcast_async(payload), self._loop)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Global singleton — imported by both the alert engine and the WS route
ws_manager = WebSocketManager()
