# SUBSENSE — ML Model Integration Contract

## Purpose

This document defines the contract between:

- **My responsibility** (backend/runtime owner)  
- **Your responsibility** (ML model owner)

The entire system is designed so the ML model can be **dropped in** at any point
without requiring any changes to the backend's ingestion, risk engine, or dashboard.

---

## What the backend provides to the model

A feature vector dict at each inference call:

```python
{
    "node_id":              "N01",          # str
    "timestamp":            "...",          # ISO-8601 UTC string

    # Tilt features
    "tilt_x":               1.24,           # float, degrees
    "tilt_y":               0.83,           # float, degrees
    "tilt_deviation":       0.24,           # float, deviation from node baseline
    "tilt_rate":            0.04,           # float, degrees/second

    # Vibration features
    "vibration_raw":        512,            # int, ADC count 0–1023
    "vibration_intensity":  0.50,           # float, normalised 0.0–1.0
    "vibration_frequency":  0.12,           # float, events per second in rolling window

    # Rolling statistics (configurable window — default 60 readings)
    "rolling_mean_tilt":    1.18,           # float
    "rolling_std_tilt":     0.08,           # float
    "rolling_mean_vib":     0.10,           # float
    "rolling_std_vib":      0.05,           # float

    # Temporal features
    "persistence":          0.42,           # float, fraction of window that is anomalous
    "trend_slope":          0.003,          # float, tilt change rate over medium window
}
```

**Type**: `dict[str, float | int | str]`  
The backend constructs this dict from processed sensor data.

---

## What the backend expects back from the model

```python
{
    "anomaly_score":    0.82,           # float in [0.0, 1.0]
                                        # higher = more anomalous
    "state":            "ANOMALOUS",    # str: "NORMAL" | "MICRO_ANOMALY" | "ANOMALOUS"
    "model_version":    "iforest-v1.0", # str, for traceability
    "confidence":       0.91,           # float in [0.0, 1.0], optional
    "raw_score":        -0.18,          # float, raw Isolation Forest score, optional
}
```

**Type**: `dict[str, float | str]`

---

## Backend interface class

The backend defines this abstract interface.  
Your model must be wrapped in a class that implements it:

```python
# backend/app/ml/interface.py

from abc import ABC, abstractmethod
from typing import Any

class AnomalyDetector(ABC):

    @abstractmethod
    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Run inference on a single feature vector.

        Parameters
        ----------
        features    dict matching the feature vector schema above

        Returns
        -------
        dict matching the inference output schema above
        """
        ...

    @abstractmethod
    def load(self, path: str) -> None:
        """Load the model from a file (e.g. .pkl, .joblib)."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Return a version string for logging/traceability."""
        ...
```

---

## How to deliver your model to me

1. Train your `IsolationForest` (or alternative) on the normal-behaviour dataset.
2. Export using `joblib.dump(model, "anomaly_detector_v1.joblib")`.
3. Write a wrapper class that inherits `AnomalyDetector` and implements:
   - `load(path)` — loads the joblib file
   - `predict(features)` — runs inference and returns the output dict
   - `version` property
4. Place both files in `backend/app/ml/`:
   - `your_detector.py` (the wrapper class)
   - `anomaly_detector_v1.joblib` (or configure path via `ML_MODEL_PATH` in `.env`)

---

## Feature preprocessing

**Important**: The backend performs signal processing (Kalman filter, rolling
statistics) BEFORE calling `predict()`. You do **not** need to re-implement
these in the model training pipeline.

However, during training, you must apply the same normalisation/scaling that
was used to generate the training features.

If your model requires feature scaling (StandardScaler, MinMaxScaler), include
the fitted scaler inside your wrapper's `load()` method.

---

## State thresholds

The backend uses the `anomaly_score` to decide the state label:

```
0.0 – 0.3  →  NORMAL
0.3 – 0.6  →  MICRO_ANOMALY
0.6 – 1.0  →  ANOMALOUS
```

These thresholds are **configurable** in `backend/app/ml/interface.py`.
If your model produces scores in a different range, document it and I will
adjust the thresholds accordingly.

---

## What the mock model does (until your model is ready)

`backend/app/ml/mock_model.py` produces:

- `anomaly_score = 0.05` (always)
- `state = "NORMAL"`
- `model_version = "mock-0.1.0"`

This lets the entire risk pipeline be developed and tested before your model
is ready. When your model is plugged in, **no other code changes are needed**.

---

## Questions? Coordinate via:

- Feature vector schema changes → update this document and `backend/app/ml/interface.py`
- Score range changes → inform the backend owner so thresholds can be adjusted
- New features needed → add to the feature pipeline in `backend/app/processing/features.py`
