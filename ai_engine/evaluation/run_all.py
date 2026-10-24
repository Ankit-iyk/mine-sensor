"""Run the complete evaluation: python -m ai_engine.evaluation.run_all --seeds 30."""

from __future__ import annotations

import argparse
import csv
import math
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
_METRICS = (
    "event_recall", "detection_delay_seconds", "false_alarms_normal_per_hour",
    "false_alarms_nuisance_per_hour", "precision", "recall", "f1", "pr_auc",
)


def run_evaluation(
    seeds: int = 30,
    output_dir: Path | None = None,
    real_csv: Path | None = None,
) -> list[dict[str, Any]]:
    if seeds < 1:
        raise ValueError("--seeds must be at least 1")
    output_dir = output_dir or (_ROOT / "docs" / "evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    training_rows = _training_features(seeds)
    suite = MethodSuite(training_rows)
    summaries: list[dict[str, Any]] = []

    for noise_model, seed_base in (("simulator", _TEST_SEED_BASE), ("distribution_shift", _SHIFT_SEED_BASE)):
        episodes: dict[tuple[str, int], list[dict[str, Any]]] = {}
        control_cache: dict[tuple[str, int], tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]] = {}
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
                    seed_records.append(_episode_metrics(
                        rows, scores, alerts,
                        controls,
                    ))
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
    if real_csv:
        summaries.extend(_evaluate_real_csv(suite, real_csv))

    _write_csv(output_dir / "results.csv", summaries)
    _write_markdown(output_dir / "results.md", summaries, seeds, real_csv)
    _plot_figures(output_dir, summaries)
    return summaries


def _training_features(seeds: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    train_seed_count = max(30, seeds)
    for offset in range(train_seed_count):
        seed = _TRAIN_SEED_BASE + offset
        normal = generate_episode("normal", seed, "simulator")
        features = extract_backend_features(normal)
        rows.extend(features[::_TRAIN_KEEP_EVERY])
    if any(row["seed"] < _TRAIN_SEED_BASE for row in rows):
        raise RuntimeError("training/test seed partition overlap detected")
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
            "fit on the same normal-only training rows as the Isolation Forest. "
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
        _write_table(stream, [row for row in rows if row["noise_model"] == "simulator" and not row["method"].startswith("ablation_")])
        stream.write("\n## Distribution-shift results\n\n")
        _write_table(stream, [row for row in rows if row["noise_model"] == "distribution_shift" and not row["method"].startswith("ablation_")])
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
            "Compare `baseline_deviation_only_spatial` against `current_system_spatial`: "
            "both use the same persistence/spatial wrapper, so differences isolate the fitted "
            "Isolation Forest's contribution to the current system's baseline-deviation alerts.\n\n"
        )
        _write_isolation_forest_value_table(stream, rows)
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
            "The backend Isolation Forest is retrained on the documented normal-only training partition for this comparison; "
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
            and not row["method"].startswith("ablation_")
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
        scenarios = sorted({row["scenario"] for row in rows if row["noise_model"] == noise_model})
        for scenario in scenarios:
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
        "| noise_model | scenario | baseline-only F1 (95% CI) | current-system F1 (95% CI) | baseline-only event recall (95% CI) | current-system event recall (95% CI) |\n"
        "|---|---|---|---|---|---|\n"
    )
    for noise_model in ("simulator", "distribution_shift"):
        scenarios = sorted({row["scenario"] for row in rows if row["noise_model"] == noise_model})
        for scenario in scenarios:
            baseline = _find_result(rows, noise_model, scenario, "baseline_deviation_only_spatial")
            current = _find_result(rows, noise_model, scenario, "current_system_spatial")
            if baseline is None or current is None:
                continue
            stream.write(
                f"| {noise_model} | {scenario} | "
                f"{_format_value(baseline['f1_mean'], baseline['f1_ci95_low'], baseline['f1_ci95_high'])} | "
                f"{_format_value(current['f1_mean'], current['f1_ci95_low'], current['f1_ci95_high'])} | "
                f"{_format_value(baseline['event_recall_mean'], baseline['event_recall_ci95_low'], baseline['event_recall_ci95_high'])} | "
                f"{_format_value(current['event_recall_mean'], current['event_recall_ci95_low'], current['event_recall_ci95_high'])} |\n"
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
    parser.add_argument("--real-csv", type=Path, help="Optional labelled hardware CSV to score with the same pipeline.")
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
    result_rows = run_evaluation(args.seeds, args.output_dir, args.real_csv)
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
