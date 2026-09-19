"""
Generates normal (stable) telemetry sequences for a single node.
Baseline data — used to train fingerprints and Isolation Forest.
"""

import random
from datetime import datetime, timedelta


def generate_normal_sequence(node_id="N01", zone_id="Z01", count=50, start_time=None):
    """
    Returns a list of `count` telemetry dicts representing stable, low-risk readings.
    Small random jitter simulates real sensor noise.
    """
    if start_time is None:
        start_time = datetime(2026, 9, 19, 9, 0, 0)

    readings = []
    base_tilt_x = 1.2
    base_tilt_y = 1.0
    base_vibration = 0.015

    for i in range(count):
        ts = (start_time + timedelta(seconds=i)).isoformat() + "Z"
        readings.append({
            "node_id": node_id,
            "zone_id": zone_id,
            "timestamp": ts,
            "ax": round(random.uniform(-0.05, 0.05), 3),
            "ay": round(random.uniform(-0.05, 0.05), 3),
            "az": round(random.uniform(0.95, 1.0), 3),
            "tilt_x": round(base_tilt_x + random.uniform(-0.3, 0.3), 2),
            "tilt_y": round(base_tilt_y + random.uniform(-0.3, 0.3), 2),
            "vibration": round(max(0.0, base_vibration + random.uniform(-0.014, 0.014)), 3),
        })
    return readings
