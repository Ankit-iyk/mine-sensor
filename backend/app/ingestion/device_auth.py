"""Authentication helpers for hardware-origin telemetry."""

import hmac

from app.config import settings


def is_valid_hardware_device_key(candidate: str | None) -> bool:
    """Return whether a supplied key matches the configured shared device key."""
    expected = settings.hardware_device_key
    return (
        isinstance(expected, str)
        and bool(expected)
        and isinstance(candidate, str)
        and bool(candidate)
        and hmac.compare_digest(expected, candidate)
    )
