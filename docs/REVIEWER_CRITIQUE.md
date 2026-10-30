# Skeptical reviewer critique

Date: 2026-10-27. This is an internal adversarial review, not external peer review.

| Criticism | Classification | Evidence / action |
|---|---|---|
| No real sensor or mine data supports field accuracy | Requires external validation | State prominently; all results are simulation-only |
| No universal advantage over simple baselines; current spatial method loses F1 on selected tilt scenarios | Mitigated, residual risk | Report paired results and negative findings in `evaluation/CONFIRMATORY_ANALYSIS.md`; no winner claim |
| The purported nuisance false-alarm endpoint is reused from baseline-drift controls for every scenario | Fixed only for interpretation; output defect unresolved | v1 outputs preserved; do not interpret per scenario. Correct metric needs new, versioned analysis and untouched seeds |
| Fixed operating points are not calibrated to a common false-alarm budget | Unresolved | `PROTOCOL.md` explicitly limits interpretation; calibration study would need a new frozen protocol and partition |
| Temporal ablation is identical in the core gradual-tilt result | Mitigated, residual risk | Test establishes code paths can differ; confirmatory scenario does not show incremental benefit |
| Dropout scenario does not test outage alarms | Unresolved | Unsupported condition is disclosed; detector methods consume feature rows and do not detect freshness |
| Simulator distributions are not physically grounded; no sensitivity sweep | Unresolved | Parameter inventory distinguishes assumptions; sensitivity sweep not run |
| Security uses a shared bearer key, not payload HMAC, and replay protection is volatile | Unresolved | See `THREAT_MODEL.md`; source downgrade is only partial mitigation |
| Docker/MQTT/dashboard chain is not proven end to end | Requires external/environment validation | Existing audit records Docker unavailable and broker path not established; dashboard production build alone is not end-to-end evidence |
| No paper, verified novelty analysis, or independent review existed at baseline | Unresolved | Current package adds this critique, model/data provenance artifacts and a claim validator; no publication-level novelty claim is made |
| Model provenance and external compatibility are incompletely verified | Mitigated, residual risk | Artifact hashes and runtime versions can be generated; clean environment compatibility is not proven |
| The recorded 64.5-minute synthetic CSV cannot support long-horizon false-alarm claims | Not fixable with current data | Report exposure and short duration honestly; no rule-of-three low-rate claim |

## ML reviewer conclusion

The registered simulated results are mixed, and code-fixed thresholds do not equalize false-alarm operating points. Per-seed analysis is preferable to row-wise pseudo-replication, but results remain tied to a programmed data generator. No broad detector superiority conclusion is supported. The nuisance endpoint defect materially limits any claim about nuisance rejection.

## Measurement and simulation reviewer conclusion

The code has explicit scenario labels and seed control, but the simulated noise and physical transfer behavior lack empirical grounding. Scenarios test the programmed signatures. No sensitivity sweep or hardware characterization establishes that those signatures resemble a mine or the intended sensor installation.

## Systems reviewer conclusion

Model/mock mode is more observable and the unauthenticated source downgrade is useful. Shared-secret checks do not provide message integrity, durable replay defense, device enrollment, or physical identity. Full broker/database/dashboard integration and failure recovery remain unverified.

## Publication reviewer conclusion

The current artifacts support a reproducible simulation benchmark report, not field validation or a novel deployed method. A publication submission needs verified related work, a corrected separately versioned nuisance analysis, stronger calibrated comparison, code and artifact audit, and external review. Authorship and rights need owner verification before submission.
