"""Per-device signed telemetry authentication and replay protection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
from threading import Lock
from typing import Any

from app.config import settings


MAX_TIMESTAMP_SKEW = timedelta(seconds=60)
_NONCE_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{16,128}$")
_REPLAY_LOCK = Lock()
_SEEN_NONCES: dict[tuple[str, str], datetime] = {}
_MAX_REPLAY_ENTRIES = 100_000


@dataclass(frozen=True)
class AuthDecision:
    authenticated: bool
    reason: str


def canonical_payload(payload: Mapping[str, Any]) -> bytes:
    """Serialize telemetry fields outside the separately signed auth envelope."""
    telemetry = {
        key: value
        for key, value in payload.items()
        if key not in {"node_id", "timestamp", "nonce", "signature"}
    }
    return json.dumps(
        telemetry,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_message(payload: Mapping[str, Any]) -> bytes:
    """Build the signed node_id|timestamp|nonce|canonical-JSON message."""
    node_id = payload.get("node_id")
    timestamp = payload.get("timestamp")
    nonce = payload.get("nonce")
    if not isinstance(node_id, str) or not node_id or "|" in node_id:
        raise ValueError("node_id must be a non-empty string without the separator")
    if not isinstance(timestamp, str) or not timestamp:
        raise ValueError("timestamp must be a non-empty string")
    if not isinstance(nonce, str) or not nonce:
        raise ValueError("node_id, timestamp, and nonce are required strings")
    return b"|".join(
        (
            node_id.encode("utf-8"),
            timestamp.encode("utf-8"),
            nonce.encode("utf-8"),
            canonical_payload(payload),
        )
    )


def sign_telemetry_payload(payload: Mapping[str, Any], device_key: str) -> str:
    """Create the lowercase SHA-256 HMAC used by device clients and tests."""
    if not isinstance(device_key, str) or not device_key:
        raise ValueError("device key must be a non-empty string")
    return hmac.new(
        device_key.encode("utf-8"),
        canonical_message(payload),
        hashlib.sha256,
    ).hexdigest()


def authenticate_telemetry(
    payload: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> AuthDecision:
    """Verify node key, HMAC, timestamp freshness, and one-time nonce atomically."""
    node_id = payload.get("node_id")
    if not isinstance(node_id, str) or not node_id or "|" in node_id:
        return AuthDecision(False, "missing_or_malformed_node_id")

    timestamp_text = payload.get("timestamp")
    if not isinstance(timestamp_text, str) or not timestamp_text:
        return AuthDecision(False, "missing_or_malformed_timestamp")
    try:
        timestamp = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
    except ValueError:
        return AuthDecision(False, "missing_or_malformed_timestamp")
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return AuthDecision(False, "timestamp_must_include_timezone")

    nonce = payload.get("nonce")
    if not isinstance(nonce, str) or not _NONCE_PATTERN.fullmatch(nonce):
        return AuthDecision(False, "missing_or_malformed_nonce")

    signature = payload.get("signature")
    if not isinstance(signature, str) or len(signature) != 64:
        return AuthDecision(False, "missing_or_malformed_signature")

    device_key = settings.hardware_device_keys.get(node_id)
    if not isinstance(device_key, str) or not device_key:
        return AuthDecision(False, "unknown_device")
    if len(device_key.encode("utf-8")) < 32:
        return AuthDecision(False, "device_key_too_short")

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("authentication clock must be timezone-aware")
    current_time = current_time.astimezone(timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
    if abs(current_time - timestamp) > MAX_TIMESTAMP_SKEW:
        return AuthDecision(False, "timestamp_outside_allowed_skew")

    try:
        expected = sign_telemetry_payload(payload, device_key)
    except (TypeError, ValueError):
        return AuthDecision(False, "malformed_signed_payload")
    if not hmac.compare_digest(expected, signature):
        return AuthDecision(False, "invalid_signature")

    nonce_key = (node_id, nonce)
    with _REPLAY_LOCK:
        for key, expires_at in list(_SEEN_NONCES.items()):
            if expires_at <= current_time:
                del _SEEN_NONCES[key]
        if nonce_key in _SEEN_NONCES:
            return AuthDecision(False, "replayed_nonce")
        if len(_SEEN_NONCES) >= _MAX_REPLAY_ENTRIES:
            return AuthDecision(False, "replay_cache_full")
        _SEEN_NONCES[nonce_key] = current_time + 2 * MAX_TIMESTAMP_SKEW

    return AuthDecision(True, "verified")


def classify_telemetry_payload(
    payload: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> tuple[dict[str, Any], AuthDecision]:
    """Strip authentication metadata and assign an internal, trusted source label."""
    decision = authenticate_telemetry(payload, now=now)
    if payload.get("source") == "simulator":
        source = "simulator"
    elif decision.authenticated:
        source = "hardware"
    else:
        source = "unknown"

    reading_payload = {
        key: value
        for key, value in payload.items()
        if key not in {"signature", "nonce", "hardware_device_key"}
    }
    reading_payload["source"] = source
    return reading_payload, decision


def clear_replay_cache() -> None:
    """Clear volatile replay state for isolated tests."""
    with _REPLAY_LOCK:
        _SEEN_NONCES.clear()
