# SUBSENSE project status

Status date: 2026-11-09. Branch: `ai-ml-development`.

## Verified state

- The AI-engine suite passed with 125 tests; the backend suite passed with 130
  tests and 2 upstream deprecation warnings on the current code. Both were run
  sequentially from the requested working directories.
- `tools/validate_claims.py` passed for all 8 paper-ledger claims, with evidence
  files and selectors resolved.
- `.github/workflows/tests.yml` runs the AI-engine suite from the repository
  root and the backend suite from `backend/`. This file was inspected; no
  remote Actions result for the latest commit is claimed here.
- Telemetry authentication uses per-node HMAC-SHA256 over
  `node_id|timestamp|nonce|canonical_payload`, enforces timestamp freshness,
  compares signatures with `hmac.compare_digest`, and keeps a bounded,
  process-local nonce cache. Tests cover invalid signatures and fields,
  tampering, replay, expiry, simulator classification, and status transitions.
- The frozen confirmatory benchmark remains simulation-only. Its existing
  results cover the registered scenario matrix; the nuisance false-alarm
  endpoint is shared across scenario rows and cannot support per-scenario
  nuisance conclusions.
- `docs/FINAL_AUDIT.md` records the exact CSV metrics, code path for the
  non-tilt alert gate, resampling method, and current evidence-based scorecard.
- The README status table distinguishes Verified, Simulated only, and Untested.
- The contributor roles in `docs/AUTHORSHIP.md` are project-owner-provided and
  use first names only. AI-assisted code generation is disclosed.
- `sensor_data.csv` is synthetic placeholder data: 38,700 data rows over
  3,869.9 seconds (1 hour, 4 minutes, 29.9 seconds), not a hardware recording.

## Known failure and measurement limits

The evaluation's `current_system` gates raw Isolation Forest positives on
tilt or baseline deviation. On some coded non-tilt scenarios, the standalone
forest flags events while the integrated rule suppresses them. The identified
behavior is documented with code locations and existing confirmatory CSV rows
in `docs/FINAL_AUDIT.md`. Correcting it requires a new frozen protocol; no
evaluation was run for this update.

The nuisance metric is measured on a shared baseline-drift control and copied
into scenario summaries. Neither the README nor the revised paper uses it to
claim nuisance-alarm rejection. The existing frozen result files and protocol
were not edited.

## Not verified or not run

- No new evaluation run or result file was created.
- The Docker/MQTT/database/dashboard chain, hardware recording, physical
  calibration, and deployment pilot were not run.
- A remote GitHub Actions result for the latest commit was not checked.
- The paper remains a draft: Related Work is an author placeholder, author
  affiliations need confirmation, and a LaTeX build was not run during this
  update.
- There is no forecasting evaluation, mine trial, safety case, or independent
  external review.

The system and all empirical claims remain research/simulation scoped. This
repository does not establish operational mine-safety capability.
