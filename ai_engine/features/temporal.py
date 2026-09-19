"""
Temporal feature extraction.
Computes windowed means, trend, and persistence over a time-stamped
sequence of values (e.g. tilt_magnitude or vibration_intensity).

History format: list of (datetime, value) tuples, oldest to newest.
"""

from datetime import datetime, timedelta


def _window_values(history: list, reference_time: datetime, seconds: float) -> list:
	cutoff = reference_time - timedelta(seconds=seconds)
	return [value for timestamp, value in history if cutoff <= timestamp <= reference_time]


def windowed_mean(history: list, reference_time: datetime, seconds: float) -> float:
	"""Mean of all values within `seconds` before reference_time."""
	values = _window_values(history, reference_time, seconds)
	if not values:
		return 0.0
	return sum(values) / len(values)


def five_min_mean(history: list, reference_time: datetime) -> float:
	return windowed_mean(history, reference_time, 5 * 60)


def fifteen_min_mean(history: list, reference_time: datetime) -> float:
	return windowed_mean(history, reference_time, 15 * 60)


def one_hour_mean(history: list, reference_time: datetime) -> float:
	return windowed_mean(history, reference_time, 60 * 60)


def trend_slope(history: list) -> float:
	"""
	Simple linear regression slope of value vs. time (in seconds since first point).
	Positive = rising trend, negative = falling, 0 = flat or insufficient data.
	"""
	if len(history) < 2:
		return 0.0

	first_time = history[0][0]
	xs = [(timestamp - first_time).total_seconds() for timestamp, _ in history]
	ys = [value for _, value in history]

	count = len(xs)
	mean_x = sum(xs) / count
	mean_y = sum(ys) / count

	numerator = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(count))
	denominator = sum((x - mean_x) ** 2 for x in xs)

	if denominator == 0:
		return 0.0
	return numerator / denominator


def persistence(is_anomalous_history: list) -> float:
	"""
	Fraction of recent readings flagged anomalous (True/False list).
	Returns 0.0 for empty input.
	"""
	if not is_anomalous_history:
		return 0.0
	return sum(1 for flag in is_anomalous_history if flag) / len(is_anomalous_history)


def rate_of_change(history: list) -> float:
	"""
	Change in value per second between the first and last point in history.
	Returns 0.0 if fewer than 2 points or zero elapsed time.
	"""
	if len(history) < 2:
		return 0.0
	first_time, first_value = history[0]
	last_time, last_value = history[-1]
	elapsed = (last_time - first_time).total_seconds()
	if elapsed == 0:
		return 0.0
	return (last_value - first_value) / elapsed
