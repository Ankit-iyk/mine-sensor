"""
Computes baseline statistics (mean, std) for a node from historical
normal-behaviour readings. Used to build/update a node's fingerprint.
"""

import math


def compute_baseline(values: list) -> dict:
	"""
	Returns {"mean": float, "std": float} for a list of numeric values.
	Requires at least 1 value; std is 0.0 with fewer than 2 values.
	"""
	if not values:
		raise ValueError("Cannot compute baseline from empty history")

	count = len(values)
	mean = sum(values) / count

	if count < 2:
		standard_deviation = 0.0
	else:
		variance = sum((value - mean) ** 2 for value in values) / count
		standard_deviation = math.sqrt(variance)

	return {"mean": mean, "std": standard_deviation}


def update_baseline_incremental(existing: dict, new_value: float, count: int) -> dict:
	"""
	Incrementally updates a mean using Welford-style running average,
	so the fingerprint can evolve without storing full history forever.
	`count` is the number of samples that produced `existing` (before this one).
	"""
	old_mean = existing["mean"]
	new_count = count + 1
	new_mean = old_mean + (new_value - old_mean) / new_count

	old_std = existing["std"]
	new_std = old_std + (abs(new_value - old_mean) - old_std) / new_count

	return {"mean": new_mean, "std": new_std}
