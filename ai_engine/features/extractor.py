"""
Master feature extractor.
Combines tilt, vibration, and temporal features into a single call per telemetry reading.
Maintains a rolling per-node history so windowed/rate/trend features work correctly.
"""

from collections import deque
from datetime import datetime

from ai_engine.features.temporal import (
	fifteen_min_mean,
	five_min_mean,
	one_hour_mean,
	rate_of_change,
	trend_slope,
)
from ai_engine.features.tilt import (
	rolling_tilt_mean,
	rolling_tilt_std,
	tilt_acceleration,
	tilt_deviation,
	tilt_magnitude,
	tilt_rate,
)
from ai_engine.features.vibration import (
	rolling_vibration_mean,
	rolling_vibration_std,
	vibration_event_count,
	vibration_frequency,
	vibration_intensity,
	vibration_rate,
)

_HISTORY_WINDOW = 20

_node_state = {}


def _get_state(node_id: str) -> dict:
	if node_id not in _node_state:
		_node_state[node_id] = {
			"tilt_mag_history": deque(maxlen=_HISTORY_WINDOW),
			"tilt_rate_history": deque(maxlen=_HISTORY_WINDOW),
			"vibration_history": deque(maxlen=_HISTORY_WINDOW),
			"timestamped_tilt": deque(maxlen=_HISTORY_WINDOW),
		}
	return _node_state[node_id]


def reset_state():
	"""Clears all per-node history. Mainly useful for tests."""
	_node_state.clear()


def extract_features(telemetry: dict, baseline_tilt_mean: float = 0.0) -> dict:
	"""
	Extracts the full feature set for one telemetry reading.
	`telemetry` must already be validated/filtered/normalized (Module 1 output).
	`baseline_tilt_mean` comes from the node's Ground Stability Fingerprint
	(Module 3) — defaults to 0.0 until a fingerprint exists.
	"""
	node_id = telemetry["node_id"]
	state = _get_state(node_id)

	timestamp = datetime.fromisoformat(telemetry["timestamp"].replace("Z", "+00:00"))
	magnitude = tilt_magnitude(telemetry["tilt_x"], telemetry["tilt_y"])
	vibration = telemetry["vibration"]

	state["tilt_mag_history"].append(magnitude)
	state["vibration_history"].append(vibration)
	state["timestamped_tilt"].append((timestamp, magnitude))

	magnitude_history = list(state["tilt_mag_history"])
	vibration_history = list(state["vibration_history"])
	timestamped_tilt = list(state["timestamped_tilt"])

	tilt_change = tilt_rate(magnitude_history)
	state["tilt_rate_history"].append(tilt_change)
	rate_history = list(state["tilt_rate_history"])

	return {
		"tilt_magnitude": magnitude,
		"tilt_deviation": tilt_deviation(magnitude, baseline_tilt_mean),
		"tilt_rate": tilt_change,
		"tilt_acceleration": tilt_acceleration(rate_history),
		"rolling_tilt_mean": rolling_tilt_mean(magnitude_history),
		"rolling_tilt_std": rolling_tilt_std(magnitude_history),
		"vibration_intensity": vibration_intensity(vibration),
		"vibration_event_count": vibration_event_count(vibration_history),
		"vibration_frequency": vibration_frequency(vibration_history),
		"vibration_rate": vibration_rate(vibration_history),
		"rolling_vibration_mean": rolling_vibration_mean(vibration_history),
		"rolling_vibration_std": rolling_vibration_std(vibration_history),
		"five_min_mean": five_min_mean(timestamped_tilt, timestamp),
		"fifteen_min_mean": fifteen_min_mean(timestamped_tilt, timestamp),
		"one_hour_mean": one_hour_mean(timestamped_tilt, timestamp),
		"trend_slope": trend_slope(timestamped_tilt),
		"rate_of_change": rate_of_change(timestamped_tilt),
	}
