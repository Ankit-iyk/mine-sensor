"""CSV loader for later evaluation of labelled hardware recordings."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = {
    "timestamp", "node_id", "tilt_x", "tilt_y",
    "accel_x", "accel_y", "accel_z", "vibration", "label",
}
POSITIVE_LABELS = {"1", "true", "yes", "event", "anomaly", "anomalous"}
NEGATIVE_LABELS = {"0", "false", "no", "normal", "none", "safe"}


def load_real_csv(path: str | Path) -> list[dict[str, Any]]:
    """Load required hardware-log columns and mark contiguous labelled events."""
    source = Path(path)
    with source.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = set(reader.fieldnames or ())
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")
        raw_rows = list(reader)

    output: list[dict[str, Any]] = []
    active_event: dict[str, str] = {}
    previously_positive: dict[str, bool] = {}
    for index, source_row in enumerate(raw_rows):
        node_value = source_row.get("node_id") or ""
        node_id = node_value.strip()
        if not node_id:
            raise ValueError(f"CSV row {index + 2} has an empty node_id")
        try:
            timestamp_value = source_row.get("timestamp") or ""
            timestamp = datetime.fromisoformat(timestamp_value.strip())
            if timestamp.tzinfo is None:
                raise ValueError("timestamp must include a timezone offset")
            label = (source_row.get("label") or "").strip().lower()
            if label not in POSITIVE_LABELS | NEGATIVE_LABELS:
                raise ValueError(f"unsupported label value {label!r}")
            positive = label in POSITIVE_LABELS
            row = {
                "timestamp": timestamp,
                "node_id": node_id,
                "zone_id": "REAL",
                "tilt_x": float(source_row["tilt_x"]),
                "tilt_y": float(source_row["tilt_y"]),
                "accel_x": float(source_row["accel_x"]),
                "accel_y": float(source_row["accel_y"]),
                "accel_z": float(source_row["accel_z"]),
                "vibration": int(float(source_row["vibration"])),
                "is_event": positive,
            }
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid CSV row {index + 2}: {exc}") from exc
        starts_event = positive and not previously_positive.get(node_id, False)
        if starts_event:
            active_event[node_id] = f"real:{node_id}:{timestamp.isoformat()}"
        if not positive:
            active_event.pop(node_id, None)
        previously_positive[node_id] = positive
        row.update({
            "event_id": active_event.get(node_id) if positive else None,
            "event_onset_time": (
                active_event[node_id].split(f"real:{node_id}:", 1)[1]
                if positive else None
            ),
            "event_type": "hardware_label" if positive else "none",
            "step": int(timestamp.timestamp()),
            "seed": None,
            "scenario": "real_data",
            "noise_model": "real_data",
            "severity": 1.0,
        })
        output.append(row)
    if not output:
        raise ValueError("CSV contains no telemetry rows")
    return sorted(output, key=lambda row: (row["timestamp"], row["node_id"]))
