# Reproduce evaluation tables

All data used here is simulated. The only bundled sensor CSV is
`docs/evaluation/placeholder_data/sensor_data.csv`: 38,700 data rows spanning
exactly 3,869.9 seconds (1 hour, 4 minutes, 29.9 seconds). It is synthetic
placeholder data, not a hardware recording.

## Regenerate the checked-in report

From the repository root in PowerShell:

```powershell
.\scripts\reproduce.ps1
```

By default this rebuilds the Markdown tables and figures from the existing
`docs/evaluation/results.csv`; it does not generate new evaluation data.
Review the report and CSV together before publishing any changed metric
interpretation.

## Run a reduced exploratory evaluation

```powershell
.\scripts\reproduce.ps1 -RunEvaluation
```

This writes a separate one-seed exploratory run under
`docs/evaluation/reproduction_run/` and does not replace the checked-in
results. The larger evaluation has exceeded the 15-minute budget, so this
script uses fewer seeds for the new run. One-seed intervals are degenerate,
not uncertainty estimates, and must not be presented as confirmatory results.
The output report identifies its seed count and seed ranges.

## Test suites

The GitHub Actions workflow runs both suites. Locally, from the repository
root, run:

```powershell
..\.venv\Scripts\python.exe -m pytest ai_engine\tests -q
Push-Location backend
..\..\.venv\Scripts\python.exe -m pytest tests -q
Pop-Location
```

## End-to-end scope

`scripts/run_e2e_inprocess.py` exercises REST telemetry and `/api/system/status`
inside the process and records its actual response data in
`docs/evaluation/e2e_run.md`. Database persistence and detector processing are
stubbed for that check. The Docker/MQTT chain was NOT RUN.
