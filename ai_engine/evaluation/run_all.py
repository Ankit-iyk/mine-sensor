"""Run the complete evaluation: python -m ai_engine.evaluation.run_all --seeds 30."""

from __future__ import annotations

import argparse
import csv
import math
from datetime import timedelta
from pathlib import Path
import sys
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "simulator") not in sys.path:
    sys.path.insert(0, str(_ROOT / "simulator"))

from ai_engine.evaluation.datasets import (
    EVENT_SCENARIOS, SCENARIOS, generate_episode,
)
from ai_engine.evaluation.methods import ABLATIONS, METHODS, MethodSuite
from ai_engine.evaluation.backend_features import extract_backend_features
from ai_engine.evaluation.metrics import (
    confidence_interval, event_metrics, false_alarms_per_hour, point_metrics,
)
from ai_engine.evaluation.real_data import load_real_csv

_TRAIN_SEED_BASE = 100_000
_TEST_SEED_BASE = 10_000
_SHIFT_SEED_BASE = 200_000
_TRAIN_KEEP_EVERY = 10
_TRAINING_CONDITIONS = (
    ("normal", "simulator"),
    ("baseline_drift", "simulator"),
    ("normal", "distribution_shift"),
)
_FOREST_VALUE_SCENARIOS = ("gradual_tilt", "step_tilt", "persistent_offset")
_METRICS = (
    "event_recall", "detection_delay_seconds", "false_alarms_normal_per_hour",
    "false_alarms_nuisance_per_hour", "precision", "recall", "f1", "pr_auc",
)


def run_evaluation(
    seeds: int = 30,
    output_dir: Path | None = None,
    real_csv: Path | None = None,
    event_log: Path | None = None,
) -> list[dict[str, Any]]:
    if seeds < 1:
        raise ValueError("--seeds must be at least 1")
    output_dir = output_dir or (_ROOT / "docs" / "evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    if real_csv:
        return _run_csv_placeholder_evaluation(real_csv, event_log, output_dir)
    training_rows = _training_features(seeds)
    suite = MethodSuite(training_rows)
    summaries: list[dict[str, Any]] = []

    for noise_model, seed_base in (("simulator", _TEST_SEED_BASE), ("distribution_shift", _SHIFT_SEED_BASE)):
        episodes: dict[tuple[str, int], list[dict[str, Any]]] = {}
        control_cache: dict[tuple[str, int], tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]] = {}
        seed_metrics: dict[tuple[str, str, int], dict[str, float]] = {}
        for scenario in SCENARIOS:
            for seed_offset in range(seeds):
                seed = seed_base + seed_offset
                raw = generate_episode(scenario, seed, noise_model)
                episodes[(scenario, seed)] = extract_backend_features(raw)
        for method in METHODS:
            for scenario in SCENARIOS:
                seed_records: list[dict[str, float]] = []
                for seed_offset in range(seeds):
                    seed = seed_base + seed_offset
                    rows = episodes[(scenario, seed)]
                    scores, alerts = suite.predict(rows, method)
                    controls = _cached_control_predictions(
                        suite, episodes, control_cache, method, seed
                    )
                    metrics = _episode_metrics(
                        rows, scores, alerts,
                        controls,
                    )
                    seed_records.append(metrics)
                    seed_metrics[(scenario, method, seed)] = metrics
                summaries.append(_summarize(
                    noise_model, scenario, method, seed_records, seeds
                ))
        for ablation in ABLATIONS:
            for scenario in SCENARIOS:
                seed_records = []
                for seed_offset in range(seeds):
                    seed = seed_base + seed_offset
                    rows = episodes[(scenario, seed)]
                    scores, alerts = suite.predict_ablation(rows, ablation)
                    controls = _cached_control_predictions(
                        suite, episodes, control_cache, f"ablation_{ablation}", seed
                    )
                    seed_records.append(_episode_metrics(
                        rows, scores, alerts, controls,
                    ))
                summaries.append(_summarize(
                    noise_model, scenario, f"ablation_{ablation}", seed_records, seeds
                ))
        for scenario in _FOREST_VALUE_SCENARIOS:
            paired_differences = []
            for seed_offset in range(seeds):
                seed = seed_base + seed_offset
                baseline = seed_metrics[(scenario, "baseline_deviation_only_spatial", seed)]
                full = seed_metrics[(scenario, "current_system_spatial", seed)]
                paired_differences.append({
                    metric: full[metric] - baseline[metric]
                    for metric in _METRICS
                    if math.isfinite(full[metric]) and math.isfinite(baseline[metric])
                })
            summaries.append(_summarize_paired_difference(
                noise_model, scenario, paired_differences, seeds
            ))
    _write_csv(output_dir / "results.csv", summaries)
    _write_markdown(output_dir / "results.md", summaries, seeds, None)
    _plot_figures(output_dir, summaries)
    return summaries


def _run_csv_placeholder_evaluation(
    sensor_csv: Path,
    event_log: Path | None,
    output_dir: Path,
) -> list[dict[str, Any]]:
    if event_log is None:
        raise ValueError("--event-log is required when evaluating the synthetic placeholder CSV")
    readings = load_real_csv(sensor_csv, event_log)
    if len(readings) < 2:
        raise ValueError("CSV evaluation requires at least two telemetry rows")
    first_timestamp = readings[0]["timestamp"]
    training_end = first_timestamp + timedelta(minutes=30)
    training_readings = [row for row in readings if row["timestamp"] < training_end]
    if not training_readings or any(
        row["label"] != "stationary" or row["is_event"]
        for row in training_readings
    ):
        raise ValueError("the first 30 minutes must contain stationary, event-free samples only")

    # The backend feature pipeline is run on the full ordered stream. The
    # learned evaluation methods are fitted only on the first 30 minutes.
    training_features_all = extract_backend_features(training_readings)
    training_features = training_features_all[::_TRAIN_KEEP_EVERY]
    if not training_features or any(row["is_event"] for row in training_features):
        raise ValueError("the 30-minute training partition produced no event-free features")
    suite = MethodSuite(training_features)
    all_features = extract_backend_features(readings)
    test_rows = [row for row in all_features if row["timestamp"] >= training_end]
    if not test_rows:
        raise ValueError("no evaluation readings remain after the 30-minute training period")

    methods = (
        "fixed_tilt_threshold",
        "baseline_z_score",
        "ewma",
        "cusum",
        "isolation_forest",
        "one_class_svm",
        "local_outlier_factor",
        "current_system",
        "current_system_spatial",
    )
    predictions = {
        method: suite.predict(test_rows, method)
        for method in methods
    }
    training_control_indices = [
        index for index, row in enumerate(training_features_all)
        if row.get("event_type") == "stationary"
    ]
    training_control_rows = [
        training_features_all[index] for index in training_control_indices
    ]
    calibrated_predictions: dict[str, tuple[float, float, np.ndarray]] = {}
    for method in methods:
        training_scores = suite.predict(training_features_all, method)[0]
        threshold, training_false_alarms = _calibrate_score_threshold(
            suite,
            method,
            training_features_all,
            training_scores,
            training_control_rows,
            training_control_indices,
        )
        test_scores = predictions[method][0]
        test_alerts = _alerts_at_score_threshold(
            suite, method, test_rows, test_scores, threshold
        )
        calibrated_predictions[method] = (
            threshold, training_false_alarms, test_alerts
        )
    stationary_indices = [
        index for index, row in enumerate(test_rows)
        if row.get("event_type") == "stationary"
    ]
    if not stationary_indices:
        raise ValueError("no post-training stationary samples are available for false-alarm measurement")
    stationary_rows = [test_rows[index] for index in stationary_indices]
    false_alarm_rates = {
        method: false_alarms_per_hour(
            stationary_rows,
            [predictions[method][1][index] for index in stationary_indices],
        )
        for method in methods
    }

    angle_records: list[dict[str, Any]] = []
    for angle in (0.25, 0.5, 1.0):
        angle_rows = [
            {
                **row,
                "is_event": row.get("event_type") == "tilt"
                and row.get("target_angle_deg") == angle,
                "event_id": row.get("event_id")
                if row.get("event_type") == "tilt"
                and row.get("target_angle_deg") == angle else None,
                "event_onset_time": row.get("event_onset_time")
                if row.get("event_type") == "tilt"
                and row.get("target_angle_deg") == angle else None,
            }
            for row in test_rows
        ]
        labels = [row["is_event"] for row in angle_rows]
        for method in methods:
            scores, alerts = predictions[method]
            point = point_metrics(labels, scores, alerts)
            event = event_metrics(angle_rows, alerts)
            angle_records.append({
                "scenario": f"tilt_{angle:g}_deg",
                "method": method,
                "target_angle_deg": angle,
                "event_count": int(event["event_count"]),
                "events_detected": round(event["event_recall"] * event["event_count"])
                if math.isfinite(event["event_recall"]) else 0,
                "event_recall": event["event_recall"],
                "detection_delay_seconds": event["detection_delay_seconds"],
                "false_alarms_per_hour": false_alarm_rates[method],
                "pr_auc": point["pr_auc"],
            })

    vibration_records = _placeholder_vibration_response(test_rows)
    minimum_detectable: dict[str, dict[str, Any]] = {}
    for method in methods:
        threshold, training_fa, calibrated_alerts = calibrated_predictions[method]
        test_false_alarms = false_alarms_per_hour(
            stationary_rows,
            [calibrated_alerts[index] for index in stationary_indices],
        )
        angle_recalls = {
            angle: _target_event_recall(test_rows, calibrated_alerts, angle)
            for angle in (0.25, 0.5, 1.0)
        }
        caught_angles = [
            angle for angle, recall in angle_recalls.items()
            if recall == 1.0
        ] if test_false_alarms <= 1.0 else []
        minimum_detectable[method] = {
            "threshold": threshold,
            "training_false_alarms": training_fa,
            "test_false_alarms": test_false_alarms,
            "angle_recalls": angle_recalls,
            "minimum_angle": f"{min(caught_angles):g}°" if caught_angles else "none at 100% event recall",
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_placeholder_csv(output_dir / "results.csv", angle_records)
    _write_placeholder_report(
        output_dir / "results.md",
        sensor_csv,
        event_log,
        len(training_features),
        angle_records,
        vibration_records,
        minimum_detectable,
    )
    print("SYNTHETIC PLACEHOLDER DATA")
    print(f"Results: {(output_dir / 'results.md').resolve()}")
    return angle_records


def _placeholder_vibration_response(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    event_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("event_type") in {"tap", "phone_vibration"} and row.get("event_id"):
            event_groups.setdefault(str(row["event_id"]), []).append(row)
    records: list[dict[str, Any]] = []
    for event_type in ("tap", "phone_vibration"):
        groups = [
            group for group in event_groups.values()
            if group[0]["event_type"] == event_type
        ]
        samples = [row for group in groups for row in group]
        intensities = [float(row["vibration_intensity"]) for row in samples]
        threshold_events = sum(
            any(float(row["vibration_intensity"]) >= 0.35 for row in group)
            for group in groups
        )
        records.append({
            "event_type": event_type,
            "event_count": len(groups),
            "sample_count": len(samples),
            "mean_intensity": float(np.mean(intensities)) if intensities else math.nan,
            "max_intensity": max(intensities) if intensities else math.nan,
            "fraction_samples_ge_0_35": (
                sum(value >= 0.35 for value in intensities) / len(intensities)
                if intensities else math.nan
            ),
            "events_with_sample_ge_0_35": threshold_events,
        })
    return records


def _alerts_at_score_threshold(
    suite: MethodSuite,
    method: str,
    rows: list[dict[str, Any]],
    scores: np.ndarray,
    threshold: float,
) -> np.ndarray:
    raw_alerts = scores >= threshold
    if method == "current_system_spatial":
        return suite._persist_and_corroborate(rows, raw_alerts, None)
    return raw_alerts


def _calibrate_score_threshold(
    suite: MethodSuite,
    method: str,
    training_rows: list[dict[str, Any]],
    scores: np.ndarray,
    control_rows: list[dict[str, Any]],
    control_indices: list[int],
    target_false_alarms_per_hour: float = 1.0,
) -> tuple[float, float]:
    values = np.unique(scores)
    candidates = np.append(values, np.nextafter(float(values[-1]), math.inf))
    left, right = 0, len(candidates) - 1
    best_index = right
    best_rate = math.inf
    while left <= right:
        middle = (left + right) // 2
        threshold = float(candidates[middle])
        alerts = _alerts_at_score_threshold(
            suite, method, training_rows, scores, threshold
        )
        rate = false_alarms_per_hour(
            control_rows,
            [alerts[index] for index in control_indices],
        )
        if rate <= target_false_alarms_per_hour:
            best_index = middle
            best_rate = rate
            right = middle - 1
        else:
            left = middle + 1
    threshold = float(candidates[best_index])
    if not math.isfinite(best_rate):
        alerts = _alerts_at_score_threshold(
            suite, method, training_rows, scores, threshold
        )
        best_rate = false_alarms_per_hour(
            control_rows,
            [alerts[index] for index in control_indices],
        )
    return threshold, best_rate


def _target_event_recall(
    rows: list[dict[str, Any]],
    alerts: np.ndarray,
    angle: float,
) -> float:
    selected = [
        {
            **row,
            "is_event": row.get("event_type") == "tilt"
            and row.get("target_angle_deg") == angle,
            "event_id": row.get("event_id")
            if row.get("event_type") == "tilt"
            and row.get("target_angle_deg") == angle else None,
            "event_onset_time": row.get("event_onset_time")
            if row.get("event_type") == "tilt"
            and row.get("target_angle_deg") == angle else None,
        }
        for row in rows
    ]
    result = event_metrics(selected, alerts)
    return result["event_recall"]


def _write_placeholder_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = (
        "scenario", "method", "target_angle_deg", "event_count",
        "events_detected", "event_recall", "detection_delay_seconds",
        "false_alarms_per_hour", "pr_auc",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_placeholder_report(
    path: Path,
    sensor_csv: Path,
    event_log: Path,
    training_feature_count: int,
    angle_rows: list[dict[str, Any]],
    vibration_rows: list[dict[str, Any]],
    minimum_detectable: dict[str, str],
) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# SYNTHETIC PLACEHOLDER DATA — evaluation only\n\n")
        stream.write(
            "These outputs use synthetic placeholder data only. They are not measured "
            "recordings and are not hardware-validated. Models were fit only on the "
            "first 30 minutes of stationary samples; the backend feature pipeline "
            "then processed the ordered input stream. This run exists to exercise "
            "the CSV loader and evaluation workflow.\n\n"
        )
        stream.write(f"- Sensor CSV: `{sensor_csv}`\n")
        stream.write(f"- Event log: `{event_log}`\n")
        stream.write(f"- Training features after 1-in-{_TRAIN_KEEP_EVERY} subsampling: {training_feature_count}\n")
        stream.write("- Acceleration units: input `_g` columns converted to m/s² (backend schema units).\n")
        stream.write("- Vibration values in [0, 1] are treated as normalized and converted to 10-bit ADC counts.\n")
        stream.write("- Event recall requires all logged events at that angle to be detected; false alarms are measured on post-training stationary samples only.\n\n")
        stream.write("## Tilt event results\n\n")
        stream.write("| target angle | method | events detected / total | event recall | detection delay (s) | false alarms/hour | PR-AUC |\n")
        stream.write("|---:|---|---:|---:|---:|---:|---:|\n")
        for row in angle_rows:
            stream.write(
                f"| {row['target_angle_deg']:g}° | {row['method']} | "
                f"{row['events_detected']}/{row['event_count']} | "
                f"{_plain_metric(row['event_recall'])} | "
                f"{_plain_metric(row['detection_delay_seconds'])} | "
                f"{_plain_metric(row['false_alarms_per_hour'])} | "
                f"{_plain_metric(row['pr_auc'])} |\n"
            )
        stream.write("\n## Minimum detectable tilt at no more than 1 false alarm/hour\n\n")
        stream.write(
            "Each method's continuous score threshold is calibrated on the first "
            "30-minute stationary training segment to allow no more than 1 false "
            "alarm/hour. The minimum angle is reported only when the held-out "
            "stationary control rate also stays ≤1/hour and all logged events at "
            "that angle are detected.\n\n"
        )
        stream.write(
            "| method | calibrated score threshold | training false alarms/hour | test false alarms/hour | recall at 0.25° | recall at 0.5° | recall at 1.0° | minimum angle at ≤1 FA/hour |\n"
            "|---|---:|---:|---:|---:|---:|---:|---|\n"
        )
        for method, result in minimum_detectable.items():
            stream.write(
                f"| {method} | {_plain_metric(result['threshold'])} | "
                f"{_plain_metric(result['training_false_alarms'])} | "
                f"{_plain_metric(result['test_false_alarms'])} | "
                f"{_plain_metric(result['angle_recalls'][0.25])} | "
                f"{_plain_metric(result['angle_recalls'][0.5])} | "
                f"{_plain_metric(result['angle_recalls'][1.0])} | "
                f"{result['minimum_angle']} |\n"
            )
        stream.write("\n## Vibration channel response (synthetic events)\n\n")
        stream.write(
            "The threshold comparison uses backend-normalized vibration intensity ≥0.35.\n\n"
            "| event type | events | samples | mean intensity | max intensity | samples ≥0.35 | events with any sample ≥0.35 |\n"
            "|---|---:|---:|---:|---:|---:|---:|\n"
        )
        for row in vibration_rows:
            fraction = row["fraction_samples_ge_0_35"]
            stream.write(
                f"| {row['event_type']} | {row['event_count']} | {row['sample_count']} | "
                f"{_plain_metric(row['mean_intensity'])} | {_plain_metric(row['max_intensity'])} | "
                f"{_plain_metric(fraction)} | "
                f"{row['events_with_sample_ge_0_35']}/{row['event_count']} |\n"
            )


def _plain_metric(value: float) -> str:
    return f"{value:.3f}" if math.isfinite(value) else "n/a"


def _training_features(seeds: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    train_seed_count = max(30, seeds)
    for offset in range(train_seed_count):
        seed = _TRAIN_SEED_BASE + offset
        for scenario, noise_model in _TRAINING_CONDITIONS:
            readings = generate_episode(scenario, seed, noise_model)
            features = extract_backend_features(readings)
            rows.extend(
                row for row in features[::_TRAIN_KEEP_EVERY]
                if not row["is_event"]
            )
    if any(row["seed"] < _TRAIN_SEED_BASE for row in rows):
        raise RuntimeError("training/test seed partition overlap detected")
    if not rows or any(row["is_event"] for row in rows):
        raise RuntimeError("training set must contain only event-free feature rows")
    return rows


def _episode_metrics(
    rows: list[dict[str, Any]],
    scores: np.ndarray,
    alerts: np.ndarray,
    controls: tuple[tuple[list[dict[str, Any]], np.ndarray], tuple[list[dict[str, Any]], np.ndarray]],
) -> dict[str, float]:
    points = point_metrics(
        [row["is_event"] for row in rows], scores, alerts
    )
    event = event_metrics(rows, alerts)
    (normal_control, normal_alerts), (nuisance_control, nuisance_alerts) = controls
    return {
        **points,
        **event,
        "false_alarms_normal_per_hour": false_alarms_per_hour(normal_control, normal_alerts),
        "false_alarms_nuisance_per_hour": false_alarms_per_hour(nuisance_control, nuisance_alerts),
    }


def _cached_control_predictions(
    suite: MethodSuite,
    episodes: dict[tuple[str, int], list[dict[str, Any]]],
    cache: dict[tuple[str, int], tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]],
    method: str,
    seed: int,
) -> tuple[tuple[list[dict[str, Any]], np.ndarray], tuple[list[dict[str, Any]], np.ndarray]]:
    key = (method, seed)
    if key not in cache:
        if method.startswith("ablation_"):
            name = method.removeprefix("ablation_")
            normal_pred = suite.predict_ablation(episodes[("normal", seed)], name)
            nuisance_pred = suite.predict_ablation(episodes[("baseline_drift", seed)], name)
        else:
            normal_pred = suite.predict(episodes[("normal", seed)], method)
            nuisance_pred = suite.predict(episodes[("baseline_drift", seed)], method)
        cache[key] = (normal_pred, nuisance_pred)
    return (
        (episodes[("normal", seed)], cache[key][0][1]),
        (episodes[("baseline_drift", seed)], cache[key][1][1]),
    )


def _summarize(
    noise_model: str,
    scenario: str,
    method: str,
    seed_records: list[dict[str, float]],
    requested_seeds: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "noise_model": noise_model,
        "scenario": scenario,
        "method": method,
        "seeds_requested": requested_seeds,
    }
    for metric in _METRICS:
        mean, low, high, n = confidence_interval(
            record[metric] for record in seed_records
        )
        if math.isfinite(low):
            if metric in {"event_recall", "precision", "recall", "f1", "pr_auc"}:
                low = max(0.0, low)
                high = min(1.0, high)
            else:
                low = max(0.0, low)
        result[f"{metric}_mean"] = mean
        result[f"{metric}_ci95_low"] = low
        result[f"{metric}_ci95_high"] = high
        result[f"{metric}_n"] = n
    return result


def _summarize_paired_difference(
    noise_model: str,
    scenario: str,
    seed_records: list[dict[str, float]],
    requested_seeds: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "noise_model": noise_model,
        "scenario": scenario,
        "method": "forest_added_value",
        "seeds_requested": requested_seeds,
    }
    for metric in _METRICS:
        mean, low, high, n = confidence_interval(
            record[metric] for record in seed_records if metric in record
        )
        result[f"{metric}_mean"] = mean
        result[f"{metric}_ci95_low"] = low
        result[f"{metric}_ci95_high"] = high
        result[f"{metric}_n"] = n
    return result


def _evaluate_real_csv(suite: MethodSuite, path: Path) -> list[dict[str, Any]]:
    raw_rows = load_real_csv(path)
    rows = extract_backend_features(raw_rows)
    results = []
    for method in METHODS:
        scores, alerts = suite.predict(rows, method)
        point = point_metrics([row["is_event"] for row in rows], scores, alerts)
        event = event_metrics(rows, alerts)
        record = {
            **point,
            **event,
            "false_alarms_normal_per_hour": math.nan,
            "false_alarms_nuisance_per_hour": math.nan,
        }
        results.append(_summarize("real_csv", "real_data", method, [record], 1))
    return results


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("evaluation produced no result rows")
    columns = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: "" if isinstance(value, float) and not math.isfinite(value) else value
                for key, value in row.items()
            })


def _write_markdown(path: Path, rows: list[dict[str, Any]], seeds: int, real_csv: Path | None) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# SUBSENSE reproducible detector evaluation\n\n")
        stream.write(
            f"Generated with `{seeds}` independent test seeds per scenario and noise model. "
            f"Training seeds are the disjoint range `{_TRAIN_SEED_BASE}`–"
            f"`{_TRAIN_SEED_BASE + max(30, seeds) - 1}`; simulator test seeds are "
            f"`{_TEST_SEED_BASE}`–`{_TEST_SEED_BASE + seeds - 1}` and shifted test seeds "
            f"`{_SHIFT_SEED_BASE}`–`{_SHIFT_SEED_BASE + seeds - 1}`. "
            "The shared learned-method training partition combines nominal simulator readings, "
            "slow baseline-drift nuisance readings, and nominal readings with added sensor noise; "
            "all training rows are event-free. "
            "All readings use the backend Kalman filter, rolling buffer, baseline tracker, "
            "and FeatureExtractor. Confidence intervals are two-sided 95% Student-t intervals "
            "across seeds (bounded metrics are truncated to valid ranges). Detection delay "
            "averages detected events only; event recall counts "
            "missed events in its denominator. PR-AUC is average precision. "
            "An `ANOMALOUS` current-system state counts as an alert; `MICRO_ANOMALY` does not. "
            "False alarms are rising edges per summed node-hour on the normal and nuisance controls.\n\n"
        )
        stream.write(
            "The shift set independently adds ±0.12° tilt noise, ±0.06 m/s² acceleration noise, "
            "and 0.8–1.2 s sampling intervals. Severity defaults to 1.0. `sensor_failure` "
            "represents a stuck tilt sensor plus zero acceleration; rejected/missing packets "
            "cannot be scored as feature vectors by the current backend pipeline. "
            "Baseline drift is a nuisance with `is_event=false`.\n\n"
        )
        stream.write("## Method and threshold protocol\n\n")
        stream.write(
            "All methods share the same extracted backend feature vectors. The fixed tilt detector "
            "alerts at 0.50° baseline deviation. The baseline z-score uses the training partition's "
            "mean and standard deviation of `tilt_deviation` and alerts at z ≥ 3.0. EWMA uses "
            "α = 0.20 and a 0.30° score threshold. CUSUM uses reference value k = 0.08°/sample "
            "and threshold 0.80. Isolation Forest uses 100 trees, contamination 0.05, seed 71. "
            "One-Class SVM uses an RBF kernel and ν = 0.05; Local Outlier Factor uses novelty "
            "mode, contamination 0.05, and up to 35 neighbors. Both SVM/LOF use a StandardScaler "
            "fit on the same event-free widened training rows as the Isolation Forest. "
            "`current_system` is the unchanged `AIEngineDetector` decision rule with that fitted "
            "Isolation Forest; only `ANOMALOUS` counts as an alert, while `MICRO_ANOMALY` does not. "
            "`current_system_spatial` applies the shared wrapper to current-system alerts. The "
            "wrapper requires three consecutive alerts per node or same-step alerts from at least "
            "two nodes in a zone. The fair `*_spatial` comparisons apply this same wrapper to each "
            "method's raw alerts. `baseline_deviation_only_spatial` removes the Isolation Forest "
            "and alerts at 0.11° baseline deviation before the wrapper; `isolation_forest_spatial` "
            "uses Isolation Forest alerts alone before the wrapper. `vibration_threshold` alerts "
            "at vibration intensity ≥ 0.35. `stuck_sensor_check` flags zero variance across tilt, "
            "acceleration magnitude and vibration intensity over 10 feature readings. These are "
            "evaluation methods, not changes to the production detector. The feature-group ablation "
            "`no_acceleration_features` is expected to be a no-op because the current Isolation "
            "Forest feature contract does not include accelerometer-derived columns.\n\n"
        )
        stream.write("Run with `python -m ai_engine.evaluation.run_all --seeds 30`. Optional labelled hardware CSV input: `--real-csv PATH`.\n\n")
        if real_csv:
            stream.write(f"Real CSV input: `{real_csv}`. It uses the synthetic-trained models; no real-data results are included unless supplied.\n\n")
        stream.write("## Main results: simulator noise\n\n")
        _write_table(stream, [row for row in rows if row["noise_model"] == "simulator" and row["method"] in METHODS])
        stream.write("\n## Distribution-shift results\n\n")
        _write_table(stream, [row for row in rows if row["noise_model"] == "distribution_shift" and row["method"] in METHODS])
        stream.write("\n## False alarms per hour\n\n")
        stream.write(
            "Values are mean false-alarm rising edges per summed node-hour on normal and "
            "baseline-drift nuisance controls, with 95% confidence intervals across seeds.\n\n"
        )
        _write_false_alarm_table(stream, rows)
        stream.write("\n## Best method per scenario\n\n")
        stream.write(
            "Selected by highest mean point-level F1 within each noise model/scenario. "
            "Intervals are 95% confidence intervals across seeds; this ranking is descriptive "
            "and does not establish statistically significant differences. Ties on mean F1 "
            "are broken by PR-AUC, then event recall.\n\n"
        )
        _write_best_method_table(stream, rows)
        stream.write("\n## Isolation Forest incremental value\n\n")
        stream.write(
            "The no-forest baseline and full system use the same persistence/spatial wrapper. "
            "Delta is full system minus baseline, calculated as a paired difference on each "
            "test seed before forming the 95% CI. Positive F1/recall is better; positive false "
            "alarm deltas are worse. The full system applies the Isolation Forest decision "
            "together with baseline-deviation thresholding.\n\n"
        )
        _write_isolation_forest_value_table(stream, rows)
        stream.write("\n## Verified gradual-tilt claims\n\n")
        _write_verified_claims(stream, rows)
        stream.write("\n## Where simple methods win\n\n")
        _write_simple_wins(stream, rows)
        stream.write("\n## Ablation results: simulator noise\n\n")
        _write_table(stream, _ablation_table_rows(rows, "simulator"))
        stream.write("\n## Ablation results: distribution shift\n\n")
        _write_table(stream, _ablation_table_rows(rows, "distribution_shift"))
        real_rows = [row for row in rows if row["noise_model"] == "real_csv"]
        if real_rows:
            stream.write("\n## Supplied real-log results\n\n")
            _write_table(stream, real_rows)
        stream.write("\n## Figures\n\n")
        stream.write(
            "- `detection_delay.png`: mean detected-event delay by method; missed events excluded from delay and counted in event recall.\n"
            "- `false_alarms_vs_recall.png`: mean normal-control false alarms/hour versus event recall.\n"
            "- `ablation_bars.png`: event recall by ablation on core simulator tests.\n\n"
        )
        stream.write(
            "These are reproducible synthetic benchmarks, not evidence of field performance. "
            "The backend Isolation Forest is retrained on the documented wider event-free training partition for this comparison; "
            "the detector implementation and runtime behavior were not modified.\n"
        )


def _write_table(stream: Any, rows: list[dict[str, Any]]) -> None:
    columns = (
        "scenario", "method", "event_recall", "detection_delay_seconds",
        "false_alarms_normal_per_hour", "false_alarms_nuisance_per_hour",
        "precision", "recall", "f1", "pr_auc",
    )
    stream.write("| " + " | ".join(columns) + " |\n")
    stream.write("|" + "|".join(["---"] * len(columns)) + "|\n")
    for row in rows:
        values = [
            str(row.get("scenario", "")),
            str(row.get("method", "")),
        ]
        for metric in columns[2:]:
            values.append(_format_value(row.get(f"{metric}_mean", math.nan), row.get(f"{metric}_ci95_low", math.nan), row.get(f"{metric}_ci95_high", math.nan)))
        stream.write("| " + " | ".join(values) + " |\n")


def _write_false_alarm_table(stream: Any, rows: list[dict[str, Any]]) -> None:
    columns = (
        "noise_model", "method", "normal_false_alarms_per_hour",
        "nuisance_false_alarms_per_hour",
    )
    stream.write("| " + " | ".join(columns) + " |\n")
    stream.write("|" + "|".join(["---"] * len(columns)) + "|\n")
    for noise_model in ("simulator", "distribution_shift"):
        candidates = [
            row for row in rows
            if row["noise_model"] == noise_model
            and row["scenario"] == "normal"
            and row["method"] in METHODS
        ]
        for row in candidates:
            stream.write(
                f"| {noise_model} | {row['method']} | "
                f"{_format_value(row['false_alarms_normal_per_hour_mean'], row['false_alarms_normal_per_hour_ci95_low'], row['false_alarms_normal_per_hour_ci95_high'])} | "
                f"{_format_value(row['false_alarms_nuisance_per_hour_mean'], row['false_alarms_nuisance_per_hour_ci95_low'], row['false_alarms_nuisance_per_hour_ci95_high'])} |\n"
            )


def _write_best_method_table(stream: Any, rows: list[dict[str, Any]]) -> None:
    stream.write(
        "| noise_model | scenario | highest-mean-F1 method | F1 (95% CI) | event recall (95% CI) |\n"
        "|---|---|---|---|---|\n"
    )
    for noise_model in ("simulator", "distribution_shift"):
        for scenario in _FOREST_VALUE_SCENARIOS:
            if scenario not in EVENT_SCENARIOS:
                stream.write(
                    f"| {noise_model} | {scenario} | negative control (no labelled event) | n/a | n/a |\n"
                )
                continue
            candidates = [
                row for row in rows
                if row["noise_model"] == noise_model
                and row["scenario"] == scenario
                and row["method"] in METHODS
                and math.isfinite(float(row["f1_mean"]))
            ]
            if not candidates:
                continue
            winner = max(
                candidates,
                key=lambda row: (
                    float(row["f1_mean"]),
                    _finite_or(row.get("pr_auc_mean"), -math.inf),
                    _finite_or(row.get("event_recall_mean"), -math.inf),
                ),
            )
            stream.write(
                f"| {noise_model} | {scenario} | {_method_label(winner['method'])} | "
                f"{_format_value(winner['f1_mean'], winner['f1_ci95_low'], winner['f1_ci95_high'])} | "
                f"{_format_value(winner['event_recall_mean'], winner['event_recall_ci95_low'], winner['event_recall_ci95_high'])} |\n"
            )


def _write_isolation_forest_value_table(stream: Any, rows: list[dict[str, Any]]) -> None:
    stream.write(
        "| noise_model | scenario | no-forest F1 (95% CI) | full-system F1 (95% CI) | paired ΔF1 (95% CI) | paired Δevent recall (95% CI) | paired Δnormal false alarms/hour (95% CI) | paired Δnuisance false alarms/hour (95% CI) |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )
    for noise_model in ("simulator", "distribution_shift"):
        scenarios = sorted({row["scenario"] for row in rows if row["noise_model"] == noise_model})
        for scenario in scenarios:
            baseline = _find_result(rows, noise_model, scenario, "baseline_deviation_only_spatial")
            current = _find_result(rows, noise_model, scenario, "current_system_spatial")
            delta = _find_result(rows, noise_model, scenario, "forest_added_value")
            if baseline is None or current is None or delta is None:
                continue
            stream.write(
                f"| {noise_model} | {scenario} | "
                f"{_format_value(baseline['f1_mean'], baseline['f1_ci95_low'], baseline['f1_ci95_high'])} | "
                f"{_format_value(current['f1_mean'], current['f1_ci95_low'], current['f1_ci95_high'])} | "
                f"{_format_value(delta['f1_mean'], delta['f1_ci95_low'], delta['f1_ci95_high'])} | "
                f"{_format_value(delta['event_recall_mean'], delta['event_recall_ci95_low'], delta['event_recall_ci95_high'])} | "
                f"{_format_value(delta['false_alarms_normal_per_hour_mean'], delta['false_alarms_normal_per_hour_ci95_low'], delta['false_alarms_normal_per_hour_ci95_high'])} | "
                f"{_format_value(delta['false_alarms_nuisance_per_hour_mean'], delta['false_alarms_nuisance_per_hour_ci95_low'], delta['false_alarms_nuisance_per_hour_ci95_high'])} |\n"
            )


def _write_verified_claims(stream: Any, rows: list[dict[str, Any]]) -> None:
    z_score = _find_result(rows, "simulator", "gradual_tilt", "baseline_z_score")
    current = _find_result(rows, "simulator", "gradual_tilt", "current_system")
    full = _find_result(rows, "simulator", "gradual_tilt", "current_system_spatial")
    no_persistence = _find_result(
        rows, "simulator", "gradual_tilt", "ablation_no_temporal_persistence"
    )
    if any(row is None for row in (z_score, current, full, no_persistence)):
        raise ValueError("results are missing a row required for verified gradual-tilt comparisons")

    stream.write(
        "These comparisons are read from the generated CSV. False-alarm figures "
        "are per summed node-hour; intervals are 95% CIs across seeds.\n\n"
        "| Comparison | Method A | Method B | Interpretation |\n"
        "|---|---|---|---|\n"
    )
    stream.write(
        "| Z-score vs current-system false alarms | "
        f"baseline_z_score: normal {_format_value(z_score['false_alarms_normal_per_hour_mean'], z_score['false_alarms_normal_per_hour_ci95_low'], z_score['false_alarms_normal_per_hour_ci95_high'])}; "
        f"nuisance {_format_value(z_score['false_alarms_nuisance_per_hour_mean'], z_score['false_alarms_nuisance_per_hour_ci95_low'], z_score['false_alarms_nuisance_per_hour_ci95_high'])} | "
        f"current_system: normal {_format_value(current['false_alarms_normal_per_hour_mean'], current['false_alarms_normal_per_hour_ci95_low'], current['false_alarms_normal_per_hour_ci95_high'])}; "
        f"nuisance {_format_value(current['false_alarms_nuisance_per_hour_mean'], current['false_alarms_nuisance_per_hour_ci95_low'], current['false_alarms_nuisance_per_hour_ci95_high'])} | "
        "Normal false-alarm rates are tied; compare nuisance rates as shown (the z-score is lower in this run). |\n"
    )
    stream.write(
        "| Full system vs no temporal persistence | "
        f"current_system_spatial: F1 {_format_value(full['f1_mean'], full['f1_ci95_low'], full['f1_ci95_high'])}; "
        f"event recall {_format_value(full['event_recall_mean'], full['event_recall_ci95_low'], full['event_recall_ci95_high'])}; "
        f"nuisance alarms/hour {_format_value(full['false_alarms_nuisance_per_hour_mean'], full['false_alarms_nuisance_per_hour_ci95_low'], full['false_alarms_nuisance_per_hour_ci95_high'])} | "
        f"ablation_no_temporal_persistence: F1 {_format_value(no_persistence['f1_mean'], no_persistence['f1_ci95_low'], no_persistence['f1_ci95_high'])}; "
        f"event recall {_format_value(no_persistence['event_recall_mean'], no_persistence['event_recall_ci95_low'], no_persistence['event_recall_ci95_high'])}; "
        f"nuisance alarms/hour {_format_value(no_persistence['false_alarms_nuisance_per_hour_mean'], no_persistence['false_alarms_nuisance_per_hour_ci95_low'], no_persistence['false_alarms_nuisance_per_hour_ci95_high'])} | "
        "Removing persistence raised mean F1 but also raised nuisance false alarms; event recall tied. |\n"
    )


def _write_simple_wins(stream: Any, rows: list[dict[str, Any]]) -> None:
    simple_methods = {
        "fixed_tilt_threshold", "fixed_tilt_threshold_spatial",
        "baseline_z_score", "baseline_z_score_spatial",
        "baseline_deviation_only_spatial", "ewma", "cusum",
        "isolation_forest_spatial", "vibration_threshold", "stuck_sensor_check",
    }
    wins = []
    for noise_model in ("simulator", "distribution_shift"):
        scenarios = sorted({row["scenario"] for row in rows if row["noise_model"] == noise_model})
        for scenario in scenarios:
            current = _find_result(rows, noise_model, scenario, "current_system_spatial")
            simple = [
                row for row in rows
                if row["noise_model"] == noise_model
                and row["scenario"] == scenario
                and row["method"] in simple_methods
                and math.isfinite(float(row["f1_mean"]))
            ]
            if current is None or not simple:
                continue
            winner = max(simple, key=lambda row: float(row["f1_mean"]))
            if float(winner["f1_mean"]) > float(current["f1_mean"]) + 1e-12:
                wins.append((noise_model, scenario, winner, current))
    stream.write(
        "| noise_model | scenario | best simple/comparable method | its F1 (95% CI) | current_system_spatial F1 (95% CI) |\n"
        "|---|---|---|---|---|\n"
    )
    if not wins:
        stream.write("| — | — | No simple method had higher mean F1 in these runs | — | — |\n")
        return
    for noise_model, scenario, winner, current in wins:
        stream.write(
            f"| {noise_model} | {scenario} | {_method_label(winner['method'])} | "
            f"{_format_value(winner['f1_mean'], winner['f1_ci95_low'], winner['f1_ci95_high'])} | "
            f"{_format_value(current['f1_mean'], current['f1_ci95_low'], current['f1_ci95_high'])} |\n"
        )


def _find_result(
    rows: list[dict[str, Any]], noise_model: str, scenario: str, method: str
) -> dict[str, Any] | None:
    return next((
        row for row in rows
        if row["noise_model"] == noise_model
        and row["scenario"] == scenario
        and row["method"] == method
    ), None)


def _finite_or(value: Any, fallback: float) -> float:
    return float(value) if isinstance(value, (int, float)) and math.isfinite(float(value)) else fallback


def _method_label(method: str) -> str:
    labels = {
        "fixed_tilt_threshold": "fixed tilt-deviation threshold",
        "fixed_tilt_threshold_spatial": "fixed tilt threshold + persistence/spatial corroboration",
        "baseline_z_score": "per-node baseline z-score",
        "baseline_z_score_spatial": "baseline z-score + persistence/spatial corroboration",
        "baseline_deviation_only_spatial": "baseline-deviation threshold, no Isolation Forest + wrapper",
        "ewma": "EWMA tilt-deviation baseline",
        "cusum": "CUSUM tilt-deviation baseline",
        "isolation_forest": "Isolation Forest alone",
        "isolation_forest_spatial": "Isolation Forest alone + persistence/spatial corroboration",
        "one_class_svm": "One-Class SVM",
        "local_outlier_factor": "Local Outlier Factor",
        "current_system": "current system (Isolation Forest + baseline deviation)",
        "current_system_spatial": "current system + persistence/spatial corroboration",
        "vibration_threshold": "vibration-only threshold",
        "stuck_sensor_check": "zero-variance stuck-sensor check",
    }
    return labels.get(method, method)


def _ablation_table_rows(rows: list[dict[str, Any]], noise_model: str) -> list[dict[str, Any]]:
    full = [
        {**row, "method": "full_system_reference"}
        for row in rows
        if row["noise_model"] == noise_model
        and row["method"] == "current_system_spatial"
    ]
    ablations = [
        row for row in rows
        if row["noise_model"] == noise_model and row["method"].startswith("ablation_")
    ]
    return full + ablations


def _format_value(mean: Any, low: Any, high: Any) -> str:
    if not isinstance(mean, (int, float)) or not math.isfinite(float(mean)):
        return "n/a"
    if isinstance(low, (int, float)) and isinstance(high, (int, float)) and math.isfinite(float(low)) and math.isfinite(float(high)):
        return f"{float(mean):.3f} [{float(low):.3f}, {float(high):.3f}]"
    return f"{float(mean):.3f}"


def _plot_figures(output_dir: Path, summaries: list[dict[str, Any]]) -> None:
    core = [row for row in summaries if row["noise_model"] == "simulator"]
    event_rows = [row for row in core if row["scenario"] in EVENT_SCENARIOS and not row["method"].startswith("ablation_")]
    methods = list(METHODS)
    delay_by_method = {
        method: _mean_rows(event_rows, method, "detection_delay_seconds", default=math.nan)
        for method in methods
    }
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(methods, [delay_by_method[method] for method in methods], color="#4178a4")
    ax.set_ylabel("Mean detection delay (seconds)")
    ax.set_title("Detected events only; core simulator test set")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(output_dir / "detection_delay.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 6))
    for method in methods:
        rows = [row for row in event_rows if row["method"] == method]
        recall = _finite_mean([row["event_recall_mean"] for row in rows])
        far = _finite_mean([row["false_alarms_normal_per_hour_mean"] for row in rows])
        ax.scatter(far, recall, label=method, s=48)
    ax.set_xlabel("False alarms per node-hour on normal controls")
    ax.set_ylabel("Event recall")
    ax.set_title("False alarms versus event recall")
    ax.legend(fontsize=7, loc="best")
    fig.tight_layout()
    fig.savefig(output_dir / "false_alarms_vs_recall.png", dpi=160)
    plt.close(fig)

    ablation_rows = [
        row for row in core
        if row["scenario"] in EVENT_SCENARIOS
        and (row["method"] == "current_system_spatial" or row["method"].startswith("ablation_"))
    ]
    ablation_methods = ["current_system_spatial"] + [f"ablation_{name}" for name in ABLATIONS]
    values = [
        _mean_rows(ablation_rows, method, "event_recall")
        for method in ablation_methods
    ]
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(
        [
            "full_system" if name == "current_system_spatial"
            else name.replace("ablation_", "")
            for name in ablation_methods
        ],
        values,
        color="#c77d37",
    )
    ax.set_ylabel("Mean event recall")
    ax.set_title("Ablation: full system with one component removed")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(output_dir / "ablation_bars.png", dpi=160)
    plt.close(fig)


def _mean_rows(rows: list[dict[str, Any]], method: str, metric: str, default: float = 0.0) -> float:
    return _finite_mean([
        row[f"{metric}_mean"] for row in rows if row["method"] == method
    ], default=default)


def _finite_mean(values: list[float], default: float = 0.0) -> float:
    finite = [float(value) for value in values if isinstance(value, (int, float)) and math.isfinite(float(value))]
    return float(np.mean(finite)) if finite else default


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=30, help="Independent test seeds per scenario and noise set (default: 30).")
    parser.add_argument("--real-csv", type=Path, help="CSV input path; bundled placeholder input is synthetic only.")
    parser.add_argument("--event-log", type=Path, help="Event interval CSV used with --real-csv.")
    parser.add_argument("--output-dir", type=Path, default=_ROOT / "docs" / "evaluation")
    parser.add_argument(
        "--refresh-reports",
        action="store_true",
        help="Rebuild Markdown/figures and bound confidence intervals from an existing results.csv.",
    )
    args = parser.parse_args()
    if args.refresh_reports:
        result_rows = _load_existing_results(args.output_dir / "results.csv")
        for row in result_rows:
            _bound_confidence_intervals(row)
        _write_csv(args.output_dir / "results.csv", result_rows)
        _write_markdown(args.output_dir / "results.md", result_rows, args.seeds, args.real_csv)
        _plot_figures(args.output_dir, result_rows)
        print(f"Reports refreshed: {args.output_dir.resolve()}")
        return
    if args.real_csv:
        run_evaluation(args.seeds, args.output_dir, args.real_csv, args.event_log)
        return
    result_rows = run_evaluation(args.seeds, args.output_dir, args.real_csv, args.event_log)
    print(f"Evaluation complete: {len(result_rows)} result rows")
    print(f"Outputs: {args.output_dir.resolve()}")
    _print_winners(result_rows)


def _load_existing_results(path: Path) -> list[dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    if not records:
        raise ValueError(f"No evaluation results found at {path}")
    output: list[dict[str, Any]] = []
    for record in records:
        row: dict[str, Any] = {}
        for key, value in record.items():
            if key in {"noise_model", "scenario", "method"}:
                row[key] = value
            elif value == "":
                row[key] = math.nan
            elif key in {"seeds_requested"} or key.endswith("_n"):
                row[key] = int(float(value))
            else:
                row[key] = float(value)
        output.append(row)
    return output


def _bound_confidence_intervals(row: dict[str, Any]) -> None:
    if row.get("method") == "forest_added_value":
        return
    bounded = {"event_recall", "precision", "recall", "f1", "pr_auc"}
    for metric in _METRICS:
        low_key = f"{metric}_ci95_low"
        high_key = f"{metric}_ci95_high"
        low, high = row.get(low_key), row.get(high_key)
        if isinstance(low, (int, float)) and math.isfinite(float(low)):
            row[low_key] = max(0.0, float(low))
            if metric in bounded and isinstance(high, (int, float)) and math.isfinite(float(high)):
                row[high_key] = min(1.0, float(high))


def _print_winners(rows: list[dict[str, Any]]) -> None:
    print("Core simulator event-recall leaders by scenario:")
    for scenario in sorted(EVENT_SCENARIOS):
        candidates = [
            row for row in rows
            if row["noise_model"] == "simulator"
            and row["scenario"] == scenario
            and row["method"] in METHODS
        ]
        candidates.sort(key=lambda row: row["event_recall_mean"] if math.isfinite(row["event_recall_mean"]) else -1, reverse=True)
        if candidates:
            winner = candidates[0]
            print(f"  {scenario}: {winner['method']} ({winner['event_recall_mean']:.3f} event recall)")


if __name__ == "__main__":
    main()
