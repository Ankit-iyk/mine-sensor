"""
Tilt feature extraction.
Converts raw tilt_x/tilt_y readings into engineered features for anomaly detection.
"""

import math


def tilt_magnitude(tilt_x: float, tilt_y: float) -> float:
	"""Combined tilt magnitude from both axes."""
	return math.sqrt(tilt_x ** 2 + tilt_y ** 2)


def tilt_deviation(current_magnitude: float, baseline_mean: float) -> float:
	"""
	How far current tilt magnitude is from the node's normal baseline.
	baseline_mean comes from the Ground Stability Fingerprint (Module 3).
	Until a fingerprint exists, caller can pass 0 as a neutral baseline.
	"""
	return abs(current_magnitude - baseline_mean)


def tilt_rate(history: list) -> float:
	"""
	Rate of change of tilt magnitude between the last two readings.
	`history` is a list of tilt_magnitude values, oldest to newest.
	Returns 0.0 if fewer than 2 points.
	"""
	if len(history) < 2:
		return 0.0
	return history[-1] - history[-2]


def tilt_acceleration(rate_history: list) -> float:
	"""
	Rate of change of tilt_rate itself (second derivative).
	`rate_history` is a list of tilt_rate values, oldest to newest.
	"""
	if len(rate_history) < 2:
		return 0.0
	return rate_history[-1] - rate_history[-2]


def rolling_tilt_mean(history: list) -> float:
	"""Mean tilt magnitude over the given window."""
	if not history:
		return 0.0
	return sum(history) / len(history)


def rolling_tilt_std(history: list) -> float:
	"""Standard deviation of tilt magnitude over the given window."""
	n = len(history)
	if n < 2:
		return 0.0
	mean = rolling_tilt_mean(history)
	variance = sum((x - mean) ** 2 for x in history) / n
	return math.sqrt(variance)
