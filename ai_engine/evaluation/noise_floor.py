"""Noise, drift, Allan-deviation and empirical false-alarm analysis."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


AXIS_COLUMNS = ("tilt_x", "tilt_y", "accel_x", "accel_y", "accel_z")
ALLAN_TAU_SECONDS = (1, 2, 4, 8, 16, 32)


def analyze_stationary_csv(
    csv_path: str | Path,
    output_dir: str | Path,
    target_false_alarms_per_hour: float = 1.0,
    node_id: str | None = None,
) -> dict[str, Any]:
    """Analyze one node's stationary log and write summary CSVs and a PNG."""
    if not math.isfinite(target_false_alarms_per_hour) or target_false_alarms_per_hour < 0:
        raise ValueError("target_false_alarms_per_hour must be finite and non-negative")
    timestamps, values, selected_node = _read_stationary_csv(csv_path, node_id)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    elapsed_hours = (timestamps[-1] - timestamps[0]).total_seconds() / 3600.0
    if elapsed_hours <= 0:
        raise ValueError("stationary CSV timestamps must span a positive duration")
    hours = np.asarray([(stamp - timestamps[0]).total_seconds() / 3600.0 for stamp in timestamps])
    summary_rows = []
    for index, axis in enumerate(AXIS_COLUMNS):
        series = values[:, index]
        slope = float(np.polyfit(hours, series, 1)[0]) if len(series) >= 2 else math.nan
        summary_rows.append({
            "node_id": selected_node,
            "axis": axis,
            "noise_std": float(np.std(series, ddof=1)) if len(series) > 1 else 0.0,
            "drift_per_hour": slope,
            "net_change": float(series[-1] - series[0]),
            "samples": len(series),
            "duration_hours": elapsed_hours,
        })

    tilt_center = np.median(values[:, :2], axis=0)
    tilt_noise = np.sqrt(np.sum((values[:, :2] - tilt_center) ** 2, axis=1))
    thresholds = np.linspace(0.0, max(float(np.max(tilt_noise)) * 1.01, 1e-9), 101)
    false_alarm_rows = []
    for threshold in thresholds:
        alarm = tilt_noise >= threshold
        rises = int(np.count_nonzero(alarm & ~np.r_[False, alarm[:-1]]))
        false_alarm_rows.append({
            "threshold_deg": float(threshold),
            "false_alarms_per_hour": rises / elapsed_hours,
        })
    acceptable = [
        item for item in false_alarm_rows
        if item["false_alarms_per_hour"] <= target_false_alarms_per_hour
    ]
    detectable_tilt = min(item["threshold_deg"] for item in acceptable) if acceptable else math.nan

    timestamps_seconds = np.asarray([(stamp - timestamps[0]).total_seconds() for stamp in timestamps])
    sample_period = float(np.median(np.diff(timestamps_seconds)))
    allan_rows = []
    for axis_index, axis in enumerate(AXIS_COLUMNS):
        for tau_requested in ALLAN_TAU_SECONDS:
            cluster = max(1, int(round(tau_requested / sample_period)))
            deviation = _allan_deviation(values[:, axis_index], cluster)
            if math.isfinite(deviation):
                allan_rows.append({
                    "node_id": selected_node,
                    "axis": axis,
                    "tau_seconds": cluster * sample_period,
                    "allan_deviation": deviation,
                })

    _write_rows(output / "noise_floor_summary.csv", summary_rows)
    _write_rows(output / "allan_deviation.csv", allan_rows)
    _write_rows(output / "false_alarms_vs_threshold.csv", false_alarm_rows)
    _plot_false_alarms(output / "false_alarms_vs_threshold.png", false_alarm_rows, target_false_alarms_per_hour)
    return {
        "node_id": selected_node,
        "axis_summary": summary_rows,
        "allan_deviation": allan_rows,
        "false_alarm_curve": false_alarm_rows,
        "target_false_alarms_per_hour": target_false_alarms_per_hour,
        "minimum_detectable_tilt_deg": detectable_tilt,
    }


def _read_stationary_csv(
    path: str | Path, node_id: str | None
) -> tuple[list[datetime], np.ndarray, str]:
    with Path(path).open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"timestamp", "node_id", *AXIS_COLUMNS}
        missing = sorted(required - set(reader.fieldnames or ()))
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")
        raw_rows = [
            row for row in reader
            if node_id is None or (row.get("node_id") or "").strip() == node_id
        ]
    if not raw_rows:
        raise ValueError("CSV contains no rows for the selected node")
    observed_nodes = {(row.get("node_id") or "").strip() for row in raw_rows}
    if len(observed_nodes) != 1:
        raise ValueError("CSV contains multiple nodes; pass --node-id to select one")
    selected_node = next(iter(observed_nodes))
    parsed = []
    for line_number, row in enumerate(raw_rows, start=2):
        try:
            stamp = datetime.fromisoformat((row.get("timestamp") or "").strip().replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("timestamp must include a timezone")
            values = [float(row[column]) for column in AXIS_COLUMNS]
            if not all(math.isfinite(value) for value in values):
                raise ValueError("axis values must be finite")
            parsed.append((stamp, values))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid CSV row {line_number}: {exc}") from exc
    parsed.sort(key=lambda item: item[0])
    if len(parsed) < 3:
        raise ValueError("at least three stationary readings are required")
    timestamps = [item[0] for item in parsed]
    if any(b <= a for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError("timestamps must be unique and strictly increasing")
    return timestamps, np.asarray([item[1] for item in parsed], dtype=float), selected_node


def _allan_deviation(series: np.ndarray, cluster_size: int) -> float:
    block_count = len(series) // cluster_size
    if block_count < 2:
        return math.nan
    means = series[:block_count * cluster_size].reshape(block_count, cluster_size).mean(axis=1)
    return float(np.sqrt(0.5 * np.mean(np.diff(means) ** 2)))


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _plot_false_alarms(path: Path, rows: list[dict[str, Any]], target: float) -> None:
    thresholds = [row["threshold_deg"] for row in rows]
    rates = [row["false_alarms_per_hour"] for row in rows]
    fig, axis = plt.subplots(figsize=(8, 5))
    axis.plot(thresholds, rates, color="#276b8e")
    axis.axhline(target, color="#bb4938", linestyle="--", label=f"target {target:g}/hour")
    axis.set_xlabel("Tilt-deviation threshold (degrees)")
    axis.set_ylabel("Empirical false alarms per hour")
    axis.set_title("Stationary-run threshold curve")
    axis.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stationary_csv", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/evaluation/real"))
    parser.add_argument("--target-false-alarms-per-hour", type=float, default=1.0)
    parser.add_argument("--node-id")
    args = parser.parse_args()
    report = analyze_stationary_csv(
        args.stationary_csv,
        args.output_dir,
        args.target_false_alarms_per_hour,
        args.node_id,
    )
    print(f"Node: {report['node_id']}")
    print(f"Empirical minimum detectable tilt: {report['minimum_detectable_tilt_deg']:.6g} degrees")
    print(f"Outputs: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
