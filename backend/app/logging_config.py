"""
SUBSENSE — Structured Logging Configuration

Uses structlog to produce consistent, machine-readable JSON logs in
production and clean coloured output in development.

Call configure_logging() once at application startup.

Usage
-----
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("telemetry_received", node_id="N01", tilt_x=1.23)
"""

import logging
import sys
import structlog
from app.config import settings


def configure_logging() -> None:
    """
    Set up structlog with:
    - JSON renderer in production (LOG_LEVEL != DEBUG)
    - Pretty coloured output when DEBUG=true
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure standard library logging so third-party libs (paho, uvicorn)
    # also flow through structlog's processors.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Choose renderer based on environment
    if settings.debug:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
