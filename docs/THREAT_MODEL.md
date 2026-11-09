# SUBSENSE telemetry threat model

Status date: 2026-11-09. This describes the checked-in application code and
tests; it is not a security certification or deployment assessment.

## Trust boundary and signed format

REST and MQTT telemetry are untrusted until authenticated by
`backend/app/ingestion/device_auth.py`. The backend looks up a per-node secret
in `HARDWARE_DEVICE_KEYS` by `node_id`; each configured key must contain at
least 32 UTF-8 bytes.

The HMAC-SHA256 input is the UTF-8 encoding of
`node_id|timestamp|nonce|canonical_payload`. The first three fields are
separately included in that order. `canonical_payload` is sorted, compact
UTF-8 JSON containing all remaining message fields except `node_id`,
`timestamp`, `nonce`, and `signature`. Thus the source label and telemetry
values are authenticated as part of the payload. The signature is a lowercase
hex digest, compared with `hmac.compare_digest`.

The timestamp must be timezone-aware and within 60 seconds of the backend
clock. A nonce must match the 16–128 character allowlist. Successfully
authenticated non-simulator traffic is classified internally as hardware;
unsigned or invalid hardware claims become `unknown`. A simulator source is
always classified as `simulator`, including when the payload has a valid
signature. The checked-in simulator forces that source label and removes
signature and nonce fields before publishing.

## Covered by the implementation

| Threat / property | Implemented behavior | Boundary of the claim |
|---|---|---|
| Forged hardware source label | A source string alone cannot produce LIVE status. Hardware status is recorded only after successful HMAC verification. | Applies to the inspected REST and MQTT ingestion paths. |
| Wrong device key or modified signed fields | The per-node key verifies the MAC over the node ID, timestamp, nonce, and canonical payload. | Protects message integrity/authenticity only while the configured secret is secret; it does not prove a physical device identity. |
| Stale message | Timezone-aware timestamps outside the 60-second skew window are rejected. | Depends on a trustworthy, synchronized backend clock. |
| Replayed nonce in one process | A locked cache tracks `(node_id, nonce)` for 120 seconds, has a 100,000-entry cap, and rejects new messages when full. | Cache state is local to one process and is lost on restart. |
| Simulator claiming LIVE | Simulator source is classified as SIMULATED even with a valid signature; the publisher also forces the simulator source and strips auth fields. | Prevents LIVE classification in the checked-in application/simulator path; it does not prevent an attacker from causing SIMULATED status. |
| Signature equality timing | `hmac.compare_digest` compares the expected and supplied digest. | Does not address timing or side channels elsewhere in the service. |

Backend tests exercise wrong keys, tampered payloads, missing signed fields,
replayed nonces, expired timestamps, forged hardware labels, simulator
classification, and the in-process OFFLINE → SIMULATED → LIVE → OFFLINE path.
They do not exercise a live broker or hardware.

## Not covered

- **Physical identity or sensor truth:** possession of a configured key does
  not prove that a sender is an ESP32, that a sensor is calibrated, or that a
  reading is physically accurate.
- **Secret lifecycle:** enrollment, protected provisioning, rotation,
  revocation, hardware-backed storage, and recovery after key compromise are
  not implemented.
- **Cross-process or durable replay protection:** each worker has its own
  volatile nonce cache. Restarts and multiple workers do not share replay
  state. The timestamp window limits stale reuse but is not a durable replay
  database.
- **Transport security:** HMAC does not encrypt traffic. TLS, broker ACLs,
  REST access control, and secure secret delivery are deployment
  responsibilities and have not been verified here.
- **Availability:** there is no request or broker rate limiting, resource
  quota, or denial-of-service protection. The nonce-cache cap bounds that
  cache, but fail-closed behavior can reject legitimate telemetry when full.
- **Clock trust, authorization policy, and operational response:** clock
  synchronization, node-to-zone authorization, audit retention, alerting,
  incident response, and recovery are not established by these checks.
- **End-to-end deployment:** Docker/MQTT/database/dashboard integration and
  physical hardware were not run as part of this verification.

Do not treat this implementation as a production security boundary or as
evidence of mine-safety capability.
