import os

import pytest

from ai_engine.anomaly.isolation_forest import (
    load_model,
    save_model,
    score_sample,
    train_isolation_forest,
)
from ai_engine.pipeline.build_training_data import FEATURE_COLUMNS, build_normal_feature_dataset


def test_train_isolation_forest_on_normal_data():
    dataset = build_normal_feature_dataset(node_ids=["N01"], count_per_node=30)
    model = train_isolation_forest(dataset)
    assert model is not None


def test_train_isolation_forest_empty_raises():
    with pytest.raises(ValueError):
        train_isolation_forest([])


def test_save_and_load_model(tmp_path):
    dataset = build_normal_feature_dataset(node_ids=["N01"], count_per_node=30)
    model = train_isolation_forest(dataset)
    path = str(tmp_path / "test_model.joblib")

    save_model(model, path)
    assert os.path.exists(path)

    loaded = load_model(path)
    assert loaded is not None


def test_score_sample_normal_reading_scores_low_anomaly():
    dataset = build_normal_feature_dataset(node_ids=["N01"], count_per_node=50)
    model = train_isolation_forest(dataset)

    result = score_sample(model, dataset[0])
    assert "is_anomalous" in result
    assert "raw_score" in result


def test_score_sample_extreme_outlier_flagged_anomalous():
    dataset = build_normal_feature_dataset(node_ids=["N01"], count_per_node=50)
    model = train_isolation_forest(dataset)

    inlier = next(
        row for row in dataset
        if model.predict([[row.get(column, 0.0) for column in FEATURE_COLUMNS]])[0] == 1
    )
    inlier_score = score_sample(model, inlier)["raw_score"]

    outlier = dict(inlier)
    for column in FEATURE_COLUMNS:
        outlier[column] = 1_000_000.0

    result = score_sample(model, outlier)
    assert result["is_anomalous"] is True
    assert result["raw_score"] < inlier_score
