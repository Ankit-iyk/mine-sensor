"""
Validates raw telemetry before it enters the ML pipeline.
Ensures sensor faults are not mistaken for mine anomalies.
"""

REQUIRED_FIELDS = ["node_id", "zone_id", "timestamp", "ax", "ay", "az", "tilt_x", "tilt_y", "vibration"]

VALID_RANGES = {
    "ax": (-2.0, 2.0),
    "ay": (-2.0, 2.0),
    "az": (-2.0, 2.0),
    "tilt_x": (-90.0, 90.0),
    "tilt_y": (-90.0, 90.0),
    "vibration": (0.0, 1.0),
}


class ValidationError(Exception):
    pass


def validate(telemetry: dict) -> dict:
    """
    Validates a single telemetry reading.
    Returns the telemetry unchanged if valid, raises ValidationError if not.
    """
    _check_required_fields(telemetry)
    _check_ranges(telemetry)
    _check_timestamp(telemetry)
    return telemetry


def _check_required_fields(telemetry: dict):
    missing = [f for f in REQUIRED_FIELDS if f not in telemetry or telemetry[f] is None]
    if missing:
        raise ValidationError(f"Missing required fields: {missing}")


def _check_ranges(telemetry: dict):
    for field, (low, high) in VALID_RANGES.items():
        value = telemetry.get(field)
        if value is None:
            continue
        if not (low <= value <= high):
            raise ValidationError(
                f"Field '{field}' value {value} out of physical range [{low}, {high}]"
            )


def _check_timestamp(telemetry: dict):
    ts = telemetry.get("timestamp")
    if not isinstance(ts, str) or len(ts) < 10:
        raise ValidationError(f"Invalid timestamp: {ts}")
