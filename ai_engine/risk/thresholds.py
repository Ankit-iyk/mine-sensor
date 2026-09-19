"""
Configurable weights and thresholds for the Risk Engine.
Prototype values are not certified mine-safety limits.
"""

TILT_WEIGHT = 0.40
VIBRATION_WEIGHT = 0.30
TREND_WEIGHT = 0.20
ANOMALY_WEIGHT = 0.10

SAFE_MAX = 30
WARNING_MAX = 70

TILT_DEVIATION_CAP = 10.0
VIBRATION_INTENSITY_CAP = 50.0
TREND_SLOPE_CAP = 5.0
