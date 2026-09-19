"""
Isolation Forest training and persistence.
Trains ONLY on normal-behaviour data (per plan Section 10) — never on
danger/anomaly examples, since this is unsupervised outlier detection.
"""

import os

import joblib
from sklearn.ensemble import IsolationForest

from ai_engine.pipeline.build_training_data import FEATURE_COLUMNS

DEFAULT_MODEL_PATH = "ai_engine/models/isolation_forest.joblib"

DEFAULT_PARAMS = {
	"n_estimators": 100,
	"contamination": 0.05,
	"random_state": 42,
}


def train_isolation_forest(feature_rows: list, params: dict = None) -> IsolationForest:
	"""
	Trains an Isolation Forest on a list of feature dicts (from
	build_normal_feature_dataset). Only FEATURE_COLUMNS are used —
	node_id and any extra keys are ignored.
	"""
	if not feature_rows:
		raise ValueError("Cannot train on empty feature dataset")

	model = IsolationForest(**(params or DEFAULT_PARAMS))
	model.fit(_rows_to_matrix(feature_rows))
	return model


def _rows_to_matrix(feature_rows: list) -> list:
	"""Converts feature dicts into rows ordered by FEATURE_COLUMNS."""
	return [[row.get(column, 0.0) for column in FEATURE_COLUMNS] for row in feature_rows]


def save_model(model: IsolationForest, path: str = DEFAULT_MODEL_PATH) -> str:
	os.makedirs(os.path.dirname(path), exist_ok=True)
	joblib.dump(model, path)
	return path


def load_model(path: str = DEFAULT_MODEL_PATH) -> IsolationForest:
	if not os.path.exists(path):
		raise FileNotFoundError(f"No trained model found at {path}. Run training first.")
	return joblib.load(path)


def score_sample(model: IsolationForest, feature_dict: dict) -> dict:
	"""
	Scores one feature dict against a trained model.
	sklearn's IsolationForest predicts -1 for outliers and 1 for inliers.
	"""
	matrix = _rows_to_matrix([feature_dict])
	prediction = model.predict(matrix)[0]
	raw_score = model.decision_function(matrix)[0]

	return {
		"is_anomalous": bool(prediction == -1),
		"raw_score": float(raw_score),
	}


if __name__ == "__main__":
	from ai_engine.pipeline.build_training_data import build_normal_feature_dataset

	dataset = build_normal_feature_dataset()
	model = train_isolation_forest(dataset)
	path = save_model(model)
	print(f"Trained Isolation Forest on {len(dataset)} normal samples -> {path}")
