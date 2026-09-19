"""
Builds a normal-behaviour training dataset for Isolation Forest.
Generates synthetic normal telemetry across multiple nodes, runs it through
Module 1 (preprocessing) and Module 2 (feature extraction), and saves the
resulting feature vectors as a CSV for training.
"""

import csv
import os

from ai_engine.features.extractor import extract_features, reset_state
from ai_engine.preprocessing.filtering import filter_readings, remove_duplicates
from ai_engine.preprocessing.normalization import normalize
from ai_engine.preprocessing.validation import validate
from simulator.normal import generate_normal_sequence

DEFAULT_NODES = ["N01", "N02", "N03", "N04", "N05"]
DEFAULT_COUNT_PER_NODE = 200
SMOOTHED_FIELDS = ["tilt_x", "tilt_y", "vibration"]

FEATURE_COLUMNS = [
    "tilt_magnitude", "tilt_deviation", "tilt_rate",
    "rolling_tilt_mean", "rolling_tilt_std",
    "vibration_intensity", "vibration_event_count", "vibration_frequency",
    "rolling_vibration_mean", "rolling_vibration_std",
    "trend_slope",
]


def _preprocess_batch(raw_sequence: list) -> list:
    """
    Runs one node's raw readings through validation, duplicate removal,
    per-field smoothing, and normalization — in that order, batch-wise.
    """
    validated = [validate(reading) for reading in raw_sequence]
    deduped = remove_duplicates(validated)

    smoothed = deduped
    for field in SMOOTHED_FIELDS:
        smoothed = filter_readings(smoothed, field)

    return [normalize(reading) for reading in smoothed]


def build_normal_feature_dataset(node_ids=None, count_per_node=DEFAULT_COUNT_PER_NODE):
    """
    Returns a list of feature dicts (each tagged with node_id) built from
    synthetic normal telemetry across the given nodes.
    """
    if node_ids is None:
        node_ids = DEFAULT_NODES

    reset_state()
    rows = []

    for node_id in node_ids:
        raw_sequence = generate_normal_sequence(node_id=node_id, count=count_per_node)
        preprocessed = _preprocess_batch(raw_sequence)

        for reading in preprocessed:
            features = extract_features(reading)
            features["node_id"] = node_id
            rows.append(features)

    return rows


def save_dataset_csv(rows: list, path: str = "ai_engine/models/normal_training_data.csv"):
    """Writes the feature rows to CSV for reuse in Isolation Forest training."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ["node_id"] + FEATURE_COLUMNS

    with open(path, "w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, 0.0) for key in fieldnames})

    return path


if __name__ == "__main__":
    dataset = build_normal_feature_dataset()
    output_path = save_dataset_csv(dataset)
    print(f"Generated {len(dataset)} normal feature rows -> {output_path}")
