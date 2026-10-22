# AI Engine

The AI engine supplies feature processing, Isolation Forest inference, and
supporting temporal, spatial, fingerprint, risk, and explanation components.
The backend uses `AIEngineDetector` from `ai_engine/adapter.py` to map backend
`FeatureVector` dictionaries to the model's 11 input columns. The backend
`app.ml.loader.get_detector()` loads `ai_engine/models/isolation_forest.joblib`
and returns the adapter; if the model cannot be loaded, it logs the error and
falls back to `MockAnomalyDetector`.

## Setup and model training

Install backend dependencies (which include the AI engine's runtime
dependencies):

```powershell
python -m pip install -r backend\requirements.txt
```

From the repository root, train the checked-in detector using normal simulator
readings passed through the backend filter, buffer, baseline tracker, and
feature extractor. Training is performed in-process without MQTT or a
database:

```powershell
python -m ai_engine.training.train_from_backend
```

This writes `ai_engine/models/isolation_forest.joblib` and prints training-row
and feature statistics. The model artifact is tracked in Git so a fresh clone
can load the AI detector without retraining.

## Tests

Run AI engine tests from the repository root:

```powershell
python -m pytest ai_engine/tests -q
```

Run backend tests from `backend/`:

```powershell
python -m pytest -q
```

## Demo

From the repository root, run the five simulator scenarios through the backend
processing pipeline and detector without Docker, MQTT, or database writes:

```powershell
python scripts\demo_inprocess.py
```

The demo prints state fractions for each scenario and the final risk
explanation for `gradual_tilt`.
