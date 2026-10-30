from collections import defaultdict
from datetime import datetime

from ai_engine.evaluation.datasets import (
    EVENT_SCENARIOS,
    SCENARIOS,
    generate_episode,
)


def test_registered_scenario_matrix_has_sixteen_entries():
    assert len(SCENARIOS) == 16
    assert len(set(SCENARIOS)) == 16


def test_all_generated_rows_include_simulation_and_event_provenance():
    for scenario in SCENARIOS:
        rows = generate_episode(scenario, seed=321)
        assert rows
        assert all(row["origin"] == "simulation" for row in rows)
        assert all(row["scenario"] == scenario for row in rows)
        for row in rows:
            if row["is_event"]:
                assert scenario in EVENT_SCENARIOS
                assert row["event_id"]
                assert row["event_onset_time"]
                assert row["event_onset_step"] == 30
                assert row["event_duration_steps"] is not None


def test_acceleration_only_and_combined_disturbances_preserve_tilt():
    accel = generate_episode("acceleration_only", seed=12)
    combined = generate_episode("combined_vibration_acceleration", seed=12)
    normal = generate_episode("normal", seed=12)
    for rows in (accel, combined):
        node_rows = [row for row in rows if row["node_id"] == "N01"]
        during = [row for row in node_rows if row["step"] == 40][0]
        nominal = next(row for row in normal if row["node_id"] == "N01" and row["step"] == 40)
        assert during["tilt_x"] == nominal["tilt_x"]
        assert during["accel_x"] - nominal["accel_x"] == 1.5
    assert next(row for row in combined if row["node_id"] == "N01" and row["step"] == 40)["vibration"] == 500


def test_correlated_drift_affects_all_nodes_with_shared_onset():
    rows = generate_episode("correlated_multi_node_drift", seed=99)
    affected = {row["node_id"] for row in rows if row["is_event"]}
    onset_by_node = {
        node: next(row["event_onset_time"] for row in rows if row["node_id"] == node and row["is_event"])
        for node in affected
    }
    assert affected == {"N01", "N02", "N03"}
    assert len(set(onset_by_node.values())) == 1


def test_sensor_dropout_is_absent_data_and_records_recovery_gap():
    rows = generate_episode("sensor_dropout", seed=5)
    node_rows = [row for row in rows if row["node_id"] == "N01"]
    assert len(node_rows) == 105
    assert not {row["step"] for row in node_rows}.intersection(range(50, 65))
    recovery = next(row for row in node_rows if row["step"] == 65)
    assert recovery["data_gap_before"] is True
    assert recovery["is_event"] is False
    assert recovery["data_gap_start_step"] == 50
    assert recovery["data_gap_duration_steps"] == 15
    assert recovery["data_gap_start_time"]
    assert recovery["data_gap_duration_seconds"] >= 15.0


def test_sampling_jitter_changes_timestamps_without_event_truth():
    rows = generate_episode("sampling_jitter", seed=7)
    by_node = defaultdict(list)
    for row in rows:
        by_node[row["node_id"]].append(row["timestamp"])
        assert row["is_event"] is False
    for timestamps in by_node.values():
        intervals = [
            (datetime.fromisoformat(later) - datetime.fromisoformat(earlier)).total_seconds()
            for earlier, later in zip(timestamps, timestamps[1:])
        ]
        assert min(intervals) >= 0.5
        assert max(intervals) <= 1.5
        assert len(set(intervals)) > 1


def test_impulse_and_phone_vibration_are_nuisance_without_tilt_labels():
    for scenario in ("impulse_nuisance", "phone_vibration_nuisance"):
        rows = generate_episode(scenario, seed=4)
        active = [row for row in rows if row["event_type"] == scenario]
        assert active
        assert all(row["is_event"] is False and row["event_id"] is None for row in active)
        assert all(row["node_id"] == "N01" for row in active)
        assert max(row["vibration"] for row in active) > 200


def test_mixed_events_overlap_tilt_and_vibration_signals():
    rows = generate_episode("mixed_overlapping_events", seed=8)
    overlapping = [
        row for row in rows
        if row["node_id"] == "N01" and row["is_event"] and 35 <= row["step"] < 40
    ]
    assert len(overlapping) == 5
    assert all(row["vibration"] == 700 for row in overlapping)
