"""Train and evaluate the Isolation Forest on backend-extracted features."""

from __future__ import annotations

import math
import random
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
SIMULATOR_ROOT = REPO_ROOT / "simulator"
for import_path in (str(BACKEND_ROOT), str(SIMULATOR_ROOT)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from ai_engine.anomaly.isolation_forest import (
    DEFAULT_PARAMS,
    save_model,
    train_isolation_forest,
)
from ai_engine.pipeline.build_training_data import FEATURE_COLUMNS
from app.config import settings
from app.ingestion.schemas import TelemetryReading
from app.ml.loader import get_detector
from app.processing.baseline import NodeBaselineTracker
from app.processing.buffer import NodeBuffer
from app.processing.features import FeatureExtractor
from app.processing.filters import NodeTiltFilter
from app.processing.schemas import ProcessedSample
from ai_engine.adapter import AIEngineDetector
from simulator.node import SensorNode
from simulator.scenarios import ALL_NODES, SCENARIOS

READINGS_PER_TRAINING_NODE = 2_000
TRAINING_SEEDS = (1, 2, 3, 4, 5)
HELD_OUT_SEEDS = (101, 102, 103)
EVALUATION_SCENARIOS = (
    "normal",
    "vibration_event",
    "gradual_tilt",
    "persistent_anomaly",
    "multi_node_event",
)
MODEL_PATH = REPO_ROOT / "ai_engine" / "models" / "isolation_forest.joblib"


def _feature_dicts(
    node_id: str,
    zone_id: str,
    scenario_name: str,
    readings_count: int,
) -> list[dict]:
    """Generate simulator readings and extract features without DB or MQTT."""
    node = SensorNode(node_id=node_id, zone_id=zone_id)
    node.set_scenario(scenario_name)
    tilt_filter = NodeTiltFilter(
        node_id=node_id,
        q_angle=settings.kalman_q_angle,
        q_rate=settings.kalman_q_rate,
        r_measure=settings.kalman_r_measure,
    )
    buffer = NodeBuffer(node_id=node_id, max_size=settings.feature_window_size)
    baseline_tracker = NodeBaselineTracker(node_id=node_id)
    extractor = FeatureExtractor()
    start = datetime.now(timezone.utc)
    rows = []

    for step in range(readings_count):
        payload = node.generate_reading()
        payload["timestamp"] = (start + timedelta(seconds=step)).isoformat()
        reading = TelemetryReading.model_validate(payload)

        estimate_x, estimate_y = tilt_filter.filter_sample(
            raw_tilt_x=reading.tilt_x,
            raw_tilt_y=reading.tilt_y,
            timestamp=reading.timestamp,
        )
        sample = ProcessedSample(
            timestamp=reading.timestamp,
            raw_tilt_x=reading.tilt_x,
            raw_tilt_y=reading.tilt_y,
            tilt_x=estimate_x.angle,
            tilt_y=estimate_y.angle,
            rate_x=estimate_x.rate,
            rate_y=estimate_y.rate,
            tilt_magnitude=math.sqrt(estimate_x.angle**2 + estimate_y.angle**2),
            vibration=reading.vibration,
            vibration_norm=min(1.0, max(0.0, reading.vibration / 1023.0)),
        )
        buffer.add_sample(sample)
        baseline_tracker.observe(
            tilt_x=estimate_x.angle,
            tilt_y=estimate_y.angle,
            vibration=float(reading.vibration),
        )
        features = extractor.extract(
            buffer,
            baseline_tracker=baseline_tracker,
            zone_id=reading.zone_id,
        )
        if features is not None:
            rows.append(features.to_dict())

    return rows


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def _train_detector() -> AIEngineDetector:
    mapper = AIEngineDetector()
    training_rows = []

    for seed in TRAINING_SEEDS:
        _set_seed(seed)
        for node_id, zone_id in ALL_NODES.items():
            features = _feature_dicts(
                node_id=node_id,
                zone_id=zone_id,
                scenario_name=SCENARIOS["normal"].node_assignments[node_id],
                readings_count=READINGS_PER_TRAINING_NODE,
            )
            training_rows.extend(mapper._map_features(row) for row in features)

    model = train_isolation_forest(training_rows, params=DEFAULT_PARAMS)
    model_path = save_model(model, str(MODEL_PATH))
    print(f"Training rows: {len(training_rows)}")
    print(f"Model saved: {model_path}")
    print("Training feature statistics (min / mean / max):")
    for column in FEATURE_COLUMNS:
        values = np.asarray([row[column] for row in training_rows], dtype=float)
        print(
            f"  {column}: "
            f"{values.min():.6f} / {values.mean():.6f} / {values.max():.6f}"
        )

    detector = get_detector()
    if not isinstance(detector, AIEngineDetector):
        raise RuntimeError(
            f"Expected AIEngineDetector after training, got {type(detector).__name__}"
        )
    return detector


def _evaluation_node(scenario_name: str) -> tuple[str, str]:
    scenario = SCENARIOS[scenario_name]
    node_id = next(
        node
        for node, assigned_scenario in scenario.node_assignments.items()
        if assigned_scenario == scenario_name
    )
    return node_id, ALL_NODES[node_id]


def _evaluate(detector: AIEngineDetector) -> None:
    outcomes: dict[str, list[dict]] = {
        scenario: [] for scenario in EVALUATION_SCENARIOS
    }
    deviations: dict[str, dict[str, list[float]]] = {
        scenario: {"tilt_deviation": [], "baseline_deviation": []}
        for scenario in EVALUATION_SCENARIOS
    }

    for scenario_index, scenario_name in enumerate(EVALUATION_SCENARIOS):
        node_id, zone_id = _evaluation_node(scenario_name)
        for seed in HELD_OUT_SEEDS:
            _set_seed(seed + scenario_index)
            rows = _feature_dicts(
                node_id=node_id,
                zone_id=zone_id,
                scenario_name=scenario_name,
                readings_count=200,
            )
            for features in rows:
                outcomes[scenario_name].append(detector.predict(features))
                for key in ("tilt_deviation", "baseline_deviation"):
                    deviations[scenario_name][key].append(float(features[key]))

    print("Held-out evaluation (seeds 101-103; fractions / anomaly_score min, mean, max):")
    print(
        "| Scenario | Features | NORMAL | MICRO_ANOMALY | ANOMALOUS "
        "| Score min | Score mean | Score max |"
    )
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for scenario_name in EVALUATION_SCENARIOS:
        predictions = outcomes[scenario_name]
        states = Counter(item["state"] for item in predictions)
        scores = np.asarray(
            [item["anomaly_score"] for item in predictions], dtype=float
        )
        count = len(predictions)
        fractions = {
            state: states.get(state, 0) / count if count else 0.0
            for state in ("NORMAL", "MICRO_ANOMALY", "ANOMALOUS")
        }
        score_min, score_mean, score_max = (
            (float(scores.min()), float(scores.mean()), float(scores.max()))
            if count
            else (float("nan"),) * 3
        )
        print(
            f"| {scenario_name} | {count} | {fractions['NORMAL']:.4f} "
            f"| {fractions['MICRO_ANOMALY']:.4f} | {fractions['ANOMALOUS']:.4f} "
            f"| {score_min:.6f} | {score_mean:.6f} | {score_max:.6f} |"
        )

    print("Held-out deviation percentiles (50th / 95th / 99th):")
    print("| Scenario | Feature | P50 | P95 | P99 |")
    print("|---|---|---:|---:|---:|")
    for scenario_name in (
        "normal",
        "gradual_tilt",
        "vibration_event",
        "persistent_anomaly",
    ):
        for key in ("tilt_deviation", "baseline_deviation"):
            values = deviations[scenario_name][key]
            p50, p95, p99 = np.percentile(values, [50, 95, 99])
            print(
                f"| {scenario_name} | {key} | {p50:.6f} "
                f"| {p95:.6f} | {p99:.6f} |"
            )


def main() -> None:
    detector = _train_detector()
    _evaluate(detector)


if __name__ == "__main__":
    main()
