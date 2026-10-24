"""Point, event, false-alarm and seed-bootstrap-summary metrics."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import math
from typing import Any, Iterable

import numpy as np
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score
from scipy.stats import t


def point_metrics(labels: Iterable[bool], scores: Iterable[float], alerts: Iterable[bool]) -> dict[str, float]:
    """Return point metrics; PR-AUC is average precision on continuous scores."""
    y_true = np.asarray(list(labels), dtype=bool)
    y_score = np.asarray(list(scores), dtype=float)
    y_pred = np.asarray(list(alerts), dtype=bool)
    if not (len(y_true) == len(y_score) == len(y_pred)):
        raise ValueError("labels, scores, and alerts must have equal lengths")
    if y_true.size == 0:
        raise ValueError("metrics require at least one reading")
    pr_auc = float(average_precision_score(y_true, y_score)) if y_true.any() else math.nan
    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)) if y_true.any() else math.nan,
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "pr_auc": pr_auc,
    }


def event_metrics(rows: list[dict[str, Any]], alerts: Iterable[bool]) -> dict[str, float]:
    """Compute event recall and delay from onset to first alert in each event."""
    decisions = list(alerts)
    if len(rows) != len(decisions):
        raise ValueError("rows and alerts must have equal lengths")
    grouped: dict[str, list[tuple[dict[str, Any], bool]]] = defaultdict(list)
    for row, alert in zip(rows, decisions):
        event_id = row.get("event_id")
        if event_id and row.get("is_event"):
            grouped[str(event_id)].append((row, bool(alert)))
    if not grouped:
        return {"event_recall": math.nan, "detection_delay_seconds": math.nan, "event_count": 0.0}
    detected = 0
    delays: list[float] = []
    for event_rows in grouped.values():
        onset = _as_datetime(event_rows[0][0]["event_onset_time"])
        hits = [
            _as_datetime(row["timestamp"])
            for row, alert in event_rows
            if alert and _as_datetime(row["timestamp"]) >= onset
        ]
        if hits:
            detected += 1
            delays.append(max(0.0, (min(hits) - onset).total_seconds()))
    return {
        "event_recall": detected / len(grouped),
        "detection_delay_seconds": float(np.mean(delays)) if delays else math.nan,
        "event_count": float(len(grouped)),
    }


def false_alarms_per_hour(rows: list[dict[str, Any]], alerts: Iterable[bool]) -> float:
    """Count rising edges of non-event alert runs per summed node-hour."""
    decisions = list(alerts)
    if len(rows) != len(decisions):
        raise ValueError("rows and alerts must have equal lengths")
    by_node: dict[str, list[tuple[datetime, bool, bool]]] = defaultdict(list)
    for row, alert in zip(rows, decisions):
        by_node[str(row["node_id"])].append((
            _as_datetime(row["timestamp"]),
            bool(alert),
            bool(row.get("is_event", False)),
        ))
    count = 0
    exposure_hours = 0.0
    for node_rows in by_node.values():
        node_rows.sort(key=lambda item: item[0])
        exposure_hours += max(
            0.0,
            (node_rows[-1][0] - node_rows[0][0]).total_seconds() / 3600.0,
        )
        previous_alert = False
        for _, alert, is_event in node_rows:
            false_alert = alert and not is_event
            if false_alert and not previous_alert:
                count += 1
            previous_alert = alert
    return count / exposure_hours if exposure_hours else 0.0


def confidence_interval(values: Iterable[float]) -> tuple[float, float, float, int]:
    """Mean and two-sided 95% Student-t confidence interval over independent seeds."""
    data = np.asarray([value for value in values if math.isfinite(float(value))], dtype=float)
    n = int(data.size)
    if n == 0:
        return math.nan, math.nan, math.nan, 0
    mean = float(np.mean(data))
    if n == 1:
        return mean, math.nan, math.nan, n
    margin = float(t.ppf(0.975, n - 1) * np.std(data, ddof=1) / math.sqrt(n))
    return mean, mean - margin, mean + margin, n


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
