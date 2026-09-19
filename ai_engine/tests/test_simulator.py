from simulator.escalating_event import generate_escalating_event
from simulator.isolated_anomaly import generate_isolated_anomaly
from simulator.normal import generate_normal_sequence
from simulator.persistent_anomaly import generate_persistent_anomaly
from simulator.regional_event import generate_regional_event


def test_normal_sequence_length_and_keys():
    data = generate_normal_sequence(count=10)
    assert len(data) == 10
    assert set(data[0].keys()) == {
        "node_id", "zone_id", "timestamp", "ax", "ay", "az", "tilt_x", "tilt_y", "vibration"
    }


def test_isolated_anomaly_spikes_after_threshold():
    data = generate_isolated_anomaly(count=40, spike_at=20)
    assert data[10]["tilt_x"] < 5
    assert data[30]["tilt_x"] > 5


def test_persistent_anomaly_stays_flat():
    data = generate_persistent_anomaly(count=30, onset_at=10)
    assert data[15]["tilt_x"] == data[25]["tilt_x"]


def test_escalating_event_increases_over_time():
    data = generate_escalating_event(count=30, onset_at=10)
    assert data[15]["tilt_x"] < data[25]["tilt_x"]


def test_regional_event_covers_all_nodes():
    result = generate_regional_event(node_ids=("N01", "N02"), count=20)
    assert set(result.keys()) == {"N01", "N02"}
    assert len(result["N01"]) == 20
