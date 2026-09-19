"""
Temporal intelligence engine.
Classifies a node's recent anomaly behaviour into STABLE, TRANSIENT,
PERSISTENT, or ESCALATING based on anomaly history and trend.
"""

from collections import deque

_HISTORY_WINDOW = 10
_PERSISTENCE_THRESHOLD = 0.6
_ESCALATION_SLOPE_THRESHOLD = 0.5

_anomaly_history = {}


def reset_temporal_state():
	"""Clears all per-node temporal history. Mainly useful for tests."""
	_anomaly_history.clear()


def _get_history(node_id: str) -> deque:
	if node_id not in _anomaly_history:
		_anomaly_history[node_id] = deque(maxlen=_HISTORY_WINDOW)
	return _anomaly_history[node_id]


def classify_temporal_state(node_id: str, is_anomalous: bool, trend_slope: float) -> dict:
	"""
	Updates a node's anomaly history and classifies its temporal state.

	Returns the state, recent anomalous fraction, and supplied trend value.
	"""
	history = _get_history(node_id)
	history.append(is_anomalous)

	persistence = sum(1 for flag in history if flag) / len(history)

	if not is_anomalous and persistence < _PERSISTENCE_THRESHOLD:
		state = "STABLE"
	elif persistence >= _PERSISTENCE_THRESHOLD and trend_slope > _ESCALATION_SLOPE_THRESHOLD:
		state = "ESCALATING"
	elif persistence >= _PERSISTENCE_THRESHOLD:
		state = "PERSISTENT"
	else:
		state = "TRANSIENT"

	return {
		"state": state,
		"persistence": persistence,
		"trend": trend_slope,
	}
