"""
SUBSENSE Simulator — MQTT Publisher

Converts SensorNode readings (plain dicts) into JSON and publishes
them to the correct MQTT topic.

Topic format: mine/{zone_id}/{node_id}/telemetry
"""

import json
import time
import structlog
import paho.mqtt.client as mqtt

from simulator.config import sim_settings

logger = structlog.get_logger(__name__)


class SimulatorPublisher:
    """
    Manages the MQTT connection for the simulator.

    Usage
    -----
        pub = SimulatorPublisher()
        pub.connect()
        pub.publish("Z01", "N01", reading_dict)
        pub.disconnect()
    """

    def __init__(self) -> None:
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="subsense-simulator",
            protocol=mqtt.MQTTv311,
        )
        self._connected = False

    def connect(self, retries: int = 5, retry_delay: float = 3.0) -> None:
        """
        Connect to the EMQX broker with retry logic.

        The simulator will wait up to (retries × retry_delay) seconds
        for the broker before raising an exception.
        """
        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        if sim_settings.mqtt_username:
            self._client.username_pw_set(
                sim_settings.mqtt_username,
                sim_settings.mqtt_password,
            )

        for attempt in range(1, retries + 1):
            try:
                self._client.connect(
                    host=sim_settings.mqtt_host,
                    port=sim_settings.mqtt_port,
                    keepalive=60,
                )
                self._client.loop_start()
                # Allow time for on_connect to fire
                time.sleep(1.0)
                if self._connected:
                    logger.info(
                        "simulator_connected",
                        host=sim_settings.mqtt_host,
                        port=sim_settings.mqtt_port,
                    )
                    return
            except OSError as exc:
                logger.warning(
                    "simulator_connect_attempt_failed",
                    attempt=attempt,
                    max_attempts=retries,
                    error=str(exc),
                )
            time.sleep(retry_delay)

        raise ConnectionError(
            f"Cannot connect to EMQX at "
            f"{sim_settings.mqtt_host}:{sim_settings.mqtt_port} "
            f"after {retries} attempts. Is the broker running?\n"
            f"  → docker compose up -d"
        )

    def publish(self, zone_id: str, node_id: str, reading: dict) -> None:
        """Serialise a reading dict and publish to the correct topic."""
        if not self._connected:
            logger.warning("simulator_not_connected_skipping", node_id=node_id)
            return

        topic = (
            f"{sim_settings.mqtt_topic_prefix}/{zone_id}/{node_id}/telemetry"
        )
        payload = json.dumps(reading, default=str)

        result = self._client.publish(topic, payload, qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                "simulator_publish_failed",
                topic=topic,
                rc=result.rc,
            )

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("simulator_disconnected")

    # ── paho callbacks ───────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if not reason_code.is_failure:
            self._connected = True
        else:
            logger.error("simulator_connect_rejected", reason=str(reason_code))

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self._connected = False
