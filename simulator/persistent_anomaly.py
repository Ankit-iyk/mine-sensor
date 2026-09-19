"""
Generates a sequence where a node becomes anomalous and STAYS anomalous
(not escalating, not transient) — tests the temporal engine's PERSISTENT state.
"""

from datetime import datetime, timedelta

from simulator.normal import generate_normal_sequence


def generate_persistent_anomaly(node_id="N01", zone_id="Z01", count=50, onset_at=20, start_time=None):
    if start_time is None:
        start_time = datetime(2026, 9, 19, 9, 0, 0)

    readings = generate_normal_sequence(node_id, zone_id, onset_at, start_time)

    for i in range(onset_at, count):
        ts = (start_time + timedelta(seconds=i)).isoformat() + "Z"
        readings.append({
            "node_id": node_id,
            "zone_id": zone_id,
            "timestamp": ts,
            "ax": 0.15,
            "ay": 0.12,
            "az": 0.92,
            "tilt_x": 5.5,
            "tilt_y": 4.8,
            "vibration": 9.0,
        })
    return readings
