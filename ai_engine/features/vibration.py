"""
Vibration feature extraction.
Converts raw vibration readings into engineered features for anomaly detection.
"""

import math


def vibration_intensity(vibration_value: float) -> float:
	"""
	Raw vibration reading, treated as intensity directly.
	Kept as its own function so the definition of "intensity" can evolve
	(e.g. combine with accel magnitude) without touching callers.
	"""
	return vibration_value


def vibration_event_count(history: list, threshold: float = 5.0) -> int:
	"""
	Counts how many readings in `history` exceed `threshold`.
	An "event" = a vibration spike above the normal noise floor.
	"""
	return sum(1 for value in history if value > threshold)


def vibration_frequency(history: list, threshold: float = 5.0) -> float:
	"""
	Fraction of readings in the window that count as vibration events.
	Returns 0.0 for an empty history.
	"""
	if not history:
		return 0.0
	return vibration_event_count(history, threshold) / len(history)


def vibration_rate(history: list) -> float:
	"""
	Rate of change of vibration between the last two readings.
	Returns 0.0 if fewer than 2 points.
	"""
	if len(history) < 2:
		return 0.0
	return history[-1] - history[-2]


def rolling_vibration_mean(history: list) -> float:
	"""Mean vibration over the given window."""
	if not history:
		return 0.0
	return sum(history) / len(history)


def rolling_vibration_std(history: list) -> float:
	"""Standard deviation of vibration over the given window."""
	n = len(history)
	if n < 2:
		return 0.0
	mean = rolling_vibration_mean(history)
	variance = sum((value - mean) ** 2 for value in history) / n
	return math.sqrt(variance)
