import joblib
import numpy as np
import pytest

from ai_engine.evaluation.classifier_v2 import (
    RuleBaselineV2,
    RuleThresholdsV2,
    SupervisedClassifierV2,
)
from ai_engine.evaluation.datasets_v2 import (
    CLASS_NAMES_V2,
    generate_episode_v2,
)
from ai_engine.evaluation.features_v2 import (
    FEATURE_NAMES_V2,
    extract_window_features_v2,
)
from ai_engine.evaluation.run_v2 import (
    _binary_confusions_by_seed,
    _class_confusions_by_seed,
)
from ai_engine.pipeline import event_classifier_v2


def _training_row(label, seed_value):
    features = {name: 0.0 for name in FEATURE_NAMES_V2}
    features.update({
        "vibration_peak": 0.6 if label == "BLAST_TRANSIENT" else 0.0,
        "vibration_decay_seconds": 0.2 if label == "BLAST_TRANSIENT" else 0.0,
        "decay_missing": 0.0 if label == "BLAST_TRANSIENT" else 1.0,
        "cumulative_tilt_magnitude_degrees": (
            0.5 if label == "PROGRESSIVE_TILT_PROXY" else 0.0
        ),
        "drift_slope_degrees_per_hour": (
            0.05 if label == "PROGRESSIVE_TILT_PROXY" else 0.0
        ),
        "persistence_fraction": (
            1.0 if label == "PROGRESSIVE_TILT_PROXY" else 0.0
        ),
        "residual_tilt_magnitude_degrees": 0.0,
        "parameters": {},
        "class_label": label,
        "seed": seed_value,
        "scenario": "unit_test",
    })
    return features


def test_v2_generator_is_seeded_and_has_protocol_shapes():
    first = generate_episode_v2("blast_impulse", 500000)
    second = generate_episode_v2("blast_impulse", 500000)
    assert first.tilt_degrees.shape == (361, 1, 2)
    assert first.waveform_acceleration.shape == (500, 3)
    assert np.array_equal(first.tilt_degrees, second.tilt_degrees)
    assert np.array_equal(first.waveform_acceleration, second.waveform_acceleration)
    assert first.origin == "simulation"


def test_progressive_generator_has_increasing_underlying_tilt_trend():
    episode = generate_episode_v2("progressive_single", 400003)
    trajectory = episode.tilt_ground_truth_degrees[60:, 0, :]
    assert np.all(np.diff(trajectory, axis=0) > 0)


def test_blast_waveform_has_a_decaying_tail():
    episode = generate_episode_v2("blast_impulse", 500001)
    early = np.mean(np.abs(episode.waveform_acceleration[:10]))
    late = np.mean(np.abs(episode.waveform_acceleration[-50:]))
    assert early > late
    assert 0.10 <= episode.parameters["decay_seconds"] <= 0.80


def test_sensitivity_and_shifted_conditions_use_frozen_values():
    decay = generate_episode_v2("blast_impulse", 500000, condition_index=1)
    shifted = generate_episode_v2("blast_tilt_recovery", 500000, condition_index=13)
    assert decay.parameters["decay_seconds"] == 0.10
    assert shifted.parameters["decay_seconds"] == 1.20
    assert shifted.parameters["tilt_offset_degrees"] == 0.15
    assert shifted.parameters["blast_peak_normalized"] == 1.0
    assert shifted.parameters["progressive_rate_deg_per_hour"] == 0.005


def test_feature_extraction_is_causal_and_reports_transient_decay():
    episode = generate_episode_v2("blast_impulse", 500002)
    features = extract_window_features_v2(episode, 60)
    assert features["class_label"] == "BLAST_TRANSIENT"
    assert features["is_event"] is True
    assert features["vibration_peak"] > 0
    assert features["decay_missing"] == 0.0
    assert features["vibration_decay_seconds"] > 0

    before_future_change = extract_window_features_v2(episode, 75)
    episode.tilt_degrees[76:] = 999.0
    after_future_change = extract_window_features_v2(episode, 75)
    assert (
        before_future_change["cumulative_tilt_magnitude_degrees"]
        == after_future_change["cumulative_tilt_magnitude_degrees"]
    )


def test_other_transient_has_no_progressive_truth_label():
    episode = generate_episode_v2("accel_vibration_without_tilt", 500003)
    features = extract_window_features_v2(episode, 60)
    assert features["class_label"] == "OTHER_TRANSIENT_OR_NORMAL"
    assert features["is_event"] is True
    assert features["cumulative_tilt_magnitude_degrees"] < 0.3


def test_rule_baseline_requires_persistence_and_separates_blast():
    thresholds = RuleThresholdsV2(0.01, 0.05, 0.5, 0.25, 0.8, 0.1)
    model = RuleBaselineV2(thresholds)
    progressive = _training_row("PROGRESSIVE_TILT_PROXY", 1)
    progressive["persistence_by_cumulative_threshold"] = {0.05: 1.0}
    blast = _training_row("BLAST_TRANSIENT", 2)
    blast["persistence_by_cumulative_threshold"] = {0.05: 0.0}
    other = _training_row("OTHER_TRANSIENT_OR_NORMAL", 3)
    other["persistence_by_cumulative_threshold"] = {0.05: 0.0}
    assert model.predict_one(progressive) == "PROGRESSIVE_TILT_PROXY"
    assert model.predict_one(blast) == "BLAST_TRANSIENT"
    assert model.predict_one(other) == "OTHER_TRANSIENT_OR_NORMAL"


def test_supervised_classifier_trains_and_calibrates_from_feature_rows():
    rows = []
    for seed in range(12):
        for label in CLASS_NAMES_V2:
            rows.append(_training_row(label, seed))
    classifier = SupervisedClassifierV2()
    classifier.fit(rows)
    temperature = classifier.calibrate_temperature(rows)
    assert temperature in (0.50, 0.75, 1.00, 1.50, 2.00)
    assert np.array_equal(
        classifier.predict(rows),
        np.asarray([row["class_label"] for row in rows], dtype=object),
    )
    probabilities = classifier.predict_proba(rows[:3])
    assert probabilities.shape == (3, 3)
    assert np.allclose(probabilities.sum(axis=1), 1.0)


def test_inference_wrapper_keeps_default_result_unchanged(monkeypatch):
    expected = {"anomaly": {"state": "NORMAL"}}
    monkeypatch.setattr(event_classifier_v2, "analyze_telemetry", lambda *args, **kwargs: expected)
    result = event_classifier_v2.analyze_telemetry_v2(
        {"node_id": "N01"},
        enable_event_classification=False,
    )
    assert result is expected
    assert "event_classification" not in result


def test_enabled_inference_abstains_when_high_rate_window_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        event_classifier_v2,
        "analyze_telemetry",
        lambda *args, **kwargs: {"anomaly": {"state": "ANOMALOUS"}},
    )
    result = event_classifier_v2.analyze_telemetry_v2(
        {"node_id": "N01"},
        enable_event_classification=True,
    )
    assert result["event_classification"]["label"] == "UNKNOWN"
    assert result["event_classification"]["reason"] == "v2_signal_window_unavailable"


def test_enabled_inference_adds_a_calibrated_class_output(monkeypatch, tmp_path):
    rows = [
        _training_row(label, seed)
        for seed in range(12)
        for label in CLASS_NAMES_V2
    ]
    classifier = SupervisedClassifierV2()
    classifier.fit(rows)
    classifier.calibrate_temperature(rows)
    artifact = tmp_path / "event_classifier.joblib"
    joblib.dump(classifier, artifact)

    monkeypatch.setattr(
        event_classifier_v2,
        "analyze_telemetry",
        lambda *args, **kwargs: {"anomaly": {"state": "NORMAL"}},
    )
    result = event_classifier_v2.analyze_telemetry_v2(
        {"node_id": "N01"},
        enable_event_classification=True,
        event_features=rows[0],
        model_path=artifact,
    )
    assert result["event_classification"]["label"] in (*CLASS_NAMES_V2, "UNKNOWN")
    assert sum(result["event_classification"]["probabilities"].values()) == pytest.approx(1.0)


def test_invalid_environment_switch_is_reported(monkeypatch):
    monkeypatch.setattr(
        event_classifier_v2,
        "analyze_telemetry",
        lambda *args, **kwargs: {"anomaly": {"state": "NORMAL"}},
    )
    monkeypatch.setenv("SUBSENSE_EVENT_CLASSIFICATION_V2", "sometimes")
    with pytest.raises(ValueError, match="SUBSENSE_EVENT_CLASSIFICATION_V2"):
        event_classifier_v2.analyze_telemetry_v2({"node_id": "N01"})


def test_v2_metric_confusions_ignore_nonexistent_nodes():
    truth = np.full((2, 9, 2, 3), "", dtype=object)
    predicted = np.full_like(truth, "")
    binary = np.zeros(truth.shape, dtype=bool)
    node_mask = np.zeros((9, 3), dtype=bool)
    node_mask[0, 0] = True
    for seed in range(2):
        truth[seed, 0, :, 0] = "OTHER_TRANSIENT_OR_NORMAL"
        predicted[seed, 0, :, 0] = "OTHER_TRANSIENT_OR_NORMAL"
    class_counts = _class_confusions_by_seed(truth, predicted, node_mask)
    binary_counts = _binary_confusions_by_seed(truth, binary, node_mask)
    assert class_counts.shape == (2, 3, 4)
    assert class_counts[:, 2, 2].tolist() == [2, 2]
    assert int(class_counts.sum()) == 4
    assert int(binary_counts.sum()) == 4
