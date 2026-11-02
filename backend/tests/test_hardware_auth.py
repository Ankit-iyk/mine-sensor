import json
from datetime import datetime, timedelta, timezone
import secrets

import pytest

from app.ingestion import message_handler
from app.ingestion.device_auth import (
    authenticate_telemetry,
    classify_telemetry_payload,
    clear_replay_cache,
    sign_telemetry_payload,
)
from app.ingestion.source_tracker import telemetry_source_tracker


DEVICE_KEY = "node-secret-for-tests-0123456789abcdef"


@pytest.fixture
def configured_node(monkeypatch):
    monkeypatch.setattr("app.config.settings.hardware_device_keys", {"N01": DEVICE_KEY})
    clear_replay_cache()
    telemetry_source_tracker.clear()
    yield
    clear_replay_cache()
    telemetry_source_tracker.clear()


def _payload(**overrides):
    payload = {
        "source": "hardware",
        "node_id": "N01",
        "zone_id": "Z01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nonce": secrets.token_hex(16),
        "accel_x": 0.0,
        "accel_y": 0.0,
        "accel_z": 9.81,
        "tilt_x": 1.0,
        "tilt_y": 0.5,
        "vibration": 0,
    }
    payload.update(overrides)
    return payload


def _signed_payload(**overrides):
    payload = _payload(**overrides)
    payload["signature"] = sign_telemetry_payload(payload, DEVICE_KEY)
    return payload


def test_missing_signature_and_forged_hardware_source_are_not_live(configured_node):
    classified, decision = classify_telemetry_payload(_payload())

    assert not decision.authenticated
    assert decision.reason == "missing_or_malformed_signature"
    assert classified["source"] == "unknown"
    telemetry_source_tracker.record(classified["source"], signed_hardware=decision.authenticated)
    assert telemetry_source_tracker.status()["mode"] == "OFFLINE"


def test_wrong_key_signature_is_rejected(configured_node):
    payload = _payload()
    payload["signature"] = sign_telemetry_payload(payload, "wrong-node-key")

    classified, decision = classify_telemetry_payload(payload)

    assert not decision.authenticated
    assert decision.reason == "invalid_signature"
    assert classified["source"] == "unknown"


def test_expired_signed_timestamp_is_rejected(configured_node):
    expired = (datetime.now(timezone.utc) - timedelta(seconds=61)).isoformat()
    payload = _signed_payload(timestamp=expired)

    decision = authenticate_telemetry(payload)

    assert not decision.authenticated
    assert decision.reason == "timestamp_outside_allowed_skew"


def test_nonce_replay_is_rejected_even_with_a_valid_signature(configured_node):
    payload = _signed_payload()

    assert authenticate_telemetry(payload).authenticated
    replay = authenticate_telemetry(payload)

    assert not replay.authenticated
    assert replay.reason == "replayed_nonce"


def test_simulator_source_stays_simulated_without_a_signature(configured_node):
    classified, decision = classify_telemetry_payload(
        _payload(source="simulator")
    )

    assert not decision.authenticated
    assert classified["source"] == "simulator"
    telemetry_source_tracker.record(classified["source"], signed_hardware=decision.authenticated)
    assert telemetry_source_tracker.status()["mode"] == "SIMULATED"


def test_mqtt_requires_valid_signature_and_strips_auth_fields(configured_node, monkeypatch):
    message_handler._RECENT_MESSAGES.clear()
    handled = []
    monkeypatch.setattr(message_handler, "_dispatch", handled.append)

    unsigned = _payload()
    message_handler.handle_message(
        "mine/Z01/N01/telemetry",
        json.dumps(unsigned).encode(),
    )
    assert handled[-1].source == "unknown"
    assert telemetry_source_tracker.status()["mode"] == "OFFLINE"

    signed = _signed_payload()
    message_handler.handle_message(
        "mine/Z01/N01/telemetry",
        json.dumps(signed).encode(),
    )
    assert handled[-1].source == "hardware"
    assert not hasattr(handled[-1], "signature")
    assert not hasattr(handled[-1], "nonce")
    assert telemetry_source_tracker.status()["mode"] == "LIVE"


def test_mqtt_signed_simulator_payload_never_sets_live(configured_node, monkeypatch):
    message_handler._RECENT_MESSAGES.clear()
    handled = []
    monkeypatch.setattr(message_handler, "_dispatch", handled.append)
    simulator = _signed_payload(source="simulator")

    message_handler.handle_message(
        "mine/Z01/N01/telemetry",
        json.dumps(simulator).encode(),
    )

    assert handled[-1].source == "simulator"
    assert telemetry_source_tracker.status()["mode"] == "SIMULATED"
