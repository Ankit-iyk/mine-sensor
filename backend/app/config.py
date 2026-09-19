"""
SUBSENSE Backend — Application Settings

Uses pydantic-settings v2 so every value can be overridden
by environment variable or a .env file at the backend root.

Usage
-----
    from app.config import settings
    print(settings.mqtt_host)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    All configuration lives here.
    Fields map 1-to-1 with variables in .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # silently ignore unknown keys in .env
    )

    # ── Application ──────────────────────────────────
    app_name: str = "SUBSENSE Backend"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # ── API Server ───────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)

    # ── MQTT ─────────────────────────────────────────
    mqtt_host: str = "localhost"
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_client_id: str = "subsense-backend-01"
    mqtt_keepalive: int = Field(default=60, ge=5)
    mqtt_topic_prefix: str = "mine"
    mqtt_qos: int = Field(default=1, ge=0, le=2)

    # ── Database (Phase 4) ───────────────────────────
    database_url: str = "postgresql+psycopg2://subsense:subsense_dev@localhost:5432/subsense"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False  # set True to log all SQL

    # ── Signal Processing & Feature Extraction (Phase 5 & 6) ─
    feature_window_size: int = Field(default=60, ge=10, le=600)
    kalman_q_angle: float = 0.001
    kalman_q_rate: float = 0.003
    kalman_r_measure: float = 0.03
    vibration_spike_threshold: float = 0.35  # normalized intensity threshold for event counting
    persistence_tilt_threshold: float = 0.25  # degrees deviation threshold for persistence calc

    # ── ML Model (Phase 8) ───────────────────────────
    ml_model_path: str = ""
    ml_model_version: str = "mock-0.1.0"

    # ── Derived helpers ──────────────────────────────
    @property
    def telemetry_topic_wildcard(self) -> str:
        """Backend subscribes to all zones and nodes."""
        return f"{self.mqtt_topic_prefix}/+/+/telemetry"

    @property
    def telemetry_topic_template(self) -> str:
        """Template for constructing per-node topics."""
        return f"{self.mqtt_topic_prefix}/{{zone_id}}/{{node_id}}/telemetry"


# Single shared instance — import this everywhere
settings = Settings()
