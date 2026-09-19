# AI Engine Progress

## Current Status

- Branch: `ai-ml-development`
- Package structure: scaffolded
- Telemetry validation: implemented and tested
- Filtering: implemented and tested
- Normalization: implemented and tested
- Module 1 preprocessing: complete
- Synthetic test dataset: implemented and tested in the top-level `simulator/` package
- Tilt features: implemented and tested
- Vibration features: implemented and tested
- Temporal features: implemented and tested
- Feature extractor: implemented and tested
- Module 2 feature engineering: complete
- Ground Stability Fingerprint: implemented and tested
- Normal-behaviour training dataset: implemented and tested
- Isolation Forest training and scoring: implemented and tested
- Anomaly detector interface: implemented and tested
- Temporal intelligence: implemented and tested
- Spatial intelligence: next

## Setup

Install dependencies from the repository root:

```powershell
pip install -r ai_engine\requirements.txt
```

Run the validation tests:

```powershell
python -m pytest ai_engine\tests\test_validation.py -v
```

## Working Agreement

Development happens on `ai-ml-development`; do not work directly on `main`.
