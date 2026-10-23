"""In-memory timestamps for identifying the current telemetry source."""

from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Literal

TelemetrySource = Literal["hardware", "simulator"]
TelemetryMode = Literal["LIVE", "SIMULATED", "OFFLINE"]


class TelemetrySourceTracker:
    def __init__(self, freshness_seconds: int = 30) -> None:
        self.freshness = timedelta(seconds=freshness_seconds)
        self._lock = Lock()
        self._last_seen: dict[TelemetrySource, datetime | None] = {
            "hardware": None,
            "simulator": None,
        }

    def record(self, source: str, seen_at: datetime | None = None) -> None:
        if source not in self._last_seen:
            return

        timestamp = seen_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc)

        with self._lock:
            self._last_seen[source] = timestamp

    def status(self, now: datetime | None = None) -> dict[str, str | None]:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        current_time = current_time.astimezone(timezone.utc)

        with self._lock:
            hardware_seen = self._last_seen["hardware"]
            simulator_seen = self._last_seen["simulator"]

        hardware_is_fresh = self._is_fresh(hardware_seen, current_time)
        simulator_is_fresh = self._is_fresh(simulator_seen, current_time)
        mode: TelemetryMode = (
            "LIVE" if hardware_is_fresh else
            "SIMULATED" if simulator_is_fresh else
            "OFFLINE"
        )
        return {
            "mode": mode,
            "last_hardware_seen": hardware_seen.isoformat() if hardware_seen else None,
            "last_simulator_seen": simulator_seen.isoformat() if simulator_seen else None,
        }

    def clear(self) -> None:
        with self._lock:
            self._last_seen = {"hardware": None, "simulator": None}

    def _is_fresh(self, timestamp: datetime | None, now: datetime) -> bool:
        return timestamp is not None and timedelta(0) <= now - timestamp <= self.freshness


telemetry_source_tracker = TelemetrySourceTracker()
