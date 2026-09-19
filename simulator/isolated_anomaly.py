"""
Generates a sequence where ONE node spikes while its neighbours stay normal.
Used to test anomaly detection without triggering false spatial correlation.
"""

from datetime import datetime, timedelta

from simulator.normal import generate_normal_sequence


def generate_isolated_anomaly(node_id="N01", zone_id="Z01", count=50, spike_at=30, start_time=None):
    """
    Returns a sequence that is normal until `spike_at`, then tilt/vibration jump sharply.
    """
    if start_time is None:
        start_time = datetime(2026, 9, 19, 9, 0, 0)

    readings = generate_normal_sequence(node_id, zone_id, spike_at, start_time)

    for i in range(spike_at, count):
        ts = (start_time + timedelta(seconds=i)).isoformat() + "Z"
        readings.append({
            "node_id": node_id,
            "zone_id": zone_id,
            "timestamp": ts,
            "ax": 0.3,
            "ay": 0.25,
            "az": 0.9,
            "tilt_x": round(8.0 + (i - spike_at) * 0.3, 2),
            "tilt_y": round(6.5 + (i - spike_at) * 0.2, 2),
            "vibration": round(min(1.0, 0.35 + (i - spike_at) * 0.015), 3),
        })
    return readings
