# SUBSENSE telemetry threat model

Status date: 2026-11-02. This describes the inspected prototype, not a security certification.

## Assets and trust boundaries

Assets include telemetry integrity, device/source status, model and risk
outputs, broker credentials, per-node secrets, and database availability.
Untrusted input crosses the MQTT broker and REST ingestion route. Device keys
are configured per `node_id`; enrollment, rotation, and revocation are
currently out-of-band.

## Signed LIVE messages

REST and MQTT ingestion use `backend/app/ingestion/device_auth.py`. The
backend selects a unique key from `HARDWARE_DEVICE_KEYS` by `node_id` and
verifies a lowercase HMAC-SHA256 hex signature. The signed message is
canonical UTF-8 JSON with sorted keys, compact separators, and all input
fields except `signature`; `timestamp` and `nonce` are therefore included in
the MAC. The backend requires a timezone-aware timestamp within 60 seconds of
its clock, a 16–128 character nonce, and a configured secret of at least 32
UTF-8 bytes. `hmac.compare_digest` checks the MAC.

Nonce uniqueness is enforced per node using a locked in-process cache. It
retains entries for 120 seconds and fails closed if the cache reaches its
100,000-entry cap. Restarting the process clears that cache, so this is not
durable replay protection. LIVE status is updated only by the REST/MQTT
ingestion paths after successful signature verification. Unauthenticated
`source="hardware"` is classified as `unknown`. A `source="simulator"` payload
is kept SIMULATED even if it carries a valid signature; the simulator strips
signature and nonce fields before publish.

## Threat coverage

| Threat | Current mitigation | Residual status |
|---|---|---|
| Forged `source="hardware"` without a key | Source is downgraded to `unknown`; source text alone never marks LIVE | MITIGATED for the inspected REST and MQTT ingestion paths |
| Wrong, absent, or modified HMAC | Unknown node, missing signature, or invalid HMAC is rejected as hardware proof | MITIGATED for message integrity when keys remain secret |
| Replay and stale timestamps | Per-node nonce cache and a 60-second timestamp window | PARTIAL: in-memory cache clears on restart; synchronized clocks are required |
| Payload tampering | MAC covers the canonical payload, including timestamp and nonce | MITIGATED for in-transit edits without the node key; compromised keys remain a risk |
| Simulator traffic claiming LIVE | Simulator publisher forces the simulator source and removes auth fields; simulator source is never classified as hardware | MITIGATED in the checked-in simulator path |
| Unknown device enrollment | Keys are mapped by configured node ID | PARTIAL: no enrollment service or identity proof |
| Key disclosure, rotation, and revocation | Per-node secrets are read from configuration | UNRESOLVED lifecycle and protected provisioning |
| Denial of service | Nonce cache is bounded and fails closed | UNRESOLVED endpoint/broker rate limits, resource quotas, and availability controls |
| Process restart or clock manipulation | Timestamp freshness limits exposure; tracker and replay cache are in memory | UNRESOLVED durable replay state, clock trust, and persistent status |
| Physical spoofing or bad sensor measurements | HMAC authenticates possession of a configured key only | OUT OF SCOPE: it cannot prove the sender is an ESP32 or validate physical measurements |

## Out of scope and required deployment controls

This prototype does not implement device enrollment, secure key provisioning,
rotation/revocation, durable replay storage, transport authentication,
per-device authorization policies, rate limiting, broker ACL validation,
secret redaction across infrastructure logs, or operational incident
response. HMAC does not encrypt data or authenticate the physical sensor.
Deployment still requires TLS, broker ACLs, protected secret storage, clock
synchronization, durable replay handling, monitoring, recovery procedures,
and an environment-specific security assessment.

## Test evidence and classification

Backend tests cover wrong keys, missing signatures, replayed nonces, expired
timestamps, forged hardware source labels, simulator classification, and the
OFFLINE → SIMULATED → LIVE → OFFLINE status path. These are in-process
software tests; the Docker/MQTT/broker chain and physical hardware were not
run or validated. Cryptographic message integrity is mitigated under the
configured-key assumptions; durable replay defense, enrollment, key lifecycle,
availability controls, and physical identity remain unresolved or external.
