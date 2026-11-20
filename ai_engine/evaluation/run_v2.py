"""Single-run executor for the frozen v2 event-discrimination evaluation."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
import sklearn

from ai_engine.adapter import AIEngineDetector
from ai_engine.anomaly.isolation_forest import DEFAULT_MODEL_PATH
from ai_engine.evaluation.classifier_v2 import (
    RuleBaselineV2,
    SupervisedClassifierV2,
    fit_rule_baseline_v2,
)
from ai_engine.evaluation.datasets_v2 import (
    CLASS_NAMES_V2,
    EPISODE_MINUTES_V2,
    EVENT_ONSET_MINUTE_V2,
    INFERENCE_INTERVAL_MINUTES_V2,
    SCENARIOS_V2,
    EpisodeV2,
    class_at_inference_v2,
    generate_episode_v2,
)
from ai_engine.evaluation.features_v2 import (
    FEATURE_NAMES_V2,
    inference_minutes_v2,
    extract_window_features_v2,
)


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / "docs" / "evaluation" / "PROTOCOL_V2.md"
FREEZE_PATH = ROOT / "docs" / "evaluation" / "protocol_freeze_v2.json"
OUTPUT_DIR = ROOT / "docs" / "evaluation" / "confirmatory_v2"
TRAINING_SEEDS = range(400000, 400200)
CALIBRATION_SEEDS = range(450000, 450050)
CONFIRMATORY_SEEDS = tuple(range(500000, 500030))
BOOTSTRAP_RESAMPLES = 10_000
PERMUTATION_RESAMPLES = 10_000
BOOTSTRAP_SEED = 600002
PERMUTATION_SEED = 600003
METHODS = ("rule", "supervised", "isolation_forest", "current_system")
CLASS_METHODS = ("rule", "supervised")
PREDICTION_LABELS = (*CLASS_NAMES_V2, "UNKNOWN")
CONDITION_NAMES = (
    "default",
    "blast_decay_0.10s",
    "blast_decay_0.30s",
    "blast_decay_0.80s",
    "blast_tilt_0.00deg",
    "blast_tilt_0.05deg",
    "blast_tilt_0.10deg",
    "blast_peak_0.25",
    "blast_peak_0.50",
    "blast_peak_0.75",
    "progressive_rate_0.01deg_per_hour",
    "progressive_rate_0.05deg_per_hour",
    "progressive_rate_0.10deg_per_hour",
    "held_out_shifted",
)

RESULT_FIELDS = (
    "method",
    "seed",
    "scenario",
    "node_index",
    "condition_index",
    "condition_name",
    "noise_model",
    "inference_minute",
    "truth_label",
    "predicted_label",
    "binary_true",
    "binary_predicted",
    "event_active",
    "confidence",
    "probability_blast",
    "probability_progressive",
    "probability_other",
    "score",
    "detector_mode",
    "origin",
    "residual_window_type",
    "observed_exposure_hours",
    "parameters_json",
    *FEATURE_NAMES_V2,
)


def main() -> int:
    protocol_hash = _verified_protocol_hash()
    if not PROTOCOL_PATH.is_file():
        raise FileNotFoundError(f"Frozen v2 protocol is missing: {PROTOCOL_PATH}")
    if not Path(DEFAULT_MODEL_PATH).is_file():
        raise FileNotFoundError(
            f"Required unchanged Isolation Forest artifact is missing: {DEFAULT_MODEL_PATH}"
        )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if any(OUTPUT_DIR.iterdir()):
        raise FileExistsError(
            f"v2 output directory is not empty; refusing to rerun: {OUTPUT_DIR}"
        )

    started = datetime.now(timezone.utc)
    classifier, rule, training_rows, calibration_rows, threshold_metrics = _fit_models()
    legacy = AIEngineDetector()
    legacy.load(str(DEFAULT_MODEL_PATH))

    dimensions = (
        len(CONDITION_NAMES),
        len(CONFIRMATORY_SEEDS),
        len(SCENARIOS_V2),
        len(inference_minutes_v2()),
        3,
    )
    truth = np.full(dimensions, "", dtype=object)
    active = np.zeros(dimensions, dtype=bool)
    node_mask = np.zeros((len(SCENARIOS_V2), 3), dtype=bool)
    for scenario_index, scenario in enumerate(SCENARIOS_V2):
        node_mask[scenario_index, : (3 if scenario == "progressive_correlated" else 1)] = True
    class_predictions = {
        method: np.full(dimensions, "", dtype=object)
        for method in CLASS_METHODS
    }
    binary_predictions = {
        method: np.zeros(dimensions, dtype=bool)
        for method in METHODS
    }
    legacy_scores = {
        method: np.full(dimensions, np.nan, dtype=np.float64)
        for method in ("isolation_forest", "current_system")
    }
    examples: dict[str, EpisodeV2] = {}
    row_count = 0
    losses: list[dict[str, Any]] = []
    labels = CLASS_NAMES_V2
    endpoints = inference_minutes_v2()
    endpoint_index = {minute: index for index, minute in enumerate(endpoints)}
    scenario_index = {scenario: index for index, scenario in enumerate(SCENARIOS_V2)}
    seed_index = {seed: index for index, seed in enumerate(CONFIRMATORY_SEEDS)}

    results_path = OUTPUT_DIR / "results.csv"
    with results_path.open("w", newline="", encoding="utf-8") as results_file:
        writer = csv.DictWriter(results_file, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        for condition_index, condition_name in enumerate(CONDITION_NAMES):
            for seed in CONFIRMATORY_SEEDS:
                for scenario in SCENARIOS_V2:
                    episode = generate_episode_v2(
                        scenario,
                        seed,
                        condition_index=condition_index,
                    )
                    s_index = scenario_index[scenario]
                    seed_position = seed_index[seed]
                    if condition_index == 0 and seed == CONFIRMATORY_SEEDS[0]:
                        if scenario in {"blast_impulse", "progressive_single", "phone_like_vibration"}:
                            examples[scenario] = episode
                    for node_index_value in range(episode.node_count):
                        feature_rows = [
                            extract_window_features_v2(
                                episode,
                                end_minute,
                                node_index=node_index_value,
                            )
                            for end_minute in endpoints
                        ]
                        rule_labels = rule.predict(feature_rows)
                        supervised_labels = classifier.predict(feature_rows)
                        supervised_probabilities = classifier.predict_proba(feature_rows)
                        probability_columns = {
                            str(name): column
                            for column, name in enumerate(classifier.model.classes_)
                        }
                        for window_index, feature_row in enumerate(feature_rows):
                            end_minute = endpoints[window_index]
                            start_minute = end_minute - INFERENCE_INTERVAL_MINUTES_V2
                            truth_label, event_active = class_at_inference_v2(
                                episode, start_minute, end_minute
                            )
                            truth[condition_index, seed_position, s_index, window_index, node_index_value] = truth_label
                            active[condition_index, seed_position, s_index, window_index, node_index_value] = event_active

                            legacy_features = _legacy_feature_mapping(feature_row)
                            legacy_output = legacy.predict(legacy_features)
                            legacy_results = {
                                "isolation_forest": (
                                    bool(float(legacy_output["raw_score"]) < 0.0),
                                    float(legacy_output["raw_score"]),
                                ),
                                "current_system": (
                                    legacy_output["state"] == "ANOMALOUS",
                                    float(legacy_output["anomaly_score"]),
                                ),
                            }
                            prediction_values = {
                                "rule": (str(rule_labels[window_index]), None, None, "frozen_rule"),
                                "supervised": (
                                    str(supervised_labels[window_index]),
                                    supervised_probabilities[window_index],
                                    float(np.max(supervised_probabilities[window_index])),
                                    "multinomial_logistic_regression",
                                ),
                            }
                            binary_target = truth_label != "OTHER_TRANSIENT_OR_NORMAL"
                            for method in CLASS_METHODS:
                                prediction, probabilities, confidence, detector_mode = prediction_values[method]
                                class_predictions[method][condition_index, seed_position, s_index, window_index, node_index_value] = prediction
                                binary_prediction = prediction in {
                                    "BLAST_TRANSIENT",
                                    "PROGRESSIVE_TILT_PROXY",
                                }
                                binary_predictions[method][condition_index, seed_position, s_index, window_index, node_index_value] = binary_prediction
                                _write_result_row(
                                    writer,
                                    method,
                                    episode,
                                    condition_index,
                                    condition_name,
                                    node_index_value,
                                    feature_row,
                                    truth_label,
                                    prediction,
                                    binary_target,
                                    binary_prediction,
                                    event_active,
                                    confidence,
                                    probabilities,
                                    probability_columns,
                                    None,
                                    detector_mode,
                                )
                                row_count += 1

                            for method, (binary_prediction, score) in legacy_results.items():
                                binary_predictions[method][condition_index, seed_position, s_index, window_index, node_index_value] = binary_prediction
                                legacy_scores[method][condition_index, seed_position, s_index, window_index, node_index_value] = score
                                _write_result_row(
                                    writer,
                                    method,
                                    episode,
                                    condition_index,
                                    condition_name,
                                    node_index_value,
                                    feature_row,
                                    truth_label,
                                    "",
                                    binary_target,
                                    binary_prediction,
                                    event_active,
                                    None,
                                    None,
                                    {},
                                    score,
                                    "existing_model",
                                )
                                row_count += 1

    if not examples.keys() >= {"blast_impulse", "progressive_single", "phone_like_vibration"}:
        raise RuntimeError("required example signal episodes were not retained")

    classifier_artifact = OUTPUT_DIR / "supervised_classifier.joblib"
    joblib.dump(classifier, classifier_artifact)
    (OUTPUT_DIR / "losses.csv").write_text(
        "status,seed,scenario,condition_index,node_index,inference_minute,reason\n"
        "zero_losses,,,,,,none\n",
        encoding="utf-8",
    )

    rng_bootstrap = np.random.default_rng(BOOTSTRAP_SEED)
    rng_permutation = np.random.default_rng(PERMUTATION_SEED)
    report_data = _summarize(
        truth,
        active,
        node_mask,
        class_predictions,
        binary_predictions,
        CONFIRMATORY_SEEDS,
        condition_names=CONDITION_NAMES,
        rng_bootstrap=rng_bootstrap,
        rng_permutation=rng_permutation,
    )
    paired_path = OUTPUT_DIR / "paired_tests.csv"
    _write_paired_tests(paired_path, report_data["paired_tests"])
    _write_figures(
        OUTPUT_DIR,
        truth,
        node_mask,
        class_predictions,
        binary_predictions,
        report_data,
        examples,
    )

    finished = datetime.now(timezone.utc)
    metadata = {
        "protocol": "docs/evaluation/PROTOCOL_V2.md",
        "protocol_sha256": protocol_hash,
        "code_revision": _git_revision(),
        "run_command": "python ai_engine/evaluation/run_v2.py",
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "duration_seconds": (finished - started).total_seconds(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "seeds": {
            "training": [400000, 400199],
            "calibration": [450000, 450049],
            "confirmatory": [500000, 500029],
        },
        "scenario_order": list(SCENARIOS_V2),
        "conditions": list(CONDITION_NAMES),
        "method_names": list(METHODS),
        "inference_interval_minutes": INFERENCE_INTERVAL_MINUTES_V2,
        "inference_windows_per_node": len(endpoints),
        "confirmatory_episode_node_rows": int(
            len(CONFIRMATORY_SEEDS)
            * sum(3 if scenario == "progressive_correlated" else 1 for scenario in SCENARIOS_V2)
        ),
        "prediction_rows_written": row_count,
        "training_feature_rows": len(training_rows),
        "calibration_feature_rows": len(calibration_rows),
        "rule_thresholds": rule.thresholds.as_dict(),
        "rule_calibration_metrics": threshold_metrics,
        "supervised_temperature": classifier.temperature,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "permutation_resamples": PERMUTATION_RESAMPLES,
        "permutation_seed": PERMUTATION_SEED,
        "loss_count": len(losses),
        "legacy_model_path": str(Path(DEFAULT_MODEL_PATH).relative_to(ROOT)),
        "origin": "simulation",
    }
    (OUTPUT_DIR / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_analysis(
    ROOT / "docs" / "evaluation" / "CONFIRMATORY_ANALYSIS_V2.md",
        report_data,
        metadata,
    )
    print(f"Protocol SHA-256 verified: {protocol_hash}")
    print(f"Prediction rows written: {row_count}")
    print(f"Loss count: {len(losses)}")
    print(f"Rule thresholds: {json.dumps(rule.thresholds.as_dict(), sort_keys=True)}")
    print(f"Classifier temperature: {classifier.temperature:g}")
    print(f"Outputs: {OUTPUT_DIR}")
    return 0


def _fit_models() -> tuple[
    SupervisedClassifierV2,
    RuleBaselineV2,
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, float],
]:
    training_rows = _split_rows(TRAINING_SEEDS, training=True)
    calibration_rows = _split_rows(CALIBRATION_SEEDS, training=True)
    classifier = SupervisedClassifierV2()
    classifier.fit(training_rows)
    temperature = classifier.calibrate_temperature(calibration_rows)
    if temperature not in (0.50, 0.75, 1.00, 1.50, 2.00):
        raise RuntimeError("temperature calibration returned a non-protocol value")
    rule, threshold_metrics = fit_rule_baseline_v2(calibration_rows)
    return classifier, rule, training_rows, calibration_rows, threshold_metrics


def _split_rows(seeds: Any, *, training: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    endpoints = inference_minutes_v2()
    for seed in seeds:
        for scenario in SCENARIOS_V2:
            episode = generate_episode_v2(
                scenario,
                seed,
                condition_index=0,
                training=training,
            )
            for node_index in range(episode.node_count):
                rows.extend(
                    extract_window_features_v2(
                        episode,
                        minute,
                        node_index=node_index,
                    )
                    for minute in endpoints
                )
    return rows


def _legacy_feature_mapping(features: dict[str, Any]) -> dict[str, float]:
    deviation = float(features["cumulative_tilt_magnitude_degrees"])
    vibration = float(features["vibration_peak"])
    tilt_x = 1.0 + float(features["cumulative_tilt_x_degrees"])
    tilt_y = 0.8 + float(features["cumulative_tilt_y_degrees"])
    return {
        "tilt_magnitude": float(np.hypot(tilt_x, tilt_y)),
        "tilt_deviation": deviation,
        "tilt_rate": float(features["drift_slope_degrees_per_hour"]),
        "rolling_mean_tilt": float(np.hypot(tilt_x, tilt_y)),
        "rolling_std_tilt": 0.05,
        "vibration_intensity": vibration,
        "vibration_event_count": int(vibration >= 0.35),
        "vibration_frequency": float(features["vibration_event_duration_seconds"]) / 900.0,
        "rolling_mean_vib": float(features["vibration_energy_sim_units"]),
        "rolling_std_vib": 0.02,
        "trend_slope": float(features["drift_slope_degrees_per_hour"]),
        "baseline_deviation": deviation,
    }


def _write_result_row(
    writer: csv.DictWriter,
    method: str,
    episode: EpisodeV2,
    condition_index: int,
    condition_name: str,
    node_index: int,
    features: dict[str, Any],
    truth_label: str,
    predicted_label: str,
    binary_true: bool,
    binary_predicted: bool,
    event_active: bool,
    confidence: float | None,
    probabilities: np.ndarray | None,
    probability_columns: dict[str, int],
    score: float | None,
    detector_mode: str,
) -> None:
    probs = probabilities
    writer.writerow({
        "method": method,
        "seed": episode.seed,
        "scenario": episode.scenario,
        "node_index": node_index,
        "condition_index": condition_index,
        "condition_name": condition_name,
        "noise_model": "shifted" if condition_index == 13 else "stationary",
        "inference_minute": features["inference_minute"],
        "truth_label": truth_label,
        "predicted_label": predicted_label,
        "binary_true": int(binary_true),
        "binary_predicted": int(binary_predicted),
        "event_active": int(event_active),
        "confidence": "" if confidence is None else confidence,
        "probability_blast": (
            "" if probs is None else float(probs[probability_columns["BLAST_TRANSIENT"]])
        ),
        "probability_progressive": (
            "" if probs is None else float(probs[probability_columns["PROGRESSIVE_TILT_PROXY"]])
        ),
        "probability_other": (
            "" if probs is None else float(probs[probability_columns["OTHER_TRANSIENT_OR_NORMAL"]])
        ),
        "score": "" if score is None else score,
        "detector_mode": detector_mode,
        "origin": episode.origin,
        "residual_window_type": features["residual_window_type"],
        "observed_exposure_hours": features["observed_exposure_hours"],
        "parameters_json": json.dumps(episode.parameters, sort_keys=True, separators=(",", ":")),
        **{name: features[name] for name in FEATURE_NAMES_V2},
    })


def _summarize(
    truth: np.ndarray,
    active: np.ndarray,
    node_mask: np.ndarray,
    class_predictions: dict[str, np.ndarray],
    binary_predictions: dict[str, np.ndarray],
    seeds: tuple[int, ...],
    *,
    condition_names: tuple[str, ...],
    rng_bootstrap: np.random.Generator,
    rng_permutation: np.random.Generator,
) -> dict[str, Any]:
    class_confusions: dict[tuple[int, str], np.ndarray] = {}
    binary_confusions: dict[tuple[int, str], np.ndarray] = {}
    class_metrics: list[dict[str, Any]] = []
    binary_metrics: list[dict[str, Any]] = []
    blast_rates: list[dict[str, Any]] = []
    progressive_delays: list[dict[str, Any]] = []
    scenario_false_classes: list[dict[str, Any]] = []
    normal_false_alarms: list[dict[str, Any]] = []
    seed_metric_values: dict[tuple[int, str, str], np.ndarray] = {}
    blast_rate_seed_values: dict[tuple[int, str], np.ndarray] = {}
    normal_alarm_seed_values: dict[tuple[int, str], np.ndarray] = {}

    for condition_index, condition_name in enumerate(condition_names):
        for method in CLASS_METHODS:
            per_seed_confusion = _class_confusions_by_seed(
                truth[condition_index],
                class_predictions[method][condition_index],
                node_mask,
            )
            class_confusions[(condition_index, method)] = per_seed_confusion
            total = per_seed_confusion.sum(axis=0)
            for class_index, class_name in enumerate(CLASS_NAMES_V2):
                precision, recall, f1, support = _class_metrics_from_confusion(
                    total, class_index
                )
                ci = _bootstrap_class_metric(
                    per_seed_confusion,
                    class_index,
                    rng_bootstrap,
                )
                class_metrics.append({
                    "condition_index": condition_index,
                    "condition_name": condition_name,
                    "method": method,
                    "class": class_name,
                    "precision": precision,
                    "precision_ci_low": ci["precision"][0],
                    "precision_ci_high": ci["precision"][1],
                    "recall": recall,
                    "recall_ci_low": ci["recall"][0],
                    "recall_ci_high": ci["recall"][1],
                    "f1": f1,
                    "f1_ci_low": ci["f1"][0],
                    "f1_ci_high": ci["f1"][1],
                    "support": support,
                })
            seed_metric_values[(condition_index, method, "macro_f1")] = np.asarray([
                _macro_f1_from_confusion(matrix)
                for matrix in per_seed_confusion
            ])
            for seed_position in range(len(seeds)):
                seed_mask = _valid_node_mask(node_mask, truth.shape[2], truth.shape[3])
                seed_mask = np.broadcast_to(seed_mask, truth[condition_index, seed_position].shape)
                valid = (truth[condition_index, seed_position] != "") & seed_mask
                truth_seed = truth[condition_index, seed_position][valid]
                pred_seed = class_predictions[method][condition_index, seed_position][valid]
                positive = truth_seed == "PROGRESSIVE_TILT_PROXY"
                seed_metric_values.setdefault(
                    (condition_index, method, "progressive_recall"),
                    np.zeros(len(seeds), dtype=np.float64),
                )[seed_position] = (
                    float(np.mean(pred_seed[positive] == "PROGRESSIVE_TILT_PROXY"))
                    if np.any(positive)
                    else 0.0
                )

        for method in METHODS:
            per_seed_confusion = _binary_confusions_by_seed(
                truth[condition_index],
                binary_predictions[method][condition_index],
                node_mask,
            )
            binary_confusions[(condition_index, method)] = per_seed_confusion
            total = per_seed_confusion.sum(axis=0)
            precision, recall, f1, support = _binary_metrics_from_confusion(total)
            ci = _bootstrap_binary_metric(per_seed_confusion, rng_bootstrap)
            binary_metrics.append({
                "condition_index": condition_index,
                "condition_name": condition_name,
                "method": method,
                "precision": precision,
                "precision_ci_low": ci["precision"][0],
                "precision_ci_high": ci["precision"][1],
                "recall": recall,
                "recall_ci_low": ci["recall"][0],
                "recall_ci_high": ci["recall"][1],
                "f1": f1,
                "f1_ci_low": ci["f1"][0],
                "f1_ci_high": ci["f1"][1],
                "support": support,
            })

            normal_predictions = binary_predictions[method][
                condition_index, :, SCENARIOS_V2.index("normal"), :, 0
            ]
            normal_per_seed = np.sum(normal_predictions, axis=1).astype(np.float64) / (
                EPISODE_MINUTES_V2 / 60.0
            )
            normal_alarm_seed_values[(condition_index, method)] = normal_per_seed
            normal_ci = _bootstrap_mean(normal_per_seed, rng_bootstrap)
            normal_false_alarms.append({
                "condition_index": condition_index,
                "condition_name": condition_name,
                "method": method,
                "false_alarm_windows": int(np.sum(normal_predictions)),
                "exposure_hours": len(seeds) * (EPISODE_MINUTES_V2 / 60.0),
                "false_alarms_per_hour": float(np.mean(normal_per_seed)),
                "ci_low": normal_ci[0],
                "ci_high": normal_ci[1],
            })

            seed_metric_values[(condition_index, method, "progressive_recall")] = (
                seed_metric_values.get(
                    (condition_index, method, "progressive_recall"),
                    np.zeros(len(seeds), dtype=np.float64),
                )
            )
        for method in CLASS_METHODS:
            scenario_rate_values = []
            for scenario in ("blast_impulse", "blast_tilt_recovery"):
                scenario_pos = SCENARIOS_V2.index(scenario)
                post_onset = np.asarray(
                    [minute >= EVENT_ONSET_MINUTE_V2 for minute in inference_minutes_v2()]
                )
                predicted_progressive = (
                    class_predictions[method][condition_index, :, scenario_pos, :, 0]
                    == "PROGRESSIVE_TILT_PROXY"
                )
                per_seed_rate = np.any(
                    predicted_progressive[:, post_onset], axis=1
                ).astype(np.float64)
                scenario_rate_values.extend(per_seed_rate.tolist())
                ci = _bootstrap_mean(per_seed_rate, rng_bootstrap)
                blast_rates.append({
                    "condition_index": condition_index,
                    "condition_name": condition_name,
                    "method": method,
                    "scenario": scenario,
                    "false_progressive_episodes": int(np.sum(per_seed_rate)),
                    "episodes": len(seeds),
                    "rate": float(np.mean(per_seed_rate)),
                    "ci_low": ci[0],
                    "ci_high": ci[1],
                })
            blast_rate_seed_values[(condition_index, method)] = np.mean(
                np.asarray(scenario_rate_values).reshape(2, len(seeds)),
                axis=0,
            )

            for scenario in ("progressive_single", "progressive_correlated"):
                scenario_pos = SCENARIOS_V2.index(scenario)
                delay_per_seed: list[float] = []
                detections = 0
                node_count = 3 if scenario == "progressive_correlated" else 1
                for seed_position in range(len(seeds)):
                    node_delays = []
                    for node_index in range(node_count):
                        predictions = class_predictions[method][
                            condition_index, seed_position, scenario_pos, :, node_index
                        ]
                        candidates = [
                            minute for minute, prediction in zip(inference_minutes_v2(), predictions)
                            if minute >= EVENT_ONSET_MINUTE_V2
                            and prediction == "PROGRESSIVE_TILT_PROXY"
                        ]
                        if candidates:
                            detected = True
                            node_delays.append(float(candidates[0] - EVENT_ONSET_MINUTE_V2))
                        else:
                            detected = False
                            node_delays.append(float(EPISODE_MINUTES_V2 - EVENT_ONSET_MINUTE_V2))
                        detections += int(detected)
                    delay_per_seed.append(float(np.mean(node_delays)))
                delay_ci = _bootstrap_mean(np.asarray(delay_per_seed), rng_bootstrap)
                progressive_delays.append({
                    "condition_index": condition_index,
                    "condition_name": condition_name,
                    "method": method,
                    "scenario": scenario,
                    "mean_delay_minutes": float(np.mean(delay_per_seed)),
                    "ci_low": delay_ci[0],
                    "ci_high": delay_ci[1],
                    "detected_nodes": detections,
                    "total_nodes": len(seeds) * node_count,
                    "censored_nodes": len(seeds) * node_count - detections,
                })

        for method in CLASS_METHODS:
            for scenario in (
                "normal",
                "phone_like_vibration",
                "nonblast_impulse",
                "accel_vibration_without_tilt",
                "stuck_sensor",
                "progressive_correlated",
                "progressive_single",
            ):
                scenario_pos = SCENARIOS_V2.index(scenario)
                for label in ("BLAST_TRANSIENT", "PROGRESSIVE_TILT_PROXY"):
                    predicted = class_predictions[method][
                        condition_index, :, scenario_pos
                    ]
                    scenario_truth = truth[condition_index, :, scenario_pos]
                    valid_nodes = node_mask[scenario_pos]
                    selected_predictions = predicted[:, :, valid_nodes]
                    selected_truth = scenario_truth[:, :, valid_nodes]
                    false_predictions = (selected_truth != label) & (
                        selected_predictions == label
                    )
                    count = int(np.sum(false_predictions))
                    denominator = int(np.sum(selected_truth != label))
                    scenario_false_classes.append({
                        "condition_index": condition_index,
                        "condition_name": condition_name,
                        "method": method,
                        "scenario": scenario,
                        "false_class": label,
                        "prediction_count": count,
                        "inference_count": denominator,
                    })

    paired_tests = _paired_comparisons(
        seed_metric_values,
        blast_rate_seed_values,
        normal_alarm_seed_values,
        rng_bootstrap,
        rng_permutation,
    )
    return {
        "class_metrics": class_metrics,
        "binary_metrics": binary_metrics,
        "blast_rates": blast_rates,
        "progressive_delays": progressive_delays,
        "scenario_false_classes": scenario_false_classes,
        "normal_false_alarms": normal_false_alarms,
        "paired_tests": paired_tests,
        "class_confusions": class_confusions,
        "binary_confusions": binary_confusions,
        "class_seed_metrics": seed_metric_values,
    }


def _valid_node_mask(node_mask: np.ndarray, scenarios: int, windows: int) -> np.ndarray:
    return np.broadcast_to(node_mask[:, None, :], (scenarios, windows, 3))


def _class_confusions_by_seed(
    truth: np.ndarray,
    predicted: np.ndarray,
    node_mask: np.ndarray,
) -> np.ndarray:
    seed_count = truth.shape[0]
    confusions = np.zeros((seed_count, 3, 4), dtype=np.int64)
    valid_mask = _valid_node_mask(node_mask, truth.shape[1], truth.shape[2])
    truth_indices = {name: index for index, name in enumerate(CLASS_NAMES_V2)}
    pred_indices = {name: index for index, name in enumerate(PREDICTION_LABELS)}
    for seed_index in range(seed_count):
        valid = (truth[seed_index] != "") & valid_mask
        true_values = truth[seed_index][valid]
        predicted_values = predicted[seed_index][valid]
        for true_value, predicted_value in zip(true_values, predicted_values):
            confusions[seed_index, truth_indices[str(true_value)], pred_indices[str(predicted_value)]] += 1
    return confusions


def _binary_confusions_by_seed(
    truth: np.ndarray,
    predicted: np.ndarray,
    node_mask: np.ndarray,
) -> np.ndarray:
    seed_count = truth.shape[0]
    confusions = np.zeros((seed_count, 2, 2), dtype=np.int64)
    valid_mask = _valid_node_mask(node_mask, truth.shape[1], truth.shape[2])
    for seed_index in range(seed_count):
        valid = (truth[seed_index] != "") & valid_mask
        truth_positive = np.isin(
            truth[seed_index][valid],
            ("BLAST_TRANSIENT", "PROGRESSIVE_TILT_PROXY"),
        )
        predicted_positive = predicted[seed_index][valid]
        for actual, guessed in zip(truth_positive, predicted_positive):
            confusions[seed_index, int(actual), int(guessed)] += 1
    return confusions


def _class_metrics_from_confusion(
    confusion: np.ndarray, class_index: int
) -> tuple[float, float, float, int]:
    tp = int(confusion[class_index, class_index])
    fp = int(np.sum(confusion[:, class_index]) - tp)
    fn = int(np.sum(confusion[class_index, :]) - tp)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1, int(np.sum(confusion[class_index, :]))


def _binary_metrics_from_confusion(
    confusion: np.ndarray,
) -> tuple[float, float, float, int]:
    return _class_metrics_from_confusion(confusion, 1)


def _macro_f1_from_confusion(confusion: np.ndarray) -> float:
    return float(np.mean([
        _class_metrics_from_confusion(confusion, index)[2]
        for index in range(3)
    ]))


def _bootstrap_class_metric(
    per_seed_confusion: np.ndarray,
    class_index: int,
    rng: np.random.Generator,
) -> dict[str, tuple[float, float]]:
    draws = rng.integers(0, len(per_seed_confusion), size=(BOOTSTRAP_RESAMPLES, len(per_seed_confusion)))
    sampled = per_seed_confusion[draws].sum(axis=1)
    tp = sampled[:, class_index, class_index].astype(np.float64)
    fp = sampled[:, :, class_index].sum(axis=1) - tp
    fn = sampled[:, class_index, :].sum(axis=1) - tp
    precision = np.divide(tp, tp + fp, out=np.zeros_like(tp), where=(tp + fp) > 0)
    recall = np.divide(tp, tp + fn, out=np.zeros_like(tp), where=(tp + fn) > 0)
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros_like(tp),
        where=(precision + recall) > 0,
    )
    return {
        "precision": tuple(np.percentile(precision, [2.5, 97.5]).tolist()),
        "recall": tuple(np.percentile(recall, [2.5, 97.5]).tolist()),
        "f1": tuple(np.percentile(f1, [2.5, 97.5]).tolist()),
    }


def _bootstrap_binary_metric(
    per_seed_confusion: np.ndarray,
    rng: np.random.Generator,
) -> dict[str, tuple[float, float]]:
    draws = rng.integers(0, len(per_seed_confusion), size=(BOOTSTRAP_RESAMPLES, len(per_seed_confusion)))
    sampled = per_seed_confusion[draws].sum(axis=1)
    tp = sampled[:, 1, 1].astype(np.float64)
    fp = sampled[:, :, 1].sum(axis=1) - tp
    fn = sampled[:, 1, :].sum(axis=1) - tp
    precision = np.divide(tp, tp + fp, out=np.zeros_like(tp), where=(tp + fp) > 0)
    recall = np.divide(tp, tp + fn, out=np.zeros_like(tp), where=(tp + fn) > 0)
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros_like(tp),
        where=(precision + recall) > 0,
    )
    return {
        "precision": tuple(np.percentile(precision, [2.5, 97.5]).tolist()),
        "recall": tuple(np.percentile(recall, [2.5, 97.5]).tolist()),
        "f1": tuple(np.percentile(f1, [2.5, 97.5]).tolist()),
    }


def _bootstrap_mean(
    values: np.ndarray, rng: np.random.Generator
) -> tuple[float, float]:
    values = np.asarray(values, dtype=np.float64)
    if not len(values):
        return 0.0, 0.0
    draws = rng.integers(0, len(values), size=(BOOTSTRAP_RESAMPLES, len(values)))
    means = values[draws].mean(axis=1)
    return tuple(np.percentile(means, [2.5, 97.5]).tolist())


def _paired_comparisons(
    seed_metric_values: dict[tuple[int, str, str], np.ndarray],
    blast_values: dict[tuple[int, str], np.ndarray],
    normal_values: dict[tuple[int, str], np.ndarray],
    rng_bootstrap: np.random.Generator,
    rng_permutation: np.random.Generator,
) -> list[dict[str, Any]]:
    families = {
        "macro_f1": lambda condition, method: seed_metric_values[(condition, method, "macro_f1")],
        "blast_as_progressive_rate": lambda condition, method: blast_values[(condition, method)],
        "progressive_recall": lambda condition, method: seed_metric_values[(condition, method, "progressive_recall")],
        "normal_false_alarms_per_hour": lambda condition, method: normal_values[(condition, method)],
    }
    rows: list[dict[str, Any]] = []
    for family, get_values in families.items():
        family_rows = []
        for condition_index, condition_name in enumerate(CONDITION_NAMES):
            rule_values = get_values(condition_index, "rule")
            supervised_values = get_values(condition_index, "supervised")
            difference = supervised_values - rule_values
            observed = float(np.mean(difference))
            signs = rng_permutation.choice(
                np.asarray([-1.0, 1.0]),
                size=(PERMUTATION_RESAMPLES, len(difference)),
            )
            permuted = np.mean(signs * difference[None, :], axis=1)
            p_value = (
                int(np.count_nonzero(np.abs(permuted) >= abs(observed))) + 1
            ) / (PERMUTATION_RESAMPLES + 1)
            draws = rng_bootstrap.integers(
                0,
                len(difference),
                size=(BOOTSTRAP_RESAMPLES, len(difference)),
            )
            bootstrap_means = difference[draws].mean(axis=1)
            ci_low, ci_high = np.percentile(bootstrap_means, [2.5, 97.5])
            family_rows.append({
                "metric_family": family,
                "condition_index": condition_index,
                "condition_name": condition_name,
                "method_a": "supervised",
                "method_b": "rule",
                "mean_difference_a_minus_b": observed,
                "ci95_low": float(ci_low),
                "ci95_high": float(ci_high),
                "p_value": p_value,
                "resamples": PERMUTATION_RESAMPLES,
                "seed_count": len(difference),
                "denominator": (
                    "seed-level macro-F1"
                    if family == "macro_f1"
                    else "seed-level blast episode rate"
                    if family == "blast_as_progressive_rate"
                    else "seed-level progressive recall"
                    if family == "progressive_recall"
                    else "seed-level normal false alarms/hour"
                ),
            })
        adjusted = _holm_adjust([float(row["p_value"]) for row in family_rows])
        for row, adjusted_p in zip(family_rows, adjusted):
            row["holm_adjusted_p_value"] = adjusted_p
            rows.append(row)
    return rows


def _holm_adjust(p_values: list[float]) -> list[float]:
    order = np.argsort(p_values)
    adjusted = np.empty(len(p_values), dtype=np.float64)
    previous = 0.0
    count = len(p_values)
    for rank, index in enumerate(order):
        value = min(1.0, (count - rank) * p_values[index])
        previous = max(previous, value)
        adjusted[index] = previous
    return adjusted.tolist()


def _write_paired_tests(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError("paired test results are empty")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_figures(
    output_dir: Path,
    truth: np.ndarray,
    node_mask: np.ndarray,
    class_predictions: dict[str, np.ndarray],
    binary_predictions: dict[str, np.ndarray],
    report: dict[str, Any],
    examples: dict[str, EpisodeV2],
) -> None:
    for method in CLASS_METHODS:
        confusion = report["class_confusions"][(0, method)].sum(axis=0)
        _plot_confusion(
            confusion,
            CLASS_NAMES_V2,
            PREDICTION_LABELS if method == "supervised" else CLASS_NAMES_V2,
            output_dir / f"confusion_{method}.png",
            f"{method.replace('_', ' ').title()} v2",
        )
    for method in ("isolation_forest", "current_system"):
        confusion = report["binary_confusions"][(0, method)].sum(axis=0)
        _plot_confusion(
            confusion,
            ("other/normal", "blast/progressive"),
            ("other/normal", "blast/progressive"),
            output_dir / f"confusion_{method}.png",
            f"{method.replace('_', ' ').title()} binary comparison",
        )
    _plot_examples(examples, output_dir / "example_signals.png")
    _plot_sensitivity(report, output_dir / "sensitivity_sweep.png")
    _plot_blast_rates(report, output_dir / "blast_as_progressive_ci.png")


def _plot_confusion(
    matrix: np.ndarray,
    true_labels: tuple[str, ...],
    predicted_labels: tuple[str, ...],
    output: Path,
    title: str,
) -> None:
    figure, axis = plt.subplots(figsize=(8, 6))
    image = axis.imshow(matrix, cmap="Blues")
    axis.set_xticks(range(len(predicted_labels)), predicted_labels, rotation=35, ha="right")
    axis.set_yticks(range(len(true_labels)), true_labels)
    axis.set_xlabel("Predicted")
    axis.set_ylabel("True")
    axis.set_title(title)
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axis.text(column, row, str(int(matrix[row, column])), ha="center", va="center")
    figure.colorbar(image, ax=axis, label="Inference windows")
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def _plot_examples(examples: dict[str, EpisodeV2], output: Path) -> None:
    figure, axes = plt.subplots(3, 2, figsize=(12, 10))
    cases = (
        ("blast_impulse", "BLAST_TRANSIENT"),
        ("progressive_single", "PROGRESSIVE_TILT_PROXY"),
        ("phone_like_vibration", "OTHER_TRANSIENT_OR_NORMAL"),
    )
    for row_index, (scenario, title) in enumerate(cases):
        episode = examples[scenario]
        axes[row_index, 0].plot(
            episode.minutes,
            episode.tilt_degrees[:, 0, 0],
            label="tilt x",
        )
        axes[row_index, 0].plot(
            episode.minutes,
            episode.tilt_degrees[:, 0, 1],
            label="tilt y",
            alpha=0.75,
        )
        axes[row_index, 0].set_title(f"{title}: slow tilt")
        axes[row_index, 0].set_xlabel("Simulated minutes")
        axes[row_index, 0].set_ylabel("Degrees")
        axes[row_index, 0].legend()
        axes[row_index, 1].plot(
            episode.waveform_time_seconds,
            episode.vibration,
            label="vibration (normalized simulation units)",
        )
        axes[row_index, 1].set_title(f"{title}: transient window")
        axes[row_index, 1].set_xlabel("Seconds from event")
        axes[row_index, 1].set_ylabel("Normalized simulation units")
        axes[row_index, 1].legend()
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def _plot_sensitivity(report: dict[str, Any], output: Path) -> None:
    conditions = list(CONDITION_NAMES)
    figure, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    for method in CLASS_METHODS:
        macro = []
        progressive_recall = []
        for condition_index in range(len(conditions)):
            matrix = report["class_confusions"][(condition_index, method)].sum(axis=0)
            macro.append(_macro_f1_from_confusion(matrix))
            rows = [
                row for row in report["class_metrics"]
                if row["condition_index"] == condition_index
                and row["method"] == method
                and row["class"] == "PROGRESSIVE_TILT_PROXY"
            ]
            progressive_recall.append(rows[0]["recall"])
        axes[0].plot(range(len(conditions)), macro, marker="o", label=method)
        axes[1].plot(range(len(conditions)), progressive_recall, marker="o", label=method)
    axes[0].set_ylabel("Macro-F1")
    axes[0].set_title("Class-aware sensitivity and held-out shifted condition")
    axes[1].set_ylabel("Progressive-tilt recall")
    axes[1].set_xlabel("Frozen condition")
    axes[1].set_xticks(range(len(conditions)), conditions, rotation=45, ha="right")
    for axis in axes:
        axis.set_ylim(0, 1.02)
        axis.grid(True, alpha=0.3)
        axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def _plot_blast_rates(report: dict[str, Any], output: Path) -> None:
    figure, axis = plt.subplots(figsize=(14, 6))
    conditions = list(CONDITION_NAMES)
    x = np.arange(len(conditions))
    offsets = {"rule": -0.15, "supervised": 0.15}
    for method in CLASS_METHODS:
        for scenario, linestyle in (
            ("blast_impulse", "-"),
            ("blast_tilt_recovery", "--"),
        ):
            selected = [
                row for row in report["blast_rates"]
                if row["method"] == method and row["scenario"] == scenario
            ]
            selected.sort(key=lambda row: row["condition_index"])
            position = x + offsets[method]
            axis.errorbar(
                position,
                [row["rate"] for row in selected],
                yerr=[
                    np.asarray([row["rate"] - row["ci_low"] for row in selected]),
                    np.asarray([row["ci_high"] - row["rate"] for row in selected]),
                ],
                marker="o",
                linestyle=linestyle,
                capsize=2,
                label=f"{method}: {scenario}",
            )
    axis.set_xticks(x, conditions, rotation=45, ha="right")
    axis.set_ylabel("Blast episodes classified as progressive")
    axis.set_ylim(0, 1.02)
    axis.set_title("Blast-as-progressive episode rate with 95% seed-bootstrap intervals")
    axis.grid(True, axis="y", alpha=0.3)
    axis.legend(fontsize=8, ncol=2)
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def _write_analysis(
    path: Path,
    report: dict[str, Any],
    metadata: dict[str, Any],
) -> None:
    lines = [
        "# Confirmatory analysis v2",
        "",
        "## Scope",
        "",
        "All analyzed records are generated simulation data under the frozen v2 protocol. "
        "The progressive-tilt label is a proxy, not verified mine subsidence. "
        "Public particle-velocity data were used only as context for plausible source "
        "duration/frequency scales and were not calibrated to node units.",
        "",
        f"Protocol SHA-256: `{metadata['protocol_sha256']}`.",
        f"Run revision: `{metadata['code_revision']}`. "
        f"Prediction rows: {metadata['prediction_rows_written']}; "
        f"recorded losses: {metadata['loss_count']}.",
        "The source of window-level observations and predictions is "
        "`docs/evaluation/confirmatory_v2/results.csv`; paired comparisons are in "
        "`docs/evaluation/confirmatory_v2/paired_tests.csv`.",
        "",
        "## Per-class results",
        "",
        "The table reports each class-aware method, condition, and class. Confidence "
        "intervals are percentile intervals from the frozen seed-level bootstrap.",
        "",
        "| Condition | Method | Class | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) | Support |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in report["class_metrics"]:
        lines.append(
            f"| {row['condition_name']} | {row['method']} | {row['class']} | "
            f"{_fmt_ci(row['precision'], row['precision_ci_low'], row['precision_ci_high'])} | "
            f"{_fmt_ci(row['recall'], row['recall_ci_low'], row['recall_ci_high'])} | "
            f"{_fmt_ci(row['f1'], row['f1_ci_low'], row['f1_ci_high'])} | "
            f"{row['support']} |"
        )
    lines.extend([
        "",
        "## Binary event-detection comparison",
        "",
        "For a common binary task, positive means the frozen truth class is blast or "
        "progressive tilt; the other/normal class is negative. Legacy methods remain "
        "binary detectors and are not assigned event-category outputs.",
        "",
        "| Condition | Method | Precision (95% CI) | Recall (95% CI) | F1 (95% CI) | Positive support |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for row in report["binary_metrics"]:
        lines.append(
            f"| {row['condition_name']} | {row['method']} | "
            f"{_fmt_ci(row['precision'], row['precision_ci_low'], row['precision_ci_high'])} | "
            f"{_fmt_ci(row['recall'], row['recall_ci_low'], row['recall_ci_high'])} | "
            f"{_fmt_ci(row['f1'], row['f1_ci_low'], row['f1_ci_high'])} | {row['support']} |"
        )
    lines.extend([
        "",
        "## Blast-as-progressive results",
        "",
        "Each rate is the fraction of blast episodes with any post-onset window "
        "classified as progressive; the denominator is shown explicitly.",
        "",
        "| Condition | Method | Blast scenario | Episodes classified as progressive | Rate (95% CI) |",
        "|---|---|---|---:|---:|",
    ])
    for row in report["blast_rates"]:
        lines.append(
            f"| {row['condition_name']} | {row['method']} | {row['scenario']} | "
            f"{row['false_progressive_episodes']}/{row['episodes']} | "
            f"{_fmt_ci(row['rate'], row['ci_low'], row['ci_high'])} |"
        )
    lines.extend([
        "",
        "## Progressive detection delay",
        "",
        "Censored nodes are assigned the full post-onset observation interval for "
        "the mean-delay summary and are counted separately.",
        "",
        "| Condition | Method | Scenario | Mean delay minutes (95% CI) | Detected / total nodes | Censored nodes |",
        "|---|---|---|---:|---:|",
    ])
    for row in report["progressive_delays"]:
        lines.append(
            f"| {row['condition_name']} | {row['method']} | {row['scenario']} | "
            f"{_fmt_ci(row['mean_delay_minutes'], row['ci_low'], row['ci_high'])} | "
            f"{row['detected_nodes']}/{row['total_nodes']} | {row['censored_nodes']} |"
        )
    lines.extend([
        "",
        "## Non-blast scenario false classifications",
        "",
        "Each denominator is the inference windows whose true class differs from "
        "the false predicted class in that named scenario.",
        "",
        "| Condition | Method | Scenario | False blast / eligible windows | False progressive / eligible windows |",
        "|---|---|---|---:|---:|---:|",
    ])
    false_index: dict[tuple[int, str, str, str], dict[str, Any]] = {}
    for row in report["scenario_false_classes"]:
        false_index[(row["condition_index"], row["method"], row["scenario"], row["false_class"])] = row
    for condition_index, condition_name in enumerate(CONDITION_NAMES):
        for method in CLASS_METHODS:
            for scenario in (
                "normal",
                "phone_like_vibration",
                "nonblast_impulse",
                "accel_vibration_without_tilt",
                "stuck_sensor",
                "progressive_correlated",
                "progressive_single",
            ):
                blast = false_index[(condition_index, method, scenario, "BLAST_TRANSIENT")]
                progressive = false_index[(condition_index, method, scenario, "PROGRESSIVE_TILT_PROXY")]
                lines.append(
                    f"| {condition_name} | {method} | {scenario} | "
                    f"{blast['prediction_count']}/{blast['inference_count']} | "
                    f"{progressive['prediction_count']}/{progressive['inference_count']} |"
                )
    lines.extend([
        "",
        "## Normal false alarms",
        "",
        "Per-hour values divide event-class predictions in normal-only inference "
        "windows by the observed normal exposure; interval estimates resample seeds.",
        "",
        "| Condition | Method | False windows | Exposure hours | False alarms/hour (95% CI) |",
        "|---|---|---:|---:|---:|",
    ])
    for row in report["normal_false_alarms"]:
        lines.append(
            f"| {row['condition_name']} | {row['method']} | {row['false_alarm_windows']} | "
            f"{row['exposure_hours']:.1f} | "
            f"{_fmt_ci(row['false_alarms_per_hour'], row['ci_low'], row['ci_high'])} |"
        )
    lines.extend([
        "",
        "## Paired tests",
        "",
        "Paired differences are supervised minus rule. Each family applies Holm "
        "adjustment across frozen conditions. The 95% intervals are seed-level "
        "bootstrap intervals; p-values use the add-one permutation correction.",
        "",
        "| Family | Condition | Mean difference | 95% CI | Raw p | Holm p | Seeds |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for row in report["paired_tests"]:
        lines.append(
            f"| {row['metric_family']} | {row['condition_name']} | "
            f"{row['mean_difference_a_minus_b']:.6g} | "
            f"[{row['ci95_low']:.6g}, {row['ci95_high']:.6g}] | "
            f"{row['p_value']:.6g} | {row['holm_adjusted_p_value']:.6g} | "
            f"{row['seed_count']} |"
        )
    lines.extend([
        "",
        "## Rule baseline compared with the supervised classifier",
        "",
        "Both models use the same frozen class labels and evaluation windows. "
        "The following point-metric comparisons cover every frozen condition:",
        "",
    ])
    macro_scores = {
        (condition_index, method): _macro_f1_from_confusion(
            report["class_confusions"][(condition_index, method)].sum(axis=0)
        )
        for condition_index in range(len(CONDITION_NAMES))
        for method in CLASS_METHODS
    }
    for condition_index, condition_name in enumerate(CONDITION_NAMES):
        rule_score = macro_scores[(condition_index, "rule")]
        supervised_score = macro_scores[(condition_index, "supervised")]
        difference = rule_score - supervised_score
        if np.isclose(difference, 0.0, atol=1e-12):
            comparison = "point macro-F1 matched"
        elif difference > 0:
            comparison = f"rule point macro-F1 was higher by {difference:.6g}"
        else:
            comparison = f"supervised point macro-F1 was higher by {abs(difference):.6g}"
        lines.append(
            f"- `{condition_name}`: rule {rule_score:.6g}, supervised "
            f"{supervised_score:.6g}; {comparison}."
        )
    lines.extend([
        "",
        "Held-out shifted-condition changes from default (shifted minus default):",
    ])
    for method in CLASS_METHODS:
        default = macro_scores[(0, method)]
        shifted = macro_scores[(13, method)]
        default_progressive = next(
            row["recall"] for row in report["class_metrics"]
            if row["condition_index"] == 0
            and row["method"] == method
            and row["class"] == "PROGRESSIVE_TILT_PROXY"
        )
        shifted_progressive = next(
            row["recall"] for row in report["class_metrics"]
            if row["condition_index"] == 13
            and row["method"] == method
            and row["class"] == "PROGRESSIVE_TILT_PROXY"
        )
        lines.append(
            f"- `{method}` macro-F1: {default:.6g} to {shifted:.6g} "
            f"(change {shifted - default:+.6g}); progressive recall: "
            f"{default_progressive:.6g} to {shifted_progressive:.6g} "
            f"(change {shifted_progressive - default_progressive:+.6g})."
        )
    lines.extend([
        "",
        "No threshold or model was refitted on the shifted condition. All output "
        "figures are generated from the same saved result arrays: "
        "`confusion_rule.png`, "
        "`confusion_supervised.png`, `confusion_isolation_forest.png`, "
        "`confusion_current_system.png`, `example_signals.png`, "
        "`sensitivity_sweep.png`, and `blast_as_progressive_ci.png`.",
        "",
        "## Losses and limits",
        "",
        "`losses.csv` records zero episode/window losses for this run. This benchmark "
        "does not test the built hardware, establish a sensor transfer function, or "
        "validate mine-site performance. The output is simulation-only.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _fmt_ci(value: float, low: float, high: float) -> str:
    return f"{value:.4f} [{low:.4f}, {high:.4f}]"


def _verified_protocol_hash() -> str:
    manifest = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    actual = hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
    expected = manifest.get("sha256")
    if manifest.get("algorithm") != "SHA-256" or actual != expected:
        raise RuntimeError(
            f"v2 protocol freeze mismatch: expected {expected}, computed {actual}"
        )
    return actual


def _git_revision() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
