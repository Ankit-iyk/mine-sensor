"""Remove duplicate telemetry and smooth noisy numeric readings."""


def remove_duplicates(readings: list[dict]) -> list[dict]:
	"""Return the first reading for each node and timestamp pair."""
	seen: set[tuple[object, object]] = set()
	unique_readings = []
	for reading in readings:
		identity = (reading.get("node_id"), reading.get("timestamp"))
		if identity in seen:
			continue
		seen.add(identity)
		unique_readings.append(reading)
	return unique_readings


def moving_average(values: list[float], window_size: int = 3) -> list[float]:
	"""Return trailing moving averages with one output for each input value."""
	if window_size < 1:
		raise ValueError("window_size must be at least 1")
	if not values:
		return []

	averages = []
	for index in range(len(values)):
		window_start = max(0, index - window_size + 1)
		window = values[window_start:index + 1]
		averages.append(sum(window) / len(window))
	return averages


def filter_readings(
	readings: list[dict], field: str, window_size: int = 3
) -> list[dict]:
	"""Deduplicate readings and add a smoothed field named ``<field>_smooth``."""
	unique_readings = remove_duplicates(readings)
	smoothed_values = moving_average(
		[reading[field] for reading in unique_readings], window_size
	)
	filtered_readings = []
	for reading, smoothed_value in zip(unique_readings, smoothed_values):
		filtered_reading = dict(reading)
		filtered_reading[f"{field}_smooth"] = smoothed_value
		filtered_readings.append(filtered_reading)
	return filtered_readings
