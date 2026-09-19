"""
Generates a sequence where risk climbs steadily over time.
Tests the temporal engine's ESCALATING state and trend_slope feature.
"""

from datetime import datetime, timedelta

from simulator.normal import generate_normal_sequence


def generate_escalating_event(node_id="N01", zone_id="Z01", count=50, onset_at=15, start_time=None):
    if start_time is None:
        start_time = datetime(2026, 9, 19, 9, 0, 0)

    readings = generate_normal_sequence(node_id, zone_id, onset_at, start_time)

    for i in range(onset_at, count):
        ts = (start_time + timedelta(seconds=i)).isoformat() + "Z"
        step = i - onset_at
        readings.append({
            "node_id": node_id,
            "zone_id": zone_id,
            "timestamp": ts,
            "ax": round(0.05 + step * 0.01, 3),
            "ay": round(0.04 + step * 0.01, 3),
            "az": round(0.95 - step * 0.005, 3),
            "tilt_x": round(1.5 + step * 0.4, 2),
            "tilt_y": round(1.2 + step * 0.35, 2),
            "vibration": round(min(1.0, 0.03 + step * 0.015), 3),
        })
    return readings
