"""CSV input support for the evaluation feature pipeline."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


POSITIVE_LABELS = {"1", "true", "yes", "event", "anomaly", "anomalous"}
NEGATIVE_LABELS = {"0", "false", "no", "normal", "none", "safe", "stationary"}
EVENT_LOG_COLUMNS = {"event_id", "event_type", "start_timestamp", "duration_s"}
GRAVITY_M_S2 = 9.80665


def load_real_csv(
    path: str | Path,
    event_log_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Load telemetry CSV aliases and optionally expand event-log intervals."""
    source = Path(path)
    with source.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fieldnames = set(reader.fieldnames or ())
        _require_one_of(fieldnames, "timestamp")
        _require_one_of(fieldnames, "tilt_x_deg", "tilt_x")
        _require_one_of(fieldnames, "tilt_y_deg", "tilt_y")
        for axis in "xyz":
            _require_one_of(fieldnames, f"accel_{axis}_g", f"accel_{axis}")
        if "vibration" not in fieldnames:
            raise ValueError("CSV is missing required column: vibration")
        if not ({"label", "event_label", "event_id"} & fieldnames):
            raise ValueError("CSV requires at least one of: label, event_label, event_id")
        raw_rows = list(reader)

    intervals = _load_event_log(event_log_path) if event_log_path else []
    output: list[dict[str, Any]] = []
    active_event: dict[str, str] = {}
    was_event: dict[str, bool] = {}
    for index, source_row in enumerate(raw_rows):
        try:
            timestamp = _parse_timestamp(source_row.get("timestamp", ""))
            node_id = (source_row.get("node_id") or "N01").strip()
            zone_id = (source_row.get("zone_id") or "Z01").strip()
            if not node_id:
                raise ValueError("node_id cannot be empty")
            if not zone_id:
                raise ValueError("zone_id cannot be empty")

            tilt_x = _number(source_row, "tilt_x_deg", "tilt_x")
            tilt_y = _number(source_row, "tilt_y_deg", "tilt_y")
            accel = {
                axis: _number(source_row, f"accel_{axis}_g", f"accel_{axis}")
                for axis in "xyz"
            }
            for axis in "xyz":
                if source_row.get(f"accel_{axis}_g") not in (None, ""):
                    accel[axis] *= GRAVITY_M_S2
            vibration_input = float(source_row["vibration"])
            if not 0.0 <= vibration_input <= 1023.0:
                raise ValueError("vibration must be between 0 and 1023 (or normalized 0 to 1)")
            vibration_adc = round(
                vibration_input * 1023.0 if vibration_input <= 1.0 else vibration_input
            )

            matched = _event_at(timestamp, intervals)
            if event_log_path is not None:
                event_type = matched["event_type"] if matched else "stationary"
                event_id = matched["event_id"] if matched else None
                target_angle = matched["target_angle_deg"] if matched else None
                label = event_type
                is_event = event_type == "tilt"
                onset = matched["start_timestamp"] if matched else None
            else:
                label = (
                    source_row.get("event_label")
                    or source_row.get("label")
                    or ("event" if source_row.get("event_id") else "normal")
                ).strip().lower()
                if label not in POSITIVE_LABELS | NEGATIVE_LABELS | {
                    "tilt", "tap", "phone_vibration",
                }:
                    raise ValueError(f"unsupported label value {label!r}")
                event_type = label if label in {"tilt", "tap", "phone_vibration"} else (
                    "labelled_event" if label in POSITIVE_LABELS else "none"
                )
                is_event = event_type == "tilt" or (
                    event_type == "labelled_event" and label in POSITIVE_LABELS
                )
                event_id = (source_row.get("event_id") or "").strip() or None
                target_angle = None
                onset = timestamp if is_event else None
                if is_event and event_id is None:
                    if not was_event.get(node_id, False):
                        active_event[node_id] = f"csv:{node_id}:{timestamp.isoformat()}"
                    event_id = active_event[node_id]
                    onset = datetime.fromisoformat(event_id.split(f"csv:{node_id}:", 1)[1])
                if not is_event:
                    active_event.pop(node_id, None)
            was_event[node_id] = is_event

            output.append({
                "timestamp": timestamp,
                "node_id": node_id,
                "zone_id": zone_id,
                "tilt_x": tilt_x,
                "tilt_y": tilt_y,
                "accel_x": accel["x"],
                "accel_y": accel["y"],
                "accel_z": accel["z"],
                "vibration": vibration_adc,
                "vibration_input": vibration_input,
                "label": label,
                "is_event": is_event,
                "event_id": event_id if is_event or event_type in {"tap", "phone_vibration"} else None,
                "event_onset_time": onset.isoformat() if onset else None,
                "event_type": event_type,
                "target_angle_deg": target_angle,
                "step": int(timestamp.timestamp()),
                "seed": None,
                "scenario": "csv_input",
                "noise_model": "csv_input",
                "severity": 1.0,
            })
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid CSV row {index + 2}: {exc}") from exc
    if not output:
        raise ValueError("CSV contains no telemetry rows")
    return sorted(output, key=lambda row: (row["timestamp"], row["node_id"]))


def _require_one_of(columns: set[str], *names: str) -> None:
    if not columns.intersection(names):
        raise ValueError(f"CSV is missing required column: {' or '.join(names)}")


def _number(row: dict[str, str], *names: str) -> float:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return float(value)
    raise ValueError(f"missing value for {' or '.join(names)}")


def _parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.strip())
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must include a timezone offset")
    return timestamp


def _load_event_log(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = set(reader.fieldnames or ())
        missing = sorted(EVENT_LOG_COLUMNS - columns)
        if missing:
            raise ValueError(f"Event log is missing required columns: {', '.join(missing)}")
        events: list[dict[str, Any]] = []
        for index, row in enumerate(reader):
            try:
                start = _parse_timestamp(row["start_timestamp"])
                duration = float(row["duration_s"])
                if duration <= 0:
                    raise ValueError("duration_s must be greater than zero")
                event_type = row["event_type"].strip().lower()
                if event_type not in {"tilt", "tap", "phone_vibration"}:
                    raise ValueError(f"unsupported event_type {event_type!r}")
                target = row.get("target_angle_deg", "").strip()
                events.append({
                    "event_id": row["event_id"].strip(),
                    "event_type": event_type,
                    "start_timestamp": start,
                    "end_timestamp": start + timedelta(seconds=duration),
                    "target_angle_deg": float(target) if target else None,
                })
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid event-log row {index + 2}: {exc}") from exc
    return events


def _event_at(timestamp: datetime, events: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [
        event for event in events
        if event["start_timestamp"] <= timestamp < event["end_timestamp"]
    ]
    if len(matches) > 1:
        raise ValueError(f"overlapping event-log intervals at {timestamp.isoformat()}")
    return matches[0] if matches else None
