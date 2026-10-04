"""
SUBSENSE — Sensor Calibration, Magnitude & Failure Detection (Phase 3)

Provides numerically safe geometric magnitude calculations and checks for
hardware sensor failures (NaN, infinite, out-of-range, or frozen sensor data).
"""

import math
from typing import Any, Optional, Tuple
import numpy as np

# Physical bounds for MPU6050 & 10-bit vibration ADC
MAX_ACCEL_VAL = 25.0    # m/s^2 (MPU6050 configured for +/-16g)
MAX_TILT_VAL = 90.0     # degrees
MAX_VIB_VAL = 1023      # 10-bit ADC


def calculate_accel_magnitude(accel_x: float, accel_y: float, accel_z: float) -> float:
    """
    Calculate Euclidean acceleration magnitude:
        accel_magnitude = sqrt(accel_x^2 + accel_y^2 + accel_z^2)

    Numerically safe: handles float overflow/underflow and clamps negative radicals to 0.0.
    """
    sum_sq = float(accel_x)**2 + float(accel_y)**2 + float(accel_z)**2
    if math.isnan(sum_sq) or math.isinf(sum_sq):
        return 0.0
    return round(float(math.sqrt(max(0.0, sum_sq))), 4)


def calculate_tilt_magnitude(tilt_x: float, tilt_y: float) -> float:
    """
    Calculate Euclidean tilt magnitude:
        tilt_magnitude = sqrt(tilt_x^2 + tilt_y^2)

    Units: degrees.
    """
    sum_sq = float(tilt_x)**2 + float(tilt_y)**2
    if math.isnan(sum_sq) or math.isinf(sum_sq):
        return 0.0
    return round(float(math.sqrt(max(0.0, sum_sq))), 4)


def validate_sensor_data(
    accel_x: Any,
    accel_y: Any,
    accel_z: Any,
    tilt_x: Any,
    tilt_y: Any,
    vibration: Any,
    recent_tilt_magnitudes: Optional[list[float]] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate incoming sensor data for sensor failure conditions:
    1. NaN or Infinite values
    2. Physically impossible values beyond hardware limits
    3. Frozen sensor (flatlined readings across multiple consecutive samples)

    Returns
    -------
    (is_valid: bool, failure_reason: Optional[str])
    """
    values = [accel_x, accel_y, accel_z, tilt_x, tilt_y, vibration]
    
    # 1. NaN or Inf
    for v in values:
        if v is None:
            return False, "SENSOR_FAILURE_MISSING_VALUE"
        try:
            fv = float(v)
            if math.isnan(fv) or math.isinf(fv):
                return False, "SENSOR_FAILURE_NAN_OR_INF"
        except (ValueError, TypeError):
            return False, "SENSOR_FAILURE_NON_NUMERIC"

    # 2. Hardware range limits
    if abs(float(accel_x)) > MAX_ACCEL_VAL or abs(float(accel_y)) > MAX_ACCEL_VAL or abs(float(accel_z)) > MAX_ACCEL_VAL:
        return False, "SENSOR_FAILURE_ACCEL_OUT_OF_RANGE"

    if abs(float(tilt_x)) > MAX_TILT_VAL or abs(float(tilt_y)) > MAX_TILT_VAL:
        return False, "SENSOR_FAILURE_TILT_OUT_OF_RANGE"

    if float(vibration) < 0 or float(vibration) > MAX_VIB_VAL:
        return False, "SENSOR_FAILURE_VIBRATION_OUT_OF_RANGE"

    # 3. Frozen flatline sensor detection (if >= 15 consecutive identical readings)
    if recent_tilt_magnitudes and len(recent_tilt_magnitudes) >= 15:
        std = float(np.std(recent_tilt_magnitudes))
        if std < 1e-6:
            return False, "SENSOR_FAILURE_FROZEN_FLATLINE"

    return True, None


def is_sensor_failure(
    tilt_x: float,
    tilt_y: float,
    accel_z: float,
    vibration: int,
    accel_x: float = 0.0,
    accel_y: float = 0.0,
) -> bool:
    """
    Convenience boolean wrapper around validate_sensor_data.
    Returns True if any sensor failure condition is detected.
    """
    valid, _ = validate_sensor_data(
        accel_x=accel_x,
        accel_y=accel_y,
        accel_z=accel_z,
        tilt_x=tilt_x,
        tilt_y=tilt_y,
        vibration=vibration,
    )
    return not valid
