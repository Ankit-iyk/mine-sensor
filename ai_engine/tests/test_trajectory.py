from ai_engine.intelligence.trajectory import reset_trajectory_state, track_trajectory


def setup_function():
    reset_trajectory_state()


def test_single_reading_is_steady():
    result = track_trajectory("N01", 20)
    assert result["trajectory"] == "STEADY"
    assert result["history"] == [20]


def test_rising_trajectory_from_plan_example():
    scores = [20, 25, 31, 39, 51, 64, 78]
    for score in scores:
        result = track_trajectory("N02", score)
    assert result["trajectory"] == "RISING"


def test_steady_trajectory_flat_scores():
    for score in [30, 31, 29, 30, 32]:
        result = track_trajectory("N03", score)
    assert result["trajectory"] == "STEADY"


def test_falling_trajectory():
    scores = [80, 65, 50, 35, 20]
    for score in scores:
        result = track_trajectory("N04", score)
    assert result["trajectory"] == "FALLING"


def test_nodes_tracked_independently():
    for score in [20, 25, 31, 39, 51, 64, 78]:
        track_trajectory("N05", score)
    result = track_trajectory("N06", 30)
    assert result["trajectory"] == "STEADY"
    assert result["history"] == [30]
