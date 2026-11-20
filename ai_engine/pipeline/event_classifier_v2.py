"""Opt-in v2 class output layered onto the existing telemetry inference path."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from ai_engine.evaluation.classifier_v2 import SupervisedClassifierV2
from ai_engine.pipeline.inference import analyze_telemetry


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_MODEL_PATH = (
    _REPO_ROOT
    / "docs"
    / "evaluation"
    / "confirmatory_v2"
    / "supervised_classifier.joblib"
)


def analyze_telemetry_v2(
    telemetry: dict[str, Any],
    *,
    enable_event_classification: bool | None = None,
    event_features: dict[str, Any] | None = None,
    model_path: str | Path | None = None,
    **inference_options: Any,
) -> dict[str, Any]:
    """Run the unchanged pipeline and optionally add a v2 event class.

    The environment switch ``SUBSENSE_EVENT_CLASSIFICATION_V2`` is off by
    default. The current telemetry contract lacks the v2 high-rate signal
    window, so callers must supply the already extracted v2 feature mapping;
    otherwise the enabled output explicitly abstains as ``UNKNOWN``.
    """
    result = analyze_telemetry(telemetry, **inference_options)
    enabled = (
        _environment_switch()
        if enable_event_classification is None
        else bool(enable_event_classification)
    )
    if not enabled:
        return result

    if event_features is None:
        result["event_classification"] = {
            "label": "UNKNOWN",
            "confidence": None,
            "probabilities": None,
            "model_version": "event-classifier-v2",
            "reason": "v2_signal_window_unavailable",
        }
        return result

    selected_path = Path(model_path) if model_path else _DEFAULT_MODEL_PATH
    classifier = _load_classifier(str(selected_path))
    label, probabilities = classifier.predict_one(event_features)
    result["event_classification"] = {
        "label": label,
        "confidence": max(probabilities.values()),
        "probabilities": probabilities,
        "model_version": "event-classifier-v2",
        "reason": None,
    }
    return result


def _environment_switch() -> bool:
    value = os.getenv("SUBSENSE_EVENT_CLASSIFICATION_V2", "false").strip().lower()
    if value not in {"true", "false", "1", "0"}:
        raise ValueError(
            "SUBSENSE_EVENT_CLASSIFICATION_V2 must be one of true, false, 1, or 0"
        )
    return value in {"true", "1"}


@lru_cache(maxsize=2)
def _load_classifier(path: str) -> SupervisedClassifierV2:
    model_path = Path(path)
    if not model_path.is_file():
        raise FileNotFoundError(
            f"v2 event-classifier artifact is not available: {model_path}"
        )
    classifier = joblib.load(model_path)
    if not isinstance(classifier, SupervisedClassifierV2):
        raise TypeError(f"unexpected v2 classifier artifact type: {type(classifier)!r}")
    return classifier
