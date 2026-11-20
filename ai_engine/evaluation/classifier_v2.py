"""Frozen rule baseline and calibrated lightweight classifier for v2."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable

import numpy as np
from scipy.special import logsumexp
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from ai_engine.evaluation.datasets_v2 import CLASS_NAMES_V2
from ai_engine.evaluation.features_v2 import (
    FEATURE_NAMES_V2,
    RULE_THRESHOLD_CANDIDATES_V2,
    feature_vector_v2,
)


@dataclass(frozen=True)
class RuleThresholdsV2:
    drift_slope: float
    cumulative_tilt: float
    persistence: float
    vibration_peak: float
    decay_seconds: float
    residual_tilt: float

    def as_dict(self) -> dict[str, float]:
        return {
            "drift_slope": self.drift_slope,
            "cumulative_tilt": self.cumulative_tilt,
            "persistence": self.persistence,
            "vibration_peak": self.vibration_peak,
            "decay_seconds": self.decay_seconds,
            "residual_tilt": self.residual_tilt,
        }


class RuleBaselineV2:
    def __init__(self, thresholds: RuleThresholdsV2):
        self.thresholds = thresholds

    def predict_one(self, features: dict[str, Any]) -> str:
        thresholds = self.thresholds
        persistence_map = features["persistence_by_cumulative_threshold"]
        if (
            float(features["drift_slope_degrees_per_hour"]) > thresholds.drift_slope
            and float(features["cumulative_tilt_magnitude_degrees"]) > thresholds.cumulative_tilt
            and float(persistence_map[thresholds.cumulative_tilt]) > thresholds.persistence
        ):
            return "PROGRESSIVE_TILT_PROXY"
        if (
            float(features["vibration_peak"]) > thresholds.vibration_peak
            and float(features["decay_missing"]) == 0.0
            and float(features["vibration_decay_seconds"]) < thresholds.decay_seconds
            and float(features["residual_tilt_magnitude_degrees"]) <= thresholds.residual_tilt
        ):
            return "BLAST_TRANSIENT"
        return "OTHER_TRANSIENT_OR_NORMAL"

    def predict(self, rows: Iterable[dict[str, Any]]) -> np.ndarray:
        return np.asarray([self.predict_one(row) for row in rows], dtype=object)


class SupervisedClassifierV2:
    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self.model = LogisticRegression(
            C=1.0,
            class_weight="balanced",
            max_iter=1000,
            random_state=0,
        )
        self.temperature = 1.0
        self._fitted = False

    def fit(self, training_rows: list[dict[str, Any]]) -> None:
        matrix = _matrix(training_rows)
        labels = np.asarray([row["class_label"] for row in training_rows], dtype=object)
        if set(labels) != set(CLASS_NAMES_V2):
            raise ValueError("training split must contain every v2 class")
        self.scaler.fit(matrix)
        self.model.fit(self.scaler.transform(matrix), labels)
        self._fitted = True

    def calibrate_temperature(self, calibration_rows: list[dict[str, Any]]) -> float:
        logits = self._logits(calibration_rows)
        labels = np.asarray([row["class_label"] for row in calibration_rows], dtype=object)
        class_indices = {label: index for index, label in enumerate(self.model.classes_)}
        targets = np.asarray([class_indices[str(label)] for label in labels], dtype=int)
        best_temperature = 0.50
        best_loss = float("inf")
        for temperature in (0.50, 0.75, 1.00, 1.50, 2.00):
            scaled = logits / temperature
            losses = logsumexp(scaled, axis=1) - scaled[np.arange(len(targets)), targets]
            mean_loss = float(np.mean(losses))
            if mean_loss < best_loss or (
                np.isclose(mean_loss, best_loss) and temperature > best_temperature
            ):
                best_loss = mean_loss
                best_temperature = temperature
        self.temperature = best_temperature
        return best_temperature

    def predict_one(self, features: dict[str, Any]) -> tuple[str, dict[str, float]]:
        probabilities = self.predict_proba([features])[0]
        best_index = int(np.argmax(probabilities))
        best_class = str(self.model.classes_[best_index])
        predicted = best_class if float(probabilities[best_index]) >= 0.50 else "UNKNOWN"
        return predicted, {
            str(label): float(probabilities[index])
            for index, label in enumerate(self.model.classes_)
        }

    def predict(self, rows: list[dict[str, Any]]) -> np.ndarray:
        probabilities = self.predict_proba(rows)
        best_indices = np.argmax(probabilities, axis=1)
        predictions = self.model.classes_[best_indices].astype(object)
        predictions[np.max(probabilities, axis=1) < 0.50] = "UNKNOWN"
        return predictions

    def predict_proba(self, rows: list[dict[str, Any]]) -> np.ndarray:
        logits = self._logits(rows) / self.temperature
        logits -= logsumexp(logits, axis=1, keepdims=True)
        return np.exp(logits)

    def _logits(self, rows: list[dict[str, Any]]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("v2 classifier must be fit before prediction")
        matrix = _matrix(rows)
        return np.asarray(
            self.model.decision_function(self.scaler.transform(matrix)),
            dtype=np.float64,
        )


def fit_rule_baseline_v2(
    calibration_rows: list[dict[str, Any]],
) -> tuple[RuleBaselineV2, dict[str, float]]:
    if not calibration_rows:
        raise ValueError("calibration rows cannot be empty")
    labels = np.asarray([row["class_label"] for row in calibration_rows], dtype=object)
    if set(labels) != set(CLASS_NAMES_V2):
        raise ValueError("calibration split must contain every v2 class")

    candidates = [
        RuleThresholdsV2(*values)
        for values in product(
            RULE_THRESHOLD_CANDIDATES_V2["drift_slope"],
            RULE_THRESHOLD_CANDIDATES_V2["cumulative_tilt"],
            RULE_THRESHOLD_CANDIDATES_V2["persistence"],
            RULE_THRESHOLD_CANDIDATES_V2["vibration_peak"],
            RULE_THRESHOLD_CANDIDATES_V2["decay_seconds"],
            RULE_THRESHOLD_CANDIDATES_V2["residual_tilt"],
        )
    ]
    normal_rows = [row for row in calibration_rows if row["scenario"] == "normal"]
    blast_rows = [
        row for row in calibration_rows
        if row["scenario"] in {"blast_impulse", "blast_tilt_recovery"}
    ]
    best_key: tuple[float, ...] | None = None
    best_model: RuleBaselineV2 | None = None
    best_metrics: dict[str, float] = {}
    for thresholds in candidates:
        model = RuleBaselineV2(thresholds)
        predictions = model.predict(calibration_rows)
        macro_f1 = _macro_f1(labels, predictions, CLASS_NAMES_V2)
        blast_as_progressive = _blast_episode_rate(blast_rows, model)
        normal_false_alarms_per_hour = _normal_false_alarms_per_hour(normal_rows, model)
        tie_key = (
            -macro_f1,
            blast_as_progressive,
            normal_false_alarms_per_hour,
            thresholds.drift_slope,
            thresholds.cumulative_tilt,
            thresholds.persistence,
            thresholds.vibration_peak,
            thresholds.decay_seconds,
            thresholds.residual_tilt,
        )
        if best_key is None or tie_key < best_key:
            best_key = tie_key
            best_model = model
            best_metrics = {
                "macro_f1": macro_f1,
                "blast_as_progressive_rate": blast_as_progressive,
                "normal_false_alarms_per_hour": normal_false_alarms_per_hour,
            }
    if best_model is None:
        raise RuntimeError("no rule threshold candidate was evaluated")
    return best_model, best_metrics


def _matrix(rows: list[dict[str, Any]]) -> np.ndarray:
    matrix = np.asarray([feature_vector_v2(row) for row in rows], dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != len(FEATURE_NAMES_V2):
        raise ValueError("v2 feature matrix has an unexpected shape")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("v2 feature matrix contains non-finite values")
    return matrix


def _macro_f1(
    truth: np.ndarray, predicted: np.ndarray, classes: tuple[str, ...]
) -> float:
    values = []
    for label in classes:
        tp = int(np.sum((truth == label) & (predicted == label)))
        fp = int(np.sum((truth != label) & (predicted == label)))
        fn = int(np.sum((truth == label) & (predicted != label)))
        denominator = 2 * tp + fp + fn
        values.append(2.0 * tp / denominator if denominator else 0.0)
    return float(np.mean(values))


def _blast_episode_rate(rows: list[dict[str, Any]], model: RuleBaselineV2) -> float:
    if not rows:
        return 0.0
    by_episode: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in rows:
        by_episode.setdefault((int(row["seed"]), str(row["scenario"])), []).append(row)
    false_episodes = 0
    for episode_rows in by_episode.values():
        if np.any(model.predict(episode_rows) == "PROGRESSIVE_TILT_PROXY"):
            false_episodes += 1
    return false_episodes / len(by_episode)


def _normal_false_alarms_per_hour(
    rows: list[dict[str, Any]], model: RuleBaselineV2
) -> float:
    if not rows:
        return 0.0
    predictions = model.predict(rows)
    false_windows = int(
        np.sum(
            np.isin(
                predictions,
                ("BLAST_TRANSIENT", "PROGRESSIVE_TILT_PROXY"),
            )
        )
    )
    exposure_hours = sum(
        1.0 / 4.0 for row in rows if row["scenario"] == "normal"
    )
    return false_windows / exposure_hours if exposure_hours else 0.0
