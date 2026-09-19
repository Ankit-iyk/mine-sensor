"""
Normalizes filtered telemetry into a consistent scale for downstream ML.
Final step of the preprocessing module.
"""


def normalize(telemetry: dict) -> dict:
	"""
	Returns a new dict with added *_norm fields (0-1 scaled).
	Does not mutate or remove the original raw fields.
	"""
	normalized = dict(telemetry)
	normalized["tilt_x_norm"] = _scale(telemetry["tilt_x"], -90, 90)
	normalized["tilt_y_norm"] = _scale(telemetry["tilt_y"], -90, 90)
	normalized["vibration_norm"] = _scale(telemetry["vibration"], 0, 100)
	return normalized


def _scale(value: float, low: float, high: float) -> float:
	if high == low:
		raise ValueError("Invalid scale range: high and low cannot be equal")
	return (value - low) / (high - low)
