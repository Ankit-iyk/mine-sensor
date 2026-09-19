"""
Generates simultaneous anomalies across MULTIPLE neighbouring nodes.
Tests spatial correlation — should produce a HIGH regional_correlation score.
"""

from simulator.escalating_event import generate_escalating_event


def generate_regional_event(node_ids=("N01", "N02", "N03"), zone_id="Z01", count=50, onset_at=15):
    """
    Returns a dict of {node_id: [readings]} where all listed nodes escalate together.
    """
    return {
        node_id: generate_escalating_event(node_id=node_id, zone_id=zone_id, count=count, onset_at=onset_at)
        for node_id in node_ids
    }
