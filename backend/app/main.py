"""
SUBSENSE Backend — FastAPI Application Entry Point

Startup sequence
----------------
1. configure_logging()      → structured JSON/pretty logs
2. ws_manager event loop    → bind async loop so WS broadcasts work from threads
3. alert_engine listener    → wire AlertEngine → WebSocket broadcast
4. mqtt_client.start()      → connect to EMQX, subscribe to telemetry wildcard
5. Yield (app running)
6. mqtt_client.stop()       → clean disconnect on shutdown

Routes registered
-----------------
- GET  /api/health           → liveness probe
- POST /api/telemetry        → ingest telemetry payload
- GET  /api/features/latest  → latest extracted feature vectors
- GET  /api/features/range   → feature history for node in time window
- GET  /api/anomalies/latest → latest ML anomaly results
- GET  /api/anomalies/range  → anomaly history in time window
- GET  /api/risk/latest      → latest composite risk scores
- GET  /api/risk/range       → risk history in time window
- GET  /api/incidents        → list incidents (ACTIVE/RESOLVED)
- GET  /api/incidents/{id}   → single incident detail
- POST /api/incidents/{id}/resolve → manually resolve an incident
- WS   /ws/alerts            → real-time alert event stream
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import configure_logging
from app.api.routes import health, telemetry, readings, features, anomalies
from app.api.routes import risk, incidents
from app.api.ws.alerts import router as ws_router
from app.api.ws.manager import ws_manager
from app.ingestion.mqtt_client import mqtt_client
from app.db.session import check_db_connection, init_db

# Configure logging before anything else writes a log line
configure_logging()
logger = structlog.get_logger(__name__)


# ── Lifespan (startup / shutdown) ───────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ── Startup ──────────────────────────────────────
    logger.info(
        "subsense_starting",
        version=settings.app_version,
        mqtt_host=settings.mqtt_host,
        mqtt_port=settings.mqtt_port,
    )

    # Bind the running event loop to the WebSocket manager so that
    # the synchronous MQTT/processing thread can broadcast alerts
    loop = asyncio.get_event_loop()
    ws_manager.set_event_loop(loop)

    # Wire the AlertEngine to broadcast events over WebSocket
    from app.intelligence.alerts import alert_engine
    alert_engine.register_listener(lambda event: ws_manager.broadcast(event.to_dict()))
    logger.info("alert_ws_listener_registered")

    mqtt_client.start()

    # Check and initialize database tables if reachable
    if check_db_connection():
        logger.info("db_connected_initializing")
        try:
            init_db()
        except Exception as exc:
            logger.warning("db_init_skipped", reason=str(exc))
    else:
        logger.warning(
            "db_not_reachable",
            note="Backend will run in degraded mode. Start PostgreSQL/TimescaleDB via docker compose.",
        )

    yield  # ← application is running

    # ── Shutdown ─────────────────────────────────────
    logger.info("subsense_stopping")
    mqtt_client.stop()


# ── Application factory ─────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "SUBSENSE — Predictive Mine Subsidence Intelligence System. "
            "Research prototype. NOT a certified mine-safety system."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — permissive in dev; restrict origins in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── REST Routers ──────────────────────────────────
    app.include_router(health.router, prefix="/api")
    app.include_router(telemetry.router, prefix="/api")
    app.include_router(readings.router, prefix="/api")
    app.include_router(features.router, prefix="/api")
    app.include_router(anomalies.router, prefix="/api")
    app.include_router(risk.router, prefix="/api")
    app.include_router(incidents.router, prefix="/api")

    # ── WebSocket Router ──────────────────────────────
    app.include_router(ws_router)

    return app


app = create_app()
