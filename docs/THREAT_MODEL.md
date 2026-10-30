# SUBSENSE telemetry threat model

Status date: 2026-10-27. This records inspected behavior; it is not a security certification.

## Assets and trust boundaries

Assets include telemetry integrity, device/source status, model and risk outputs, broker credentials, device secrets, and database availability. Untrusted inputs cross the MQTT broker and REST ingestion route. The current backend pipeline has no demonstrated authenticated device enrollment service.

## Current behavior and limits

`backend/app/ingestion/device_auth.py` compares a single configured `hardware_device_key` using constant-time string comparison. REST expects it in `X-Hardware-Device-Key`; MQTT expects `hardware_device_key` in the JSON payload when `source` says `hardware`. Missing or incorrect values downgrade the source to `unknown`. This is a shared bearer secret, not HMAC-SHA-256 message authentication: payload fields are not cryptographically bound, timestamps/nonces are not verified, and the key is not per-device. The MQTT duplicate guard hashes exact payload bytes, stores only the last hash per topic in process memory, and is not durable replay protection. `TelemetrySourceTracker` is also in-memory. Consequently, key possession can be replayed, payload tampering is not prevented, a disclosed key enables impersonation, and process restart clears duplicate/status state.

## Threat coverage

| Threat | Current mitigation | Residual status |
|---|---|---|
| Forged `source=hardware` without key | Downgraded to `unknown` on REST and MQTT | PARTIAL: shared key is bearer proof, not physical identity |
| Invalid or missing key | Constant-time comparison; source downgrade | PARTIAL; no signed canonical payload |
| Payload tampering | None beyond transport/schema handling | UNRESOLVED |
| Replay, timestamp expiry, nonce reuse | No timestamp or nonce validation; exact duplicate guard is volatile | UNRESOLVED |
| Unknown device / enrollment | One global configured key, no device registry | UNRESOLVED |
| Key disclosure / rotation / revocation | Environment configuration only; no rotation protocol | UNRESOLVED |
| Unauthorized REST/MQTT submission | No endpoint authentication demonstrated; broker auth depends on deployment configuration | UNRESOLVED |
| Denial of service | Schema validation and broker QoS exist; no assessed rate limits or resource bounds | UNRESOLVED |
| False/suppressed alarms or failed auth infrastructure | No security monitoring or fail-closed operational acceptance test | UNRESOLVED |
| Misleading LIVE label | Freshness tracker only records messages with `source=hardware`; auth downgrade helps | PARTIAL: shared secret acceptance is not physical-device verification; status is volatile |

## Required future design

Use per-device keys provisioned through a controlled enrollment process; HMAC-SHA-256 over a versioned canonical representation that includes device ID, timestamp, nonce, and all security-relevant telemetry fields; constant-time MAC verification; bounded timestamp skew; persistent replay state with atomic nonce insertion and defined retention; key rotation/revocation; rate limits; secret redaction; and tests across restart and concurrency. An authenticated message establishes possession of an enrolled key, not that the sender is an ESP32 or that the measurements are physically valid. Deployment still needs TLS/broker ACLs, protected secret storage, monitoring, backup/recovery, and a field threat assessment.

## Classification

Mitigated: unkeyed self-assertion of hardware source is downgraded in the inspected ingestion paths. Partially mitigated: configured shared-key checks. Unresolved: cryptographic integrity, durable replay defense, per-device enrollment, lifecycle management, endpoint authorization, resilience, and physical identity. Physical device validation is REQUIRES EXTERNAL VALIDATION.
