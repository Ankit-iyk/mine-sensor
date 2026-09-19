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
- Temporal features: next

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
