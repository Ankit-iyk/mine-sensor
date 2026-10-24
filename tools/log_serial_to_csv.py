"""Capture ESP32 telemetry JSON lines into a labelled SUBSENSE CSV."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable, TextIO


CSV_COLUMNS = (
    "timestamp", "node_id", "tilt_x", "tilt_y", "accel_x",
    "accel_y", "accel_z", "vibration", "label",
)
LABEL_COLUMNS = {
    "event_id", "node_id", "start_time", "end_time",
    "event_type", "true_angle_deg",
}


def normalize_serial_record(record: dict[str, Any], line_number: int) -> dict[str, Any]:
    """Map a telemetry JSON object to the CSV's canonical fields."""
    try:
        timestamp = _parse_timestamp(record["timestamp"])
        node_id = str(record["node_id"]).strip()
        if not node_id:
            raise ValueError("node_id is empty")
        if len(node_id) > 20 or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in node_id):
            raise ValueError("node_id must match the telemetry schema pattern ^[A-Z0-9_-]{1,20}$")
        zone_id = str(record["zone_id"]).strip()
        if len(zone_id) > 20 or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in zone_id):
            raise ValueError("zone_id must match the telemetry schema pattern ^[A-Z0-9_-]{1,20}$")
        accel_x = _finite_float(record.get("accel_x", record.get("ax")), "accel_x")
        accel_y = _finite_float(record.get("accel_y", record.get("ay")), "accel_y")
        accel_z = _finite_float(record.get("accel_z", record.get("az")), "accel_z")
        tilt_x = _finite_float(record["tilt_x"], "tilt_x")
        tilt_y = _finite_float(record["tilt_y"], "tilt_y")
        if any(not -20.0 <= value <= 20.0 for value in (accel_x, accel_y, accel_z)):
            raise ValueError("acceleration axes must be between -20 and 20 m/s^2")
        if any(not -90.0 <= value <= 90.0 for value in (tilt_x, tilt_y)):
            raise ValueError("tilt axes must be between -90 and 90 degrees")
        vibration_value = float(record["vibration"])
        if not vibration_value.is_integer():
            raise ValueError("vibration must be an integer ADC count")
        normalized = {
            "timestamp": timestamp.isoformat(),
            "node_id": node_id,
            "tilt_x": tilt_x,
            "tilt_y": tilt_y,
            "accel_x": accel_x,
            "accel_y": accel_y,
            "accel_z": accel_z,
            "vibration": int(vibration_value),
        }
        if not 0 <= normalized["vibration"] <= 1023:
            raise ValueError("vibration must be between 0 and 1023")
        return normalized
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid telemetry JSON line {line_number}: {exc}") from exc


def read_json_lines(stream: Iterable[str], start_line: int = 1) -> list[dict[str, Any]]:
    """Parse non-empty JSON lines; malformed input fails with its line number."""
    records = []
    for line_number, line in enumerate(stream, start=start_line):
        if not line.strip():
            continue
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
        if not isinstance(decoded, dict):
            raise ValueError(f"Invalid JSON on line {line_number}: expected an object")
        records.append(normalize_serial_record(decoded, line_number))
    return records


def load_label_intervals(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = sorted(LABEL_COLUMNS - set(reader.fieldnames or ()))
        if missing:
            raise ValueError(f"Label CSV is missing required columns: {', '.join(missing)}")
        intervals = []
        for line_number, item in enumerate(reader, start=2):
            try:
                node_id = (item.get("node_id") or "").strip()
                event_id = (item.get("event_id") or "").strip()
                event_type = (item.get("event_type") or "").strip()
                start = _parse_timestamp(item.get("start_time", ""))
                end = _parse_timestamp(item.get("end_time", ""))
                angle = (item.get("true_angle_deg") or "").strip()
                if not node_id or not event_id or not event_type:
                    raise ValueError("event_id, node_id and event_type must be non-empty")
                if end < start:
                    raise ValueError("end_time must not precede start_time")
                if angle:
                    _finite_float(angle, "true_angle_deg")
                intervals.append({
                    "node_id": node_id,
                    "start": start,
                    "end": end,
                })
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid label CSV row {line_number}: {exc}") from exc
    return intervals


def attach_labels(
    records: list[dict[str, Any]], intervals: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Mark in-interval rows positive; no label file leaves labels blank."""
    output = []
    for source in records:
        row = dict(source)
        if intervals is None:
            row["label"] = ""
        else:
            timestamp = _parse_timestamp(row["timestamp"])
            row["label"] = "1" if any(
                interval["node_id"] == row["node_id"]
                and interval["start"] <= timestamp <= interval["end"]
                for interval in intervals
            ) else "0"
        output.append(row)
    return output


def write_csv(path: str | Path, records: list[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def _parse_timestamp(value: Any) -> datetime:
    timestamp = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        from datetime import timezone
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp


def _finite_float(value: Any, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _serial_lines(port: str, baudrate: int) -> Iterable[str]:
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError(
            "Serial-port capture requires pyserial; install it with `python -m pip install pyserial`."
        ) from exc
    connection = serial.Serial(port, baudrate=baudrate, timeout=1)
    try:
        while True:
            line = connection.readline()
            if line:
                yield line.decode("utf-8")
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="JSON-lines file, or '-' for stdin.")
    source.add_argument("--port", help="Serial device, such as COM4 (requires pyserial).")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label-file", type=Path)
    parser.add_argument("--max-lines", type=int, help="Stop after this many input lines.")
    args = parser.parse_args()
    if args.max_lines is not None and args.max_lines < 1:
        parser.error("--max-lines must be positive")

    try:
        if args.input is not None:
            stream: Iterable[str] | TextIO = (
                sys.stdin if str(args.input) == "-" else args.input.open("r", encoding="utf-8")
            )
        else:
            stream = _serial_lines(args.port, args.baudrate)
        records: list[dict[str, Any]] = []
        try:
            for line_number, line in enumerate(stream, start=1):
                if args.max_lines is not None and line_number > args.max_lines:
                    break
                records.extend(read_json_lines([line], start_line=line_number))
        except KeyboardInterrupt:
            pass
        finally:
            if args.input is not None and str(args.input) != "-" and hasattr(stream, "close"):
                stream.close()
            elif args.port is not None:
                close_stream = getattr(stream, "close", None)
                if close_stream is not None:
                    close_stream()
        labels = load_label_intervals(args.label_file) if args.label_file else None
        write_csv(args.output, attach_labels(records, labels))
    except (OSError, RuntimeError, UnicodeDecodeError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Wrote {len(records)} readings to {args.output}")


if __name__ == "__main__":
    main()
