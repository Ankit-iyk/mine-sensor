# Phase 2 protocol and scenario implementation

Date: 2026-10-27 (Asia/Calcutta)

## Frozen protocol

- Protocol: `PROTOCOL.md`.
- Immutable identifier: SHA-256 `2dd1833ebd31c269ea1d720538900887cccbfb44a072b6b05c339e4dff91ea58` (`protocol_freeze.json`).
- The historical held-out families 10000–10011 and 200000–200011 were inspected and excluded. Confirmatory families are ordinary 300000–300029 and shifted 400000–400029. A non-overlapping smoke-only pair used 900000 and 910000.
- Existing method thresholds were frozen at their code-defined values. No parameter was tuned on the confirmatory partition. This is explicitly not a common calibrated false-alarm-budget comparison.
- Unit of analysis is a seed episode. Method comparisons use identical generated feature rows within each scenario/noise/seed.

## Added controlled simulator conditions

The registry now contains 16 scenarios: the eight historical conditions plus acceleration-only, combined vibration/acceleration, correlated multi-node drift, packet dropout, sampling jitter, impulse nuisance, phone-like vibration nuisance, and mixed tilt/vibration events. Each row identifies simulation origin, scenario, severity, event ID and onset metadata where applicable. Generator tests verify node scope, labels, onset, duration metadata, nuisance labeling, data gaps, and deterministic simulator semantics.

All new numerical values are simulation assumptions. They are not manufacturer specifications or realistic mine recordings. Packet dropout is generated as absent rows with a recorded recovery gap, but packet-freshness detection is unsupported by the compared feature methods; `unsupported_conditions.csv` states that limitation. The dropout scenario's empty event metrics are not evidence of successful outage detection.

## Evaluation outputs added

The evaluation now writes per-seed raw metrics, paired bootstrap intervals, paired sign-flip tests, Holm-adjusted p-values, machine-readable run metadata with dependency/source/model/protocol/output hashes, and an explicit unsupported-conditions file. The original historical `results.csv` was left unchanged.

## Verification so far

- Scenario/statistics targeted tests passed: 23 passed.
- Full AI-engine suite: 125 passed, exit 0 (`phase2_ai_tests.xml`).
- Full backend suite: 120 passed, 2 dependency deprecation warnings, exit 0 (`phase2_backend_tests.xml`). It ran outside the sandbox for local Windows asyncio socketpair access.
- Smoke command: `python -m ai_engine.evaluation.run_all --seeds 1 --test-seed-base 900000 --shift-seed-base 910000 --output-dir docs/evaluation/phase2_smoke` (exit 0). It generated 710 summary rows, 710 per-seed records, and 1,600 paired comparison rows. The single-seed intervals are not inferential; these outputs are development smoke artifacts only.
- All eight smoke output hashes matched the manifest in `phase2_smoke/metadata.json`; protocol hash matched the frozen identifier.

## Confirmatory run

The preregistered 30-seed run completed with exit code 0:

`python -m ai_engine.evaluation.run_all --seeds 30 --output-dir docs/evaluation/confirmatory_v1`

The default seed bases resolve to 300000 and 400000, as frozen. It generated 710 aggregate rows, 21,300 per-seed metric rows, and 1,600 paired-test rows. Every represented group has 30 seeds. The protocol hash and output hashes in `confirmatory_v1/metadata.json` were verified. Interpretation and the metric caveat found during analysis are in `CONFIRMATORY_ANALYSIS.md`; generated v1 outputs remain unchanged.
