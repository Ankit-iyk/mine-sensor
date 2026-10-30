# Reproduction and artifact verification

This procedure targets the repository state audited on 2026-10-27. Use the parent workspace virtual environment at `..\.venv\Scripts\python.exe` from this repository directory.

## Registered simulation outputs

The frozen v1 run is already present under `docs/evaluation/confirmatory_v1/` and is reproduced with:

```powershell
..\.venv\Scripts\python.exe -m ai_engine.evaluation.run_all --seeds 30 --output-dir docs/evaluation/confirmatory_reproduction
```

That command uses the frozen default test seed bases. Compare protocol and output hashes in the generated `metadata.json`; do not overwrite or replace `confirmatory_v1` when rerunning. The historical v1 nuisance metric caveat remains applicable.

## Local checks

```powershell
..\.venv\Scripts\python.exe -m pytest ai_engine/tests -q --basetemp=.test-tmp/ai
..\.venv\Scripts\python.exe -m ai_engine.evaluation.run_all --seeds 1 --test-seed-base 990000 --shift-seed-base 991000 --output-dir docs/evaluation/final_smoke
..\.venv\Scripts\python.exe tools/validate_claims.py
..\.venv\Scripts\python.exe tools/artifact_manifest.py
```

For the backend suite, run from `backend/` with the same parent interpreter: `..\..\.venv\Scripts\python.exe -m pytest tests -q --basetemp=..\.test-tmp\backend`. On this Windows machine, the backend suite stalled inside the sandbox during asyncio/socket setup, so the recorded full run was outside the sandbox. If Python's system temp root is protected, point `TEMP` and `TMP` to `.test-tmp` before the evaluation command. The dashboard production build passed in the baseline audit; Docker/MQTT/database/browser end-to-end testing was not established. The compiler status for `paper/` is reported in `docs/FINAL_AUDIT.md`.

## Artifact scope

`tools/artifact_manifest.py` hashes the model, frozen protocol, and key confirmatory CSV/metadata files. It does not hash the whole repository or guarantee a clean environment. The model is a joblib artifact and should only be loaded from a trusted source. Do not use this simulation model for field safety decisions.
