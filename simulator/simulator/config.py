"""
SUBSENSE Simulator — Configuration

Reads from simulator/.env (or inherits environment variables).
Mirrors the same pattern as the backend config.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class SimulatorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── MQTT ─────────────────────────────────────────
    mqtt_host: str = "localhost"
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_topic_prefix: str = "mine"

    # ── Simulator behaviour ───────────────────────────
    publish_interval: float = Field(
        default=1.0,
        ge=0.1,
        description="Seconds between readings per node.",
    )
    schema_version: str = "1.0"


sim_settings = SimulatorSettings()
