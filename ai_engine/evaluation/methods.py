"""Comparable detector implementations fitted only on the training partition."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from ai_engine.adapter import AIEngineDetector
from ai_engine.anomaly.isolation_forest import train_isolation_forest
from ai_engine.pipeline.build_training_data import FEATURE_COLUMNS


METHODS = (
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
ABLATIONS = (
    "no_baseline_deviation",
    "no_temporal_persistence",
    "no_spatial_corroboration",
    "no_tilt_features",
    "no_vibration_features",
    "no_acceleration_features",
    "no_temporal_features",
)

TILT_FEATURES = (
    "tilt_magnitude", "tilt_deviation", "tilt_rate",
    "rolling_mean_tilt", "rolling_std_tilt",
)
VIBRATION_FEATURES = (
    "vibration_intensity", "vibration_event_count", "vibration_frequency",
    "rolling_mean_vib", "rolling_std_vib",
)
ACCELERATION_FEATURES = ("accel_magnitude", "accel_mean", "accel_std", "accel_peak")
TEMPORAL_FEATURES = ("trend_slope", "persistence")


class MethodSuite:
    """Fit learned methods on one shared normal-only seed partition."""

    def __init__(self, training_rows: list[dict[str, Any]]) -> None:
        if len(training_rows) < 20:
            raise ValueError("at least 20 training feature rows are required")
        matrix = _matrix(training_rows)
        self.isolation_forest = train_isolation_forest(
            training_rows,
            params={"n_estimators": 100, "contamination": 0.05, "random_state": 71},
        )
        self.scaler = StandardScaler().fit(matrix)
        scaled = self.scaler.transform(matrix)
        self.one_class_svm = OneClassSVM(kernel="rbf", gamma="scale", nu=0.05).fit(scaled)
        self.local_outlier_factor = LocalOutlierFactor(
            n_neighbors=min(35, max(5, len(training_rows) - 1)),
            contamination=0.05,
            novelty=True,
        ).fit(scaled)
        self.deviation_mean = float(np.mean([row["tilt_deviation"] for row in training_rows]))
        self.deviation_std = max(
            0.01,
            float(np.std([row["tilt_deviation"] for row in training_rows], ddof=1)),
        )
        self.current_adapter = AIEngineDetector()
        with tempfile.TemporaryDirectory(prefix="subsense-eval-") as temp_dir:
            model_path = Path(temp_dir) / "isolation_forest.joblib"
            import joblib
            joblib.dump(self.isolation_forest, model_path)
            self.current_adapter.load(str(model_path))
        parity_rows = training_rows[:5]
        batch_scores, batch_alerts = self._current_predictions(parity_rows)
        individual = [self.current_adapter.predict(row) for row in parity_rows]
        if not np.allclose(batch_scores, [item["anomaly_score"] for item in individual]):
            raise RuntimeError("vectorized current-system scores disagree with AIEngineDetector")
        if not np.array_equal(batch_alerts, [item["state"] == "ANOMALOUS" for item in individual]):
            raise RuntimeError("vectorized current-system states disagree with AIEngineDetector")

    def predict(self, rows: list[dict[str, Any]], method: str, ablation: str | None = None) -> tuple[np.ndarray, np.ndarray]:
        if not rows:
            return np.asarray([], dtype=float), np.asarray([], dtype=bool)
        if method == "fixed_tilt_threshold":
            scores = np.asarray([row["tilt_deviation"] for row in rows], dtype=float)
            return scores, scores >= 0.5
        if method == "baseline_z_score":
            scores = np.asarray([
                (row["tilt_deviation"] - self.deviation_mean) / self.deviation_std
                for row in rows
            ])
            return scores, scores >= 3.0
        if method in ("ewma", "cusum"):
            scores = self._sequential_scores(rows, method)
            threshold = 0.3 if method == "ewma" else 0.8
            return scores, scores >= threshold

        variant_rows = [_ablate_row(row, ablation) for row in rows] if ablation else rows
        matrix = _matrix(variant_rows)
        if method == "isolation_forest":
            scores = -self.isolation_forest.decision_function(matrix)
            alerts = self.isolation_forest.predict(matrix) == -1
            return scores, alerts
        if method == "one_class_svm":
            scaled = self.scaler.transform(matrix)
            scores = -self.one_class_svm.decision_function(scaled)
            return scores, self.one_class_svm.predict(scaled) == -1
        if method == "local_outlier_factor":
            scaled = self.scaler.transform(matrix)
            scores = -self.local_outlier_factor.decision_function(scaled)
            return scores, self.local_outlier_factor.predict(scaled) == -1
        if method in ("current_system", "current_system_spatial"):
            scores, alerts = self._current_predictions(variant_rows)
            if method == "current_system":
                return scores, alerts
            return scores, self._persist_and_corroborate(rows, alerts, ablation)
        raise ValueError(f"Unknown evaluation method: {method}")

    def predict_ablation(self, rows: list[dict[str, Any]], ablation: str) -> tuple[np.ndarray, np.ndarray]:
        """Run the current system + spatial method with one component removed."""
        if ablation not in ABLATIONS:
            raise ValueError(f"Unknown ablation: {ablation}")
        if ablation in ("no_temporal_persistence", "no_spatial_corroboration"):
            return self._component_ablation(rows, ablation)
        return self.predict(rows, "current_system_spatial", ablation=ablation)

    def _component_ablation(self, rows: list[dict[str, Any]], ablation: str) -> tuple[np.ndarray, np.ndarray]:
        base_rows = [_ablate_row(row, None) for row in rows]
        scores, raw = self._current_predictions(base_rows)
        if ablation == "no_temporal_persistence":
            return scores, np.logical_or(raw, _spatial_only(rows, raw))
        return scores, _persist(raw, rows, minimum=3)

    def _sequential_scores(self, rows: list[dict[str, Any]], method: str) -> np.ndarray:
        ordered = sorted(range(len(rows)), key=lambda idx: (
            str(rows[idx]["node_id"]), rows[idx]["timestamp"]
        ))
        result = np.zeros(len(rows), dtype=float)
        state: dict[str, float] = defaultdict(float)
        for idx in ordered:
            row = rows[idx]
            node_id = str(row["node_id"])
            deviation = max(0.0, float(row["tilt_deviation"]))
            if method == "ewma":
                state[node_id] = 0.2 * deviation + 0.8 * state[node_id]
            else:
                state[node_id] = max(0.0, state[node_id] + deviation - 0.08)
            result[idx] = state[node_id]
        return result

    def _current_predictions(self, rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
        """Batch-equivalent of AIEngineDetector.predict for evaluation throughput."""
        matrix = _matrix(rows)
        predicted = self.isolation_forest.predict(matrix) == -1
        raw_scores = self.isolation_forest.decision_function(matrix)
        scores = np.clip(0.5 - raw_scores, 0.0, 1.0)
        deviations = np.asarray([float(row.get("tilt_deviation", 0.0)) for row in rows])
        baseline = np.asarray([float(row.get("baseline_deviation", 0.0)) for row in rows])
        alerts = predicted & ((deviations >= 0.11) | (baseline >= 0.11))
        return scores, alerts

    def _persist_and_corroborate(
        self,
        rows: list[dict[str, Any]],
        raw_alerts: np.ndarray,
        ablation: str | None,
    ) -> np.ndarray:
        if ablation == "no_temporal_persistence":
            persisted = raw_alerts
        else:
            persisted = _persist(raw_alerts, rows, minimum=3)
        if ablation == "no_spatial_corroboration":
            return persisted
        return np.logical_or(persisted, _spatial_only(rows, raw_alerts))


def _persist(alerts: np.ndarray, rows: list[dict[str, Any]], minimum: int) -> np.ndarray:
    result = np.zeros(len(rows), dtype=bool)
    previous_node: str | None = None
    streak = 0
    for idx in sorted(range(len(rows)), key=lambda i: (rows[i]["node_id"], rows[i]["timestamp"])):
        node_id = str(rows[idx]["node_id"])
        if node_id != previous_node:
            previous_node = node_id
            streak = 0
        streak = streak + 1 if alerts[idx] else 0
        result[idx] = streak >= minimum
    return result


def _spatial_only(rows: list[dict[str, Any]], alerts: np.ndarray) -> np.ndarray:
    by_step: dict[tuple[str, int], list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        by_step[(str(row["zone_id"]), int(row["step"]))].append(idx)
    result = np.zeros(len(rows), dtype=bool)
    for indices in by_step.values():
        positives = [idx for idx in indices if alerts[idx]]
        if len(positives) >= 2:
            result[positives] = True
    return result


def _ablate_row(row: dict[str, Any], ablation: str | None) -> dict[str, Any]:
    copied = dict(row)
    if ablation == "no_baseline_deviation":
        copied["tilt_deviation"] = 0.0
        copied["baseline_deviation"] = 0.0
    elif ablation == "no_tilt_features":
        for key in TILT_FEATURES:
            copied[key] = 0.0
        copied["baseline_deviation"] = 0.0
    elif ablation == "no_vibration_features":
        for key in VIBRATION_FEATURES:
            copied[key] = 0.0
    elif ablation == "no_acceleration_features":
        for key in ACCELERATION_FEATURES:
            copied[key] = 0.0
    elif ablation == "no_temporal_features":
        for key in TEMPORAL_FEATURES:
            copied[key] = 0.0
    return copied


def _matrix(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray(
        [[float(row.get(column, 0.0)) for column in FEATURE_COLUMNS] for row in rows],
        dtype=float,
    )
