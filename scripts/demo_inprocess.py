"""Run simulator scenarios through backend processing without Docker or DB."""

from __future__ import annotations

import random
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "backend", ROOT / "simulator"):
   sys.path.insert(0, str(path))

from app.ingestion.schemas import TelemetryReading
from app.ml.loader import get_detector
from app.processing.pipeline import ProcessingPipeline
from app.intelligence.alerts import alert_engine
from app.intelligence.risk_engine import risk_engine
from app.intelligence.spatial import spatial_engine
from app.intelligence.temporal import temporal_engine
from ai_engine.adapter import AIEngineDetector
from simulator.node import SensorNode
from simulator.scenarios import ALL_NODES, SCENARIOS

SCENARIO_NAMES = (
    "normal",
    "vibration_event",
    "gradual_tilt",
    "persistent_anomaly",
    "multi_node_event",
)


def _reset_intelligence_state() -> None:
    temporal_engine.reset()
    risk_engine.reset()
    spatial_engine._states.clear()
    alert_engine.reset()


def main() -> None:
    detector = get_detector()
    if not isinstance(detector, AIEngineDetector):
        raise RuntimeError(f"AIEngineDetector required, got {type(detector).__name__}")
    print(f"Detector: {type(detector).__name__} ({detector.version})")

    for scenario_index, scenario_name in enumerate(SCENARIO_NAMES):
        random.seed(20261022 + scenario_index)
        np.random.seed(20261022 + scenario_index)
        _reset_intelligence_state()

        scenario = SCENARIOS[scenario_name]
        node_id = next(
            node
            for node, assignment in scenario.node_assignments.items()
            if assignment == scenario_name
        )
        node = SensorNode(node_id=node_id, zone_id=ALL_NODES[node_id])
        node.set_scenario(scenario_name)
        pipeline = ProcessingPipeline(persist_to_db=False)
        start = datetime.now(timezone.utc)
        states: Counter[str] = Counter()
        count = 0
        final_result = None

        for step in range(200):
            payload = node.generate_reading()
            payload["timestamp"] = (start + timedelta(seconds=step)).isoformat()
            reading = TelemetryReading.model_validate(payload)
            result = pipeline.process_reading(reading)
            if result is None:
                continue
            states[result.state] += 1
            count += 1
            final_result = result

        fractions = {
            state: states[state] / count if count else 0.0
            for state in ("NORMAL", "MICRO_ANOMALY", "ANOMALOUS")
        }
        print(f"{scenario_name}: features={count}, state_fractions={fractions}")
        if scenario_name == "gradual_tilt":
            if final_result is None:
                raise RuntimeError("gradual_tilt produced no backend feature results")
            print(
                "gradual_tilt final risk explanation: "
                f"state={final_result.risk['state']}, "
                f"score={final_result.risk['risk_score']}, "
                f"reasons={final_result.risk['reasons']}, "
                f"precursor={final_result.temporal['explanations']}"
            )


if __name__ == "__main__":
    main()
