"""
SUBSENSE — Spatial Correlation Engine (Phase 10)

Correlates multi-node sensor telemetry across the mine spatial topology:
1. Spatial Topology Graph: Tracks physical coordinates (x, y) and topological adjacency.
2. Anomaly Verification: Distinguishes single-node isolated noise (e.g. vehicle passing by)
   from genuine ground subsidence involving adjacent ground movement.
3. Multi-Node Correlation Metrics:
   - Neighbor anomaly coincidence
   - Directional tilt coherence
   - Cluster radius and zone-wide scope
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Optional


@dataclass
class NodeSpatialState:
    """Latest recorded spatial and kinematic state of a node."""
    node_id: str
    zone_id: str
    x: float
    y: float
    timestamp: datetime
    anomaly_score: float
    state: str             # NORMAL | MICRO_ANOMALY | ANOMALOUS
    tilt_x: float
    tilt_y: float
    precursor_score: float


@dataclass
class SpatialCorrelationAssessment:
    """Spatial correlation assessment for a specific node and its surrounding zone."""
    node_id: str
    zone_id: str
    timestamp: datetime
    neighbor_nodes: list[str]
    affected_neighbors: list[str]
    spatial_correlation_index: float   # 0.0 to 1.0
    is_multi_node_event: bool
    event_scope: str                   # ISOLATED_DISTURBANCE | LOCAL_CLUSTER | ZONE_WIDE_SUBSIDENCE
    explanations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "zone_id": self.zone_id,
            "timestamp": self.timestamp.isoformat(),
            "neighbor_nodes": self.neighbor_nodes,
            "affected_neighbors": self.affected_neighbors,
            "spatial_correlation_index": self.spatial_correlation_index,
            "is_multi_node_event": self.is_multi_node_event,
            "event_scope": self.event_scope,
            "explanations": self.explanations,
        }


class SpatialCorrelationEngine:
    """
    Manages mine geometry, node adjacency, and multi-node spatial correlation.
    """

    DEFAULT_TOPOLOGY = {
        # Zone 01: Longwall Panel Face
        "N01": {"zone_id": "Z01", "x": 0.0, "y": 0.0},
        "N02": {"zone_id": "Z01", "x": 25.0, "y": 0.0},
        "N03": {"zone_id": "Z01", "x": 12.5, "y": 20.0},
        # Zone 02: Main Haulage Drift
        "N04": {"zone_id": "Z02", "x": 100.0, "y": 0.0},
        "N05": {"zone_id": "Z02", "x": 125.0, "y": 0.0},
        "N06": {"zone_id": "Z02", "x": 112.5, "y": 20.0},
    }

    NEIGHBOR_RADIUS_METERS: float = 35.0  # Max distance to consider as topological neighbors

    def __init__(self, topology: Optional[dict[str, dict[str, Any]]] = None) -> None:
        self.topology = topology or self.DEFAULT_TOPOLOGY
        # Latest known states: node_id -> NodeSpatialState
        self._states: dict[str, NodeSpatialState] = {}

    def update_node_state(
        self,
        node_id: str,
        zone_id: str,
        timestamp: datetime,
        anomaly_score: float,
        state: str,
        tilt_x: float,
        tilt_y: float,
        precursor_score: float = 0.0,
    ) -> SpatialCorrelationAssessment:
        """
        Update the spatial snapshot for node_id and compute its spatial correlation.
        """
        node_info = self.topology.get(node_id, {"zone_id": zone_id, "x": 0.0, "y": 0.0})
        x = float(node_info.get("x", 0.0))
        y = float(node_info.get("y", 0.0))

        self._states[node_id] = NodeSpatialState(
            node_id=node_id,
            zone_id=zone_id,
            x=x,
            y=y,
            timestamp=timestamp,
            anomaly_score=anomaly_score,
            state=state,
            tilt_x=tilt_x,
            tilt_y=tilt_y,
            precursor_score=precursor_score,
        )

        return self.assess_spatial_correlation(node_id)

    def get_neighbors(self, node_id: str) -> list[str]:
        """Return list of node IDs located within NEIGHBOR_RADIUS_METERS of node_id."""
        if node_id not in self.topology:
            return []

        target = self.topology[node_id]
        tx, ty = target["x"], target["y"]
        tz = target.get("zone_id")

        neighbors = []
        for nid, info in self.topology.items():
            if nid == node_id:
                continue
            # Check zone alignment and Euclidean distance
            if info.get("zone_id") == tz:
                dist = math.hypot(info["x"] - tx, info["y"] - ty)
                if dist <= self.NEIGHBOR_RADIUS_METERS:
                    neighbors.append(nid)
        return neighbors

    def assess_spatial_correlation(self, node_id: str) -> SpatialCorrelationAssessment:
        """
        Assess spatial subsidence correlation for a specific node against its neighbors.
        """
        state = self._states.get(node_id)
        zone_id = self.topology.get(node_id, {}).get("zone_id", "Z01")
        now = state.timestamp if state else datetime.now(timezone.utc)

        neighbors = self.get_neighbors(node_id)
        if not neighbors:
            return SpatialCorrelationAssessment(
                node_id=node_id,
                zone_id=zone_id,
                timestamp=now,
                neighbor_nodes=[],
                affected_neighbors=[],
                spatial_correlation_index=0.0,
                is_multi_node_event=False,
                event_scope="ISOLATED_DISTURBANCE",
                explanations=["No adjacent sensor nodes within correlation radius."],
            )

        # Check neighbor anomaly and freshness (within last 30 seconds)
        affected_neighbors = []
        explanations = []

        target_score = state.anomaly_score if state else 0.0

        for nid in neighbors:
            n_state = self._states.get(nid)
            if n_state is None:
                continue

            # Freshness check
            age = (now - n_state.timestamp).total_seconds()
            if abs(age) > 45.0:
                continue  # Stale data

            # Neighbor is considered affected if anomaly score > 0.30 or precursor > 0.30
            if n_state.anomaly_score >= 0.30 or n_state.precursor_score >= 0.30:
                affected_neighbors.append(nid)

        # Calculate Spatial Correlation Index
        if not affected_neighbors:
            if target_score >= 0.60:
                spatial_correlation_index = 0.15
                event_scope = "ISOLATED_DISTURBANCE"
                explanations.append(
                    f"Elevated anomaly on {node_id} is unconfirmed by neighbors "
                    f"({', '.join(neighbors)}). Likely local disturbance."
                )
            else:
                spatial_correlation_index = 0.05
                event_scope = "ISOLATED_DISTURBANCE"
            is_multi_node = False
        else:
            n_affected = len(affected_neighbors)
            ratio = n_affected / len(neighbors)

            if n_affected >= 2 or ratio >= 0.66:
                spatial_correlation_index = round(min(1.0, 0.75 + 0.25 * ratio), 3)
                event_scope = "ZONE_WIDE_SUBSIDENCE"
                is_multi_node = True
                explanations.append(
                    f"Wide-area subsidence confirmed: {node_id} correlated with "
                    f"{n_affected} adjacent nodes ({', '.join(affected_neighbors)}) in {zone_id}."
                )
            else:
                spatial_correlation_index = round(0.50 + 0.25 * ratio, 3)
                event_scope = "LOCAL_CLUSTER"
                is_multi_node = True
                explanations.append(
                    f"Multi-node cluster detected between {node_id} and "
                    f"{', '.join(affected_neighbors)}."
                )

        return SpatialCorrelationAssessment(
            node_id=node_id,
            zone_id=zone_id,
            timestamp=now,
            neighbor_nodes=neighbors,
            affected_neighbors=affected_neighbors,
            spatial_correlation_index=spatial_correlation_index,
            is_multi_node_event=is_multi_node,
            event_scope=event_scope,
            explanations=explanations,
        )


# Global singleton instance
spatial_engine = SpatialCorrelationEngine()
