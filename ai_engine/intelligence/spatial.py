"""
Spatial intelligence engine.
Computes neighbourhood relationships between nodes using their coordinates,
and measures regional correlation when nearby nodes are anomalous together.
"""

import math

_node_positions = {}


def reset_node_registry():
	"""Clears the node position registry. Mainly useful for tests."""
	_node_positions.clear()


def register_node(node_id: str, x: float, y: float):
	"""Registers or updates a node's physical position."""
	_node_positions[node_id] = {"x": x, "y": y}


def register_nodes(nodes: dict):
	"""Bulk-registers nodes from a mapping of coordinates."""
	for node_id, position in nodes.items():
		register_node(node_id, position["x"], position["y"])


def _distance(node_a: str, node_b: str) -> float:
	position_a = _node_positions[node_a]
	position_b = _node_positions[node_b]
	return math.sqrt(
		(position_a["x"] - position_b["x"]) ** 2
		+ (position_a["y"] - position_b["y"]) ** 2
	)


def get_neighbours(node_id: str, radius: float) -> list:
	"""
	Returns registered nodes within `radius` of node_id, excluding node_id.
	"""
	if node_id not in _node_positions:
		return []

	neighbours = []
	for other_id in _node_positions:
		if other_id == node_id:
			continue
		if _distance(node_id, other_id) <= radius:
			neighbours.append(other_id)
	return neighbours


def spatial_correlation(node_id: str, anomalous_nodes: set, radius: float = 15.0) -> dict:
	"""
	Measures the fraction of node_id's neighbours that are anomalous.
	"""
	neighbours = get_neighbours(node_id, radius)
	if not neighbours:
		return {"correlation": 0.0, "affected_nodes": []}

	affected_nodes = [node for node in neighbours if node in anomalous_nodes]
	return {
		"correlation": len(affected_nodes) / len(neighbours),
		"affected_nodes": affected_nodes,
	}
