"""
Risk trajectory engine.
Tracks a node's risk score over time and classifies whether it is
rising, falling, or holding steady.
"""

from collections import deque

_HISTORY_WINDOW = 10
_RISING_SLOPE_THRESHOLD = 3.0
_FALLING_SLOPE_THRESHOLD = -3.0

_risk_history = {}


def reset_trajectory_state():
	"""Clears all per-node risk history. Mainly useful for tests."""
	_risk_history.clear()


def _get_history(node_id: str) -> deque:
	if node_id not in _risk_history:
		_risk_history[node_id] = deque(maxlen=_HISTORY_WINDOW)
	return _risk_history[node_id]


def _slope(values: list) -> float:
	"""Simple average step-to-step change across the window."""
	if len(values) < 2:
		return 0.0
	differences = [values[index] - values[index - 1] for index in range(1, len(values))]
	return sum(differences) / len(differences)


def track_trajectory(node_id: str, risk_score: float) -> dict:
	"""
	Records the current risk score and classifies its trajectory.
	"""
	history = _get_history(node_id)
	history.append(risk_score)

	values = list(history)
	slope = _slope(values)

	if slope >= _RISING_SLOPE_THRESHOLD:
		trajectory = "RISING"
	elif slope <= _FALLING_SLOPE_THRESHOLD:
		trajectory = "FALLING"
	else:
		trajectory = "STEADY"

	return {
		"trajectory": trajectory,
		"slope": slope,
		"history": values,
	}
