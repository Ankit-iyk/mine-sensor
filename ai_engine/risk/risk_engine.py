"""
Risk Engine.
Combines tilt, vibration, trend, and anomaly signals into a single
0-100 risk score, then classifies it as SAFE / WARNING / DANGER.
"""

from ai_engine.risk.thresholds import (
	ANOMALY_WEIGHT,
	SAFE_MAX,
	TILT_DEVIATION_CAP,
	TILT_WEIGHT,
	TREND_SLOPE_CAP,
	TREND_WEIGHT,
	VIBRATION_INTENSITY_CAP,
	VIBRATION_WEIGHT,
	WARNING_MAX,
)


def _normalize(value: float, cap: float) -> float:
	"""Scales a raw value to 0-100, clamped at the given cap."""
	if cap == 0:
		return 0.0
	return min((abs(value) / cap) * 100, 100.0)


def calculate_risk(features: dict, anomaly: dict) -> dict:
	"""Compute weighted risk components, score, and state bucket."""
	tilt_risk = _normalize(anomaly["tilt_deviation"], TILT_DEVIATION_CAP)
	vibration_risk = _normalize(features["vibration_intensity"], VIBRATION_INTENSITY_CAP)
	trend_risk = _normalize(features["trend_slope"], TREND_SLOPE_CAP)
	anomaly_risk = 100.0 if anomaly["is_anomalous"] else 0.0

	score = (
		TILT_WEIGHT * tilt_risk
		+ VIBRATION_WEIGHT * vibration_risk
		+ TREND_WEIGHT * trend_risk
		+ ANOMALY_WEIGHT * anomaly_risk
	)

	return {
		"score": round(score, 2),
		"state": _classify(score),
		"components": {
			"tilt_risk": round(tilt_risk, 2),
			"vibration_risk": round(vibration_risk, 2),
			"trend_risk": round(trend_risk, 2),
			"anomaly_risk": round(anomaly_risk, 2),
		},
	}


def _classify(score: float) -> str:
	if score <= SAFE_MAX:
		return "SAFE"
	if score <= WARNING_MAX:
		return "WARNING"
	return "DANGER"
