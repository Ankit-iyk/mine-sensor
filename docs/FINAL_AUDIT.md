# SUBSENSE final audit and phase checklist

Audit date: 2026-10-27. Repository: `ai-ml-development` at starting commit `784a895a6c176b6922d95476a2199a6ae7205622`. No commit was created. The original uncommitted user change in `ai_engine/evaluation/run_all.py` was inspected and preserved.

## Evidence-based scorecard

Scoring rubric used for both baseline and current state: 0–2 means largely absent or unverified; 3–4 means partial implementation with limited checks; 5–6 means core behavior and local evidence exist but material integration or validation gaps remain; 7–8 means independently reproducible, robustly integrated evidence; 9–10 requires strong independent validation and, where relevant, real deployment evidence. Scores measure evidence, not effort or feature count.

| Domain | Baseline | Current | Evidence and remaining ceiling |
|---|---:|---:|---|
| Working implementation | 4/10 | 5/10 | AI and backend suites pass; dashboard production build passed; fallback mode is now observable; API source rejects unauthenticated hardware claims. Docker/MQTT/browser integration, HMAC/replay protection, security threat coverage, and real hardware are not verified. Ceiling with local code alone is roughly 7; physical identity and sensor behavior require hardware evidence. |
| Reasoning and rigor | 3/10 | 6/10 | A protocol was frozen before disjoint 30-seed evaluation; paired seed-level bootstrap/sign-flip/Holm outputs and provenance hashes are present. Results are simulation-only, thresholds are not calibrated to a shared false-alarm budget, and analysis found a repeated nuisance-rate metric that invalidates scenario-specific nuisance interpretations. Sensitivity and robust operating-point studies remain. |
| Preprint readiness | 1/10 | 2/10 | Data/method audit, protocol, run artifacts, and candid analysis exist. There is no verified related-work package, manuscript, claims ledger, model card, datasheet, or reproducible paper build. Even a complete simulation paper cannot claim field validation. |
| Impact | 2/10 | 2/10 | The problem has potential relevance and the code may support a simulation benchmark. No independent adoption, publication, physical recording, mine trial, or external validation was established. Local work cannot raise demonstrated external impact. |

Before scores are reconstructed from the inspected baseline evidence, not from a prior formal scorecard. The unchanged explicit rubric is applied to the new evidence. The current result does not justify a 9/10 in any domain.

## What existed, changed, and was learned

- The checkout already had an AI/backend/dashboard pipeline, model artifact, historical evaluation, synthetic placeholder CSVs, and a dirty user-authored `run_all.py` change.
- Phase 0 recorded environment, tests, dataset coverage, dashboard build, model and evaluation state. Available sensor CSV coverage is about 64.5 minutes, not two hours.
- Phase 1 made model/mock status observable, logged missing-model fallback, added score-semantics and temporal-path tests, and verified the documented unit/feature mapping. The telemetry source still does not have signed-message replay protection.
- Phase 2 froze protocol SHA-256 `2dd1833ebd31c269ea1d720538900887cccbfb44a072b6b05c339e4dff91ea58`, added controlled simulated scenarios and paired statistics, and completed the disjoint 30-seed confirmatory run.
- Results do not show a universal winner. Simple baselines outperform the current spatial system on several coded tilt scenarios; the forest performs strongly for selected vibration signatures but poorly for acceleration-only events. The no-temporal ablation is identical on gradual tilt, although the targeted test shows the inference paths can diverge on a designed sequence.
- The generated nuisance false-alarm metric repeats the shared baseline-drift control episode across scenario rows. Preserve that result but do not cite it as a per-scenario nuisance rate. See [`evaluation/CONFIRMATORY_ANALYSIS.md`](evaluation/CONFIRMATORY_ANALYSIS.md).
- Nothing here establishes real-mine predictive capability, hardware accuracy, safety benefit, or prevention of incidents.

## Verification record

| Verification | Command/result | Evidence |
|---|---|---|
| Baseline AI tests | `python -m pytest ai_engine/tests -q --junitxml=docs/evaluation/baseline_ai_tests.xml` — 111 passed, exit 0 | `evaluation/baseline_ai_tests.xml` |
| Baseline backend tests | `python -m pytest -q --junitxml=../docs/evaluation/baseline_backend_tests.xml` — 119 passed, 2 warnings, exit 0 (outside sandbox for Windows asyncio socketpair) | `evaluation/baseline_backend_tests.xml` |
| Phase 1 AI/backend | 113 and 120 passed respectively; exit 0 | `evaluation/phase1_test_report.json`, JUnit files |
| Phase 2 AI/backend | 125 and 120 passed respectively; exit 0; backend has 2 dependency warnings | `evaluation/phase2_test_report.json`, JUnit files |
| Registered evaluation | `python -m ai_engine.evaluation.run_all --seeds 30 --output-dir docs/evaluation/confirmatory_v1` — exit 0; 710 aggregate, 21,300 raw, 1,600 paired rows | `evaluation/confirmatory_v1/metadata.json` and CSV files |
| Dashboard | `npm run build` — passed, exit 0; 4 static pages and TypeScript check | `evaluation/BASELINE_AUDIT.md` |
| Diff whitespace | `git diff --check` — passed | final local command |

Backend suites required running outside the sandbox because Windows asyncio socketpair setup stalled within the sandbox. Docker was unavailable, MQTT broker connectivity was not established, and browser status behavior was not checked. The 30-seed run is simulation, not an integration test.

## Master checklist

| Status | Major task | Evidence / remaining work |
|---|---|---|
| DONE | Preserve user changes and establish baseline repository, data, environment, and tests | `BASELINE_AUDIT.md`, `baseline_test_report.json`; dirty starting edit preserved |
| DONE | Fix and test detector-mode fallback visibility and score semantics | `PHASE1_CORRECTNESS.md`, phase 1 tests and report |
| DONE | Add a temporal ablation path test | `ai_engine/tests/test_evaluation_methods.py`; full phase 1 suite |
| DONE | Freeze protocol before confirmatory run and add registered simulator scenarios | `PROTOCOL.md`, `protocol_freeze.json`, `PHASE2_REPORT.md` |
| PARTIAL | Fair method comparison | Same scenario/seed rows and fixed thresholds; no equal-budget calibration, no shared false-alarm operating point |
| DONE | Complete confirmatory run and preserve raw, aggregate, paired, metadata, figures, and unsupported case | `confirmatory_v1/`; metadata output hashes verified |
| PARTIAL | Interpret baseline, forest, temporal and spatial outcomes | `CONFIRMATORY_ANALYSIS.md`; generated nuisance rate has a scenario scope bug; no broad added-value conclusion |
| PARTIAL | Simulator parameter inventory and sensitivity sweep | `evaluation/SIMULATOR_PARAMETERS.md` inventories assumptions; no parameter sweep was run |
| PARTIAL | Source authentication and status trust review | Existing static key/source downgrade inspected; missing HMAC, replay defense, enrollment, persistent identity, and rotation tests |
| PARTIAL | Threat model and secure telemetry | `docs/THREAT_MODEL.md`; design documented, but HMAC, durable replay protection, enrollment, and lifecycle implementation remain absent |
| DONE | In-process telemetry-to-risk API integration test | `backend/tests/test_inprocess_telemetry_pipeline.py`; 1 passed, with database persistence stubbed |
| NOT RUN | Docker/MQTT/dashboard end-to-end test | Docker unavailable; no physical device |
| PARTIAL | Dashboard verification | Production build passed; browser/API status behavior not inspected |
| PARTIAL | Reproduction procedure, dependency lock strategy, CI, contribution/authorship and release docs | `docs/REPRODUCE.md` added; lock strategy, CI, contribution/authorship and release docs remain incomplete |
| PARTIAL | Public benchmark/deployment plan and verified literature novelty matrix | Three bibliography entries were checked; a domain literature review and novelty matrix remain incomplete |
| PARTIAL | Preprint, claims ledger validator, model card, datasheet, reviewer critique | Draft `paper/main.tex`, 10-row ledger and validator pass; model/data cards and critique exist; LaTeX compile timed out during format downloads; no publication-ready manuscript |
| PARTIAL | Model artifact release readiness | Existing artifact inspected and hashed in baseline audit; full clean-environment provenance/retraining verification not completed |
| PARTIAL | Adversarial review | `docs/REVIEWER_CRITIQUE.md` records four perspectives; no independent reviewer was involved |
| PARTIAL | Final reproduction and release audit | Updated test suites, smoke evaluation, claim validation and manifest ran; no clean checkout or 30-seed rerun of the final tree; no commit, push, publication, or release |
| REQUIRES EXTERNAL VALIDATION | Physical sensor calibration, mine performance, field safety and external adoption | Cannot be established from current simulator or software tests |

## Final repository state and authorization boundaries

The worktree intentionally contains source changes, generated evaluation artifacts, reports, and the original user modification. No staging, commit, push, publication, or release was performed. Docker, broker, physical hardware, independent review, and external adoption remain unverified. The project is not release-ready as a field safety system. Completing a preprint package, selecting a publication venue, licensing contributions, and publishing would require verified authorship/rights and owner decisions.

## Continuation record (2026-10-27)

This continuation preserves the original audit above and adds the following artifacts after that audit was written:

- Added `MODEL_CARD.md`, `DATASHEET.md`, `docs/THREAT_MODEL.md`, `docs/REVIEWER_CRITIQUE.md`, `docs/evaluation/SIMULATOR_PARAMETERS.md`, and `docs/REPRODUCE.md`.
- Added a cautious LaTeX draft in `paper/main.tex`, an explicitly limited bibliography in `paper/references.bib`, and `paper/claims_ledger.csv`. This is a draft, not a submission-ready paper; novelty review, broader related work, author confirmation, and rights checks remain open.
- Added `tools/validate_claims.py`. Command `..\.venv\Scripts\python.exe tools\validate_claims.py` passed: 10 ledger rows, referenced files resolved, result selectors matched CSV rows, and the citation key resolved in the bibliography.
- Added `tools/artifact_manifest.py` and its captured selected-artifact inventory at `docs/evaluation/artifact_manifest.json`. The model is 1,117,737 bytes with SHA-256 `5ce973c38507aa717989d5b77efc614a971fe98b9cab96e41c83a7cb55de4692`. This hashes the declared files, not the entire checkout.
- Fresh AI suite: `..\.venv\Scripts\python.exe -m pytest ai_engine\tests -q --basetemp=.test-tmp\final-ai --junitxml=docs\evaluation\final_ai_tests.xml` — 125 passed, exit 0. An initial invocation using the protected system temp root had 15 pytest fixture setup errors; the repository-local temp rerun passed.
- New in-process integration check: `backend/tests/test_inprocess_telemetry_pipeline.py` passed 1 test, exit 0. It posts simulated readings through the FastAPI route and real `ProcessingPipeline`, reaches a risk result, checks explicit detector mode, and confirms SIMULATED status. Database persistence is stubbed; it is not a broker/database/deployment test.
- Fresh backend suite after adding the integration test: `..\..\.venv\Scripts\python.exe -m pytest tests -q --basetemp=..\.test-tmp\final-backend-rerun --junitxml=..\docs\evaluation\final_backend_tests.xml` from `backend/` — 121 passed, exit 0, two dependency deprecation warnings (`docs/evaluation/final_backend_tests.xml`).
- LaTeX compilation through the built-in compiler was attempted. It timed out while fetching the initial Tectonic/TeX format and package files; **BLOCKED**, not compiled. The source-level claim ledger validation passed.
- A final one-seed smoke run first failed because its temporary model artifact was written under a sandbox-protected Windows temp folder. It was restarted with `TEMP` and `TMP` redirected to `.test-tmp`: `..\.venv\Scripts\python.exe -m ai_engine.evaluation.run_all --seeds 1 --test-seed-base 990000 --shift-seed-base 991000 --output-dir docs\evaluation\final_smoke` — exit 0. It generated 710 summary rows, 710 per-seed rows, 1,600 paired rows, and one unsupported-condition row. All eight files listed in `final_smoke/metadata.json` had matching SHA-256 hashes. The failed first invocation is not counted as a result.
- `Get-Command docker` found no Docker executable in this environment; no Docker stack, broker, or live dashboard chain was tested.
- The selected protocol and confirmatory outputs remain those of `confirmatory_v1`; no new confirmatory evaluation was conducted in this continuation. Sensitivity analysis, corrected nuisance-rate experiment, performance timing, authenticated HMAC/replay implementation, full in-process telemetry-to-risk path, Docker/MQTT/dashboard chain, and clean-environment reproduction remain incomplete or blocked.

Scores remain evidence-based under the rubric above: working implementation 5/10; reasoning and rigor 6/10; preprint readiness 2/10; impact 2/10. The added documentation and claim checks improve traceability but do not establish stronger field evidence, a corrected experiment, a security certification, novelty, external adoption, or physical validation. No score is raised based only on task completion.
