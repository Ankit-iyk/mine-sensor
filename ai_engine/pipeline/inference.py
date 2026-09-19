"""
Master inference pipeline.
The single entry point the backend calls for one telemetry reading.
"""

from ai_engine.anomaly.detector import detect_anomaly
from ai_engine.anomaly.isolation_forest import DEFAULT_MODEL_PATH
from ai_engine.explainability.explanation import generate_explanation
from ai_engine.features.extractor import extract_features
from ai_engine.fingerprint.fingerprint import update_fingerprint
from ai_engine.intelligence.spatial import spatial_correlation
from ai_engine.intelligence.temporal import classify_temporal_state
from ai_engine.intelligence.trajectory import track_trajectory
from ai_engine.preprocessing.normalization import normalize
from ai_engine.preprocessing.validation import validate
from ai_engine.risk.risk_engine import calculate_risk

_anomalous_nodes = set()
DEFAULT_SPATIAL_RADIUS = 15.0


def reset_pipeline_state():
	"""Clears cross-request anomalous-node state. Mainly useful for tests."""
	_anomalous_nodes.clear()


def analyze_telemetry(
	telemetry: dict,
	model_path: str = DEFAULT_MODEL_PATH,
	spatial_radius: float = DEFAULT_SPATIAL_RADIUS,
) -> dict:
	"""Run one telemetry reading through the complete AI inference pipeline."""
	node_id = telemetry["node_id"]
	zone_id = telemetry["zone_id"]

	validated = validate(telemetry)
	normalized = normalize(validated)
	features = extract_features(normalized)

	update_fingerprint(
		node_id,
		tilt_magnitude=features["tilt_magnitude"],
		vibration_value=features["vibration_intensity"],
	)

	anomaly = detect_anomaly(features, node_id=node_id, model_path=model_path)
	if anomaly["is_anomalous"]:
		_anomalous_nodes.add(node_id)
	else:
		_anomalous_nodes.discard(node_id)

	temporal = classify_temporal_state(
		node_id,
		is_anomalous=anomaly["is_anomalous"],
		trend_slope=features["trend_slope"],
	)
	spatial = spatial_correlation(
		node_id,
		anomalous_nodes=_anomalous_nodes,
		radius=spatial_radius,
	)
	risk = calculate_risk(features, anomaly)
	trajectory = track_trajectory(node_id, risk["score"])
	explanation = generate_explanation(
		features, anomaly, temporal, spatial, risk, zone_id=zone_id
	)

	return {
		"node_id": node_id,
		"zone_id": zone_id,
		"features": features,
		"anomaly": anomaly,
		"temporal": temporal,
		"spatial": spatial,
		"risk": risk,
		"trajectory": trajectory,
		"explanation": explanation,
	}
