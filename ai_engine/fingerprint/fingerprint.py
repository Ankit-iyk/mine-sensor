"""
Ground Stability Fingerprint.
Stores per-node baseline behaviour (tilt, vibration) and scores how
unusual a live reading is relative to that node's own history.
"""

from ai_engine.fingerprint.baseline import compute_baseline, update_baseline_incremental


_fingerprints = {}


def reset_fingerprints():
	"""Clears all stored fingerprints. Mainly useful for tests."""
	_fingerprints.clear()


def build_fingerprint(node_id: str, tilt_history: list, vibration_history: list) -> dict:
	"""
	Builds an initial fingerprint for a node from a batch of normal-behaviour
	readings (e.g. from the simulator's generate_normal_sequence).
	"""
	fingerprint = {
		"tilt": compute_baseline(tilt_history),
		"vibration": compute_baseline(vibration_history),
		"count": len(tilt_history),
	}
	_fingerprints[node_id] = fingerprint
	return fingerprint


def update_fingerprint(node_id: str, tilt_magnitude: float, vibration_value: float) -> dict:
	"""
	Incrementally updates an existing fingerprint with one new live reading.
	If no fingerprint exists yet for this node, creates one from this single reading.
	"""
	if node_id not in _fingerprints:
		return build_fingerprint(node_id, [tilt_magnitude], [vibration_value])

	fingerprint = _fingerprints[node_id]
	fingerprint["tilt"] = update_baseline_incremental(
		fingerprint["tilt"], tilt_magnitude, fingerprint["count"]
	)
	fingerprint["vibration"] = update_baseline_incremental(
		fingerprint["vibration"], vibration_value, fingerprint["count"]
	)
	fingerprint["count"] += 1
	return fingerprint


def get_fingerprint(node_id: str) -> dict:
	"""Returns the stored fingerprint for a node, or None if it doesn't exist yet."""
	return _fingerprints.get(node_id)


def deviation_score(node_id: str, tilt_magnitude: float, vibration_value: float) -> dict:
	"""
	Scores how unusual the given live values are compared to the node's
	own fingerprint, in units of standard deviations (z-score style).
	Returns 0.0 deviation for a node with no fingerprint yet (nothing to compare).
	"""
	fingerprint = get_fingerprint(node_id)
	if fingerprint is None:
		return {"tilt_deviation": 0.0, "vibration_deviation": 0.0}

	tilt_std = fingerprint["tilt"]["std"] or 1e-6
	vibration_std = fingerprint["vibration"]["std"] or 1e-6

	tilt_deviation = abs(tilt_magnitude - fingerprint["tilt"]["mean"]) / tilt_std
	vibration_deviation = abs(vibration_value - fingerprint["vibration"]["mean"]) / vibration_std

	return {"tilt_deviation": tilt_deviation, "vibration_deviation": vibration_deviation}
