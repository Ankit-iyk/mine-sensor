from ai_engine.intelligence.spatial import (
    get_neighbours,
    register_node,
    register_nodes,
    reset_node_registry,
    spatial_correlation,
)


def setup_function():
    reset_node_registry()


def test_register_and_get_neighbours_within_radius():
    register_nodes({
        "N01": {"x": 0, "y": 0},
        "N02": {"x": 5, "y": 0},
        "N03": {"x": 50, "y": 50},
    })
    neighbours = get_neighbours("N01", radius=10)
    assert neighbours == ["N02"]


def test_get_neighbours_unregistered_node_returns_empty():
    assert get_neighbours("N99", radius=10) == []


def test_spatial_correlation_no_neighbours():
    register_node("N01", 0, 0)
    result = spatial_correlation("N01", anomalous_nodes={"N01"}, radius=10)
    assert result == {"correlation": 0.0, "affected_nodes": []}


def test_spatial_correlation_all_neighbours_anomalous():
    register_nodes({
        "N01": {"x": 0, "y": 0},
        "N02": {"x": 5, "y": 0},
        "N03": {"x": 8, "y": 0},
    })
    result = spatial_correlation("N01", anomalous_nodes={"N02", "N03"}, radius=10)
    assert result["correlation"] == 1.0
    assert set(result["affected_nodes"]) == {"N02", "N03"}


def test_spatial_correlation_partial_neighbours_anomalous():
    register_nodes({
        "N01": {"x": 0, "y": 0},
        "N02": {"x": 5, "y": 0},
        "N03": {"x": 8, "y": 0},
    })
    result = spatial_correlation("N01", anomalous_nodes={"N02"}, radius=10)
    assert result["correlation"] == 0.5
    assert result["affected_nodes"] == ["N02"]
