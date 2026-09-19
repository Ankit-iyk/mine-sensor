"""
Explainability engine.
Converts risk components, temporal state, and spatial correlation into
a human-readable summary and plain-language reasons.
"""

TILT_RISK_NOTABLE = 30.0
VIBRATION_RISK_NOTABLE = 30.0
PERSISTENCE_NOTABLE = 0.5
SPATIAL_CORRELATION_NOTABLE = 0.5


def generate_explanation(
	features: dict,
	anomaly: dict,
	temporal: dict,
	spatial: dict,
	risk: dict,
	zone_id: str = "",
) -> dict:
	"""Build a plain-language explanation for the current risk assessment."""
	reasons = []
	components = risk["components"]

	if components["tilt_risk"] >= TILT_RISK_NOTABLE:
		reasons.append("Tilt deviation is increasing")

	if components["vibration_risk"] >= VIBRATION_RISK_NOTABLE:
		reasons.append("Vibration activity is elevated")

	if temporal["state"] in ("PERSISTENT", "ESCALATING"):
		reasons.append("Abnormal behaviour is persistent")

	if spatial["correlation"] >= SPATIAL_CORRELATION_NOTABLE:
		reasons.append("Neighbouring nodes show correlated behaviour")

	if temporal["state"] == "ESCALATING":
		reasons.append("Risk trajectory is escalating")

	if not reasons:
		reasons.append("All readings within normal range")

	return {
		"summary": _build_summary(risk["state"], zone_id),
		"reasons": reasons,
	}


def _build_summary(risk_state: str, zone_id: str) -> str:
	zone_part = f" in Zone {zone_id}" if zone_id else ""

	if risk_state == "SAFE":
		return f"Conditions are stable{zone_part}"
	if risk_state == "WARNING":
		return f"Risk is increasing{zone_part}"
	return f"Critical risk detected{zone_part}"
