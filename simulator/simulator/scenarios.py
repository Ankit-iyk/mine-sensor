"""
SUBSENSE Simulator — Scenario Definitions

A Scenario is a named configuration that maps node IDs to the
scenario they should run. This allows coordinated multi-node
scenarios (e.g. Scenario 5: several nearby nodes develop anomalies
simultaneously).

Usage
-----
    from simulator.scenarios import SCENARIOS, ScenarioConfig
    cfg = SCENARIOS["gradual_tilt"]
    # cfg.node_assignments = {"N01": "gradual_tilt", "N02": "normal", ...}
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ScenarioConfig:
    """
    A named simulation scenario.

    node_assignments maps node_id → scenario name to run on that node.
    duration_seconds: optional cap; None = run until interrupted.
    description: human-readable explanation.
    """
    name: str
    description: str
    node_assignments: Dict[str, str]  # node_id → scenario_name
    duration_seconds: int | None = None


# ── Available nodes in the prototype mine ───────────────────────────────────
#
# Physical layout (approximate):
#
#   ZONE Z01                  ZONE Z02            ZONE Z03
#   ┌───────────────┐         ┌──────────┐        ┌────────┐
#   │ N01      N02  │         │  N04     │        │  N06   │
#   │               │         │          │        └────────┘
#   │ N03           │         │  N05     │
#   └───────────────┘         └──────────┘
#
# N01–N03 are close neighbours. N04–N05 are neighbours. N06 is isolated.

ALL_NODES = {
    "N01": "Z01",
    "N02": "Z01",
    "N03": "Z01",
    "N04": "Z02",
    "N05": "Z02",
    "N06": "Z03",
}

# ── Scenario registry ────────────────────────────────────────────────────────

SCENARIOS: Dict[str, ScenarioConfig] = {

    # ── Scenario 1: Fully stable mine ──────────────────────────────────
    "normal": ScenarioConfig(
        name="normal",
        description=(
            "All nodes report stable readings with realistic sensor noise. "
            "Used to establish baselines and verify nominal system behaviour."
        ),
        node_assignments={nid: "normal" for nid in ALL_NODES},
    ),

    # ── Scenario 2: Isolated vibration event ───────────────────────────
    "vibration_event": ScenarioConfig(
        name="vibration_event",
        description=(
            "Node N02 experiences a short vibration burst (simulating nearby "
            "machinery or micro-seismic activity). All other nodes remain normal. "
            "Tests that the system detects a transient vibration event on a "
            "single node without raising a zone-level alert."
        ),
        node_assignments={
            "N01": "normal",
            "N02": "vibration_event",   # ← affected
            "N03": "normal",
            "N04": "normal",
            "N05": "normal",
            "N06": "normal",
        },
        duration_seconds=60,
    ),

    # ── Scenario 3: Gradual tilt on one node ───────────────────────────
    "gradual_tilt": ScenarioConfig(
        name="gradual_tilt",
        description=(
            "Node N01 shows a slowly increasing tilt angle. "
            "Tests the temporal engine's ability to detect monotonic trend "
            "over time vs random noise."
        ),
        node_assignments={
            "N01": "gradual_tilt",      # ← slow drift
            "N02": "normal",
            "N03": "normal",
            "N04": "normal",
            "N05": "normal",
            "N06": "normal",
        },
        duration_seconds=120,
    ),

    # ── Scenario 4: Persistent anomaly (single node) ────────────────────
    "persistent_anomaly": ScenarioConfig(
        name="persistent_anomaly",
        description=(
            "Node N03 is locked in a persistently anomalous state: "
            "elevated tilt AND intermittent vibration, sustained indefinitely. "
            "Tests the persistence tracker and incident creation."
        ),
        node_assignments={
            "N01": "normal",
            "N02": "normal",
            "N03": "persistent_anomaly",  # ← sustained
            "N04": "normal",
            "N05": "normal",
            "N06": "normal",
        },
    ),

    # ── Scenario 5: Multi-node correlated event ─────────────────────────
    "multi_node_event": ScenarioConfig(
        name="multi_node_event",
        description=(
            "Nodes N01, N02, N03 (all in Z01) develop correlated gradual tilt. "
            "N04 (adjacent zone Z02) also starts showing mild tilt. "
            "N05 and N06 remain normal. "
            "Tests spatial correlation: the risk engine should escalate Z01 "
            "to a zone-level warning even if individual node scores are moderate."
        ),
        node_assignments={
            "N01": "multi_node_event",  # ← affected
            "N02": "multi_node_event",  # ← affected
            "N03": "multi_node_event",  # ← affected
            "N04": "gradual_tilt",      # ← mild correlation
            "N05": "normal",
            "N06": "normal",
        },
    ),

    # ── Scenario 6: Sensor failure ──────────────────────────────────────
    "sensor_failure": ScenarioConfig(
        name="sensor_failure",
        description=(
            "Node N05 rotates through sensor failure modes: "
            "all-zero accel, frozen readings, out-of-range values, missing fields. "
            "Tests that the validation layer rejects bad data and the system "
            "flags sensor health — NOT ground instability."
        ),
        node_assignments={
            "N01": "normal",
            "N02": "normal",
            "N03": "normal",
            "N04": "normal",
            "N05": "sensor_failure",    # ← broken sensor
            "N06": "normal",
        },
    ),
}
