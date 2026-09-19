"""
Anomaly detection interface.
Combines Isolation Forest scoring with fingerprint deviation into a single
call, matching the signature the master pipeline expects.
"""

from ai_engine.anomaly.isolation_forest import (
	DEFAULT_MODEL_PATH,
	load_model,
	score_sample,
)
from ai_engine.fingerprint.fingerprint import deviation_score

_model_cache = {}


def _get_model(model_path: str = DEFAULT_MODEL_PATH):
	"""Loads and caches the trained Isolation Forest model."""
	if model_path not in _model_cache:
		_model_cache[model_path] = load_model(model_path)
	return _model_cache[model_path]


def reset_model_cache():
	"""Clears the cached model. Mainly useful for tests."""
	_model_cache.clear()


def detect_anomaly(features: dict, node_id: str, model_path: str = DEFAULT_MODEL_PATH) -> dict:
	"""
	Runs Isolation Forest scoring and combines it with the node fingerprint's
	deviation score.
	"""
	model = _get_model(model_path)
	isolation_result = score_sample(model, features)
	deviation = deviation_score(
		node_id,
		tilt_magnitude=features["tilt_magnitude"],
		vibration_value=features["vibration_intensity"],
	)

	return {
		"score": isolation_result["raw_score"],
		"is_anomalous": isolation_result["is_anomalous"],
		"tilt_deviation": deviation["tilt_deviation"],
		"vibration_deviation": deviation["vibration_deviation"],
	}
