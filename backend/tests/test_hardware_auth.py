import json

from app.ingestion import message_handler


def test_mqtt_hardware_source_requires_payload_device_key(monkeypatch):
    monkeypatch.setattr("app.config.settings.hardware_device_key", "mqtt-secret")
    message_handler._RECENT_MESSAGES.clear()
    handled = []
    monkeypatch.setattr(message_handler, "_dispatch", handled.append)

    payload = {
        "source": "hardware",
        "hardware_device_key": "incorrect-secret",
        "node_id": "N01",
        "zone_id": "Z01",
        "timestamp": "2026-10-24T00:00:00+00:00",
        "accel_x": 0.0,
        "accel_y": 0.0,
        "accel_z": 9.81,
        "tilt_x": 1.0,
        "tilt_y": 0.5,
        "vibration": 0,
    }
    message_handler.handle_message("mine/Z01/N01/telemetry", json.dumps(payload).encode())
    assert handled[-1].source == "unknown"
    assert not hasattr(handled[-1], "hardware_device_key")


def test_mqtt_hardware_source_accepts_valid_payload_device_key(monkeypatch):
    monkeypatch.setattr("app.config.settings.hardware_device_key", "mqtt-secret")
    message_handler._RECENT_MESSAGES.clear()
    handled = []
    monkeypatch.setattr(message_handler, "_dispatch", handled.append)

    payload = {
        "source": "hardware",
        "hardware_device_key": "mqtt-secret",
        "node_id": "N02",
        "zone_id": "Z01",
        "timestamp": "2026-10-24T00:00:01+00:00",
        "accel_x": 0.0,
        "accel_y": 0.0,
        "accel_z": 9.81,
        "tilt_x": 1.0,
        "tilt_y": 0.5,
        "vibration": 0,
    }
    message_handler.handle_message("mine/Z01/N02/telemetry", json.dumps(payload).encode())
    assert handled[-1].source == "hardware"
    assert not hasattr(handled[-1], "hardware_device_key")
