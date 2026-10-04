"""
SUBSENSE — MQTT Client (Phase 3)

Wraps paho-mqtt 2.x in a simple class that:
- Connects to EMQX in a background daemon thread
- Subscribes to all telemetry topics via wildcard
- Reconnects automatically on disconnect
- Exposes is_connected property so /api/health can report status
- Shuts down cleanly when FastAPI lifespan ends

Thread model
------------
paho-mqtt's loop_forever() runs in its own daemon thread.
on_message callbacks execute on that thread and must be fast.
Heavy processing (ML inference, DB writes) must be offloaded to
an async task or thread pool (Phase 5+).

paho-mqtt v2 API notes
----------------------
- Client() requires callback_api_version=CallbackAPIVersion.VERSION2
- on_connect(client, userdata, connect_flags, reason_code, properties)
- on_disconnect(client, userdata, disconnect_flags, reason_code, properties)
- on_message(client, userdata, msg)
- reason_code.is_failure → True means connection error
"""

import threading
import structlog
import paho.mqtt.client as mqtt
from paho.mqtt.reasoncodes import ReasonCode

from app.config import settings
from app.ingestion.message_handler import handle_message

logger = structlog.get_logger(__name__)


class MQTTClient:
    """
    Lifecycle-managed MQTT subscriber.

    Usage
    -----
        client = MQTTClient()
        client.start()     # call at app startup
        ...
        client.stop()      # call at app shutdown
    """

    def __init__(self) -> None:
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.mqtt_client_id,
            protocol=mqtt.MQTTv311,
        )
        self._thread: threading.Thread | None = None
        self._connected: bool = False

    # ── Public interface ────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        """Connect to EMQX and start the background loop thread."""
        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message    = self._on_message

        if settings.mqtt_username:
            self._client.username_pw_set(
                settings.mqtt_username,
                settings.mqtt_password,
            )

        # Enable automatic reconnect (paho 2.x)
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        try:
            self._client.connect(
                host=settings.mqtt_host,
                port=settings.mqtt_port,
                keepalive=settings.mqtt_keepalive,
            )
        except OSError as exc:
            logger.error(
                "mqtt_connect_failed",
                host=settings.mqtt_host,
                port=settings.mqtt_port,
                error=str(exc),
                hint="Is EMQX running? Try: docker compose up -d",
            )
            # Do not raise — backend starts in degraded mode and retries
            return

        self._thread = threading.Thread(
            target=self._client.loop_forever,
            name="mqtt-loop",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "mqtt_client_started",
            host=settings.mqtt_host,
            port=settings.mqtt_port,
            topic_wildcard=settings.telemetry_topic_wildcard,
        )

    def stop(self) -> None:
        """Disconnect cleanly and stop the loop thread."""
        self._client.disconnect()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("mqtt_client_stopped")

    # ── paho callbacks ──────────────────────────────────────────────────────

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        connect_flags: mqtt.ConnectFlags,
        reason_code: ReasonCode,
        properties: object,
    ) -> None:
        if reason_code.is_failure:
            logger.error(
                "mqtt_connect_rejected",
                reason=str(reason_code),
                hint="Check EMQX credentials or firewall.",
            )
            return

        self._connected = True
        topic = settings.telemetry_topic_wildcard
        client.subscribe(topic, qos=settings.mqtt_qos)
        logger.info(
            "mqtt_connected",
            topic=topic,
            qos=settings.mqtt_qos,
        )

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: ReasonCode,
        properties: object,
    ) -> None:
        self._connected = False
        if reason_code.is_failure:
            logger.warning(
                "mqtt_unexpected_disconnect",
                reason=str(reason_code),
                note="paho will attempt automatic reconnect.",
            )
        else:
            logger.info("mqtt_clean_disconnect")

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: object,
        msg: mqtt.MQTTMessage,
    ) -> None:
        """
        Called for every incoming MQTT message.
        Delegates immediately to message_handler to keep this method thin.
        """
        try:
            handle_message(topic=msg.topic, raw_payload=msg.payload)
        except Exception as exc:
            # Catch-all: a handler crash must never kill the MQTT loop
            logger.error(
                "mqtt_message_handler_error",
                topic=msg.topic,
                error=str(exc),
                exc_info=True,
            )


# ── Singleton shared across the FastAPI app ─────────────────────────────────
mqtt_client = MQTTClient()
