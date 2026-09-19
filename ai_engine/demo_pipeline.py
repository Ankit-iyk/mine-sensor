"""
Demo: runs each simulator scenario through the full AI pipeline
and prints how risk evolves. This is the end-to-end proof.
"""

from simulator.normal import generate_normal_sequence
from simulator.isolated_anomaly import generate_isolated_anomaly
from simulator.escalating_event import generate_escalating_event

from ai_engine.pipeline.inference import analyze_telemetry, reset_pipeline_state
from ai_engine.pipeline.build_training_data import build_normal_feature_dataset
from ai_engine.anomaly.isolation_forest import train_isolation_forest, save_model
from ai_engine.fingerprint.fingerprint import reset_fingerprints
from ai_engine.intelligence.temporal import reset_temporal_state
from ai_engine.intelligence.trajectory import reset_trajectory_state
from ai_engine.intelligence.spatial import reset_node_registry
from ai_engine.features.extractor import reset_state
from ai_engine.anomaly.detector import reset_model_cache


def reset_everything():
    reset_pipeline_state()
    reset_fingerprints()
    reset_temporal_state()
    reset_trajectory_state()
    reset_node_registry()
    reset_state()
    reset_model_cache()


def run_scenario(name, readings, model_path):
    print(f"\n{'=' * 50}\nSCENARIO: {name}\n{'=' * 50}")
    reset_everything()
    for index, reading in enumerate(readings):
        result = analyze_telemetry(reading, model_path=model_path)
        risk = result["risk"]
        print(
            f"  step {index:3d} | risk={risk['score']:6.2f} | state={risk['state']:8s} "
            f"| trajectory={result['trajectory']['trajectory']:8s} "
            f"| temporal={result['temporal']['state']}"
        )
    print(f"  FINAL EXPLANATION: {result['explanation']['summary']}")
    for reason in result["explanation"]["reasons"]:
        print(f"    - {reason}")


if __name__ == "__main__":
    print("Training model on normal data...")
    dataset = build_normal_feature_dataset(node_ids=["N01"], count_per_node=50)
    model = train_isolation_forest(dataset)
    model_path = save_model(model)

    run_scenario("Normal", generate_normal_sequence(count=30), model_path)
    run_scenario("Isolated anomaly", generate_isolated_anomaly(count=40, spike_at=20), model_path)
    run_scenario("Escalating event", generate_escalating_event(count=40, onset_at=15), model_path)
