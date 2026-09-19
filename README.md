# SUBSENSE

## Predictive Mine Subsidence Intelligence System

A low-cost IoT-based mine stability monitoring platform using distributed ESP32 sensor nodes.

> ⚠️ **Research Prototype** — NOT a certified mine-safety system.
> Terminology used: *anomaly*, *developing instability*, *stability indicator*, *early-warning indicator*.

---

## Architecture

```
ESP32 Nodes → Wi-Fi → MQTT/EMQX → FastAPI Backend
                                         │
                              ┌──────────┼──────────┐
                         Validation  Processing   Database
                                         │
                              Feature Extraction
                                         │
                                   ML Interface ← teammate's model
                                         │
                              Temporal / Spatial / Risk Engine
                                         │
                              WebSocket / REST API
                                         │
                              Next.js Dashboard
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Docker Desktop (for EMQX)

### 1 — Clone and set up Python environment

```powershell
cd subsense

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2 — Copy environment file

```powershell
copy backend\.env.example backend\.env
```

### 3 — Start EMQX broker

```powershell
docker compose up -d
```

Wait ~15 seconds for EMQX to initialise.

Verify: http://localhost:18083 (admin / subsense_dev)

### 4 — Start the FastAPI backend

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
subsense_starting  version=0.1.0  mqtt_host=localhost  mqtt_port=1883
mqtt_connected     topic=mine/+/+/telemetry  qos=1
```

### 5 — Verify health endpoint

```powershell
curl http://localhost:8000/api/health
```

Expected:
```json
{
  "status": "ok",
  "service": "subsense-backend",
  "version": "0.1.0",
  "mqtt_connected": true
}
```

### 6 — Run the simulator

Open a new terminal:

```powershell
# Activate venv first
.venv\Scripts\Activate.ps1

# Run normal scenario
python -m simulator.main --scenario normal

# Run gradual tilt for 2 minutes
python -m simulator.main --scenario gradual_tilt --duration 120

# List all scenarios
python -m simulator.main --list

# Dry run (no MQTT needed — great for testing)
python -m simulator.main --scenario sensor_failure --dry-run
```

### 7 — Watch telemetry arrive in the backend

The FastAPI terminal should show:
```
telemetry_received  node_id=N01  zone_id=Z01  tilt_x=1.023  tilt_y=0.804  vibration=0
telemetry_received  node_id=N02  zone_id=Z01  tilt_x=0.853  tilt_y=1.102  vibration=0
...
```

---

## Running tests

```powershell
cd backend
pytest -v
```

Expected:
```
tests/test_health.py::test_health_returns_200     PASSED
tests/test_health.py::test_health_response_schema PASSED
tests/test_schemas.py::test_valid_payload_accepted PASSED
... (all pass)
```

---

## API Documentation

FastAPI auto-generates docs:

- Swagger UI: http://localhost:8000/docs
- ReDoc:      http://localhost:8000/redoc

---

## Repository Structure

```
subsense/
├── backend/                 FastAPI application
│   ├── app/
│   │   ├── main.py          App factory + lifespan
│   │   ├── config.py        Settings (pydantic-settings)
│   │   ├── logging_config.py
│   │   ├── api/routes/
│   │   │   └── health.py    GET /api/health
│   │   └── ingestion/
│   │       ├── schemas.py   TelemetryReading (Pydantic)
│   │       ├── mqtt_client.py
│   │       └── message_handler.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── simulator/               ESP32 simulator
│   ├── main.py              CLI entry point
│   ├── node.py              SensorNode + 6 scenarios
│   ├── scenarios.py         Scenario registry
│   ├── publisher.py         MQTT publish logic
│   └── config.py
│
├── ml-contract/             Interface contract for ML teammate
│   └── README.md
│
├── frontend/                (Phase 16 — not yet built)
├── docker-compose.yml       EMQX broker
└── .gitignore
```

---

## Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Done | Backend skeleton, config, health endpoint |
| 2 | ✅ Done | Sensor simulator (6 scenarios, 6 nodes) |
| 3 | ✅ Done | MQTT ingestion + Pydantic validation |
| 4 | 🔲 Next | PostgreSQL + TimescaleDB |
| 5 | 🔲      | Signal processing (Kalman, rolling stats) |
| 6 | 🔲      | Feature extraction pipeline |
| 7 | 🔲      | Ground Stability Fingerprint |
| 8 | 🔲      | ML anomaly detection interface |
| 9 | 🔲      | Precursor Pattern Engine |
| 10 | 🔲     | Spatial Correlation Engine |
| 11 | 🔲     | Risk Engine |
| 12 | 🔲     | Risk Trajectory |
| 13 | 🔲     | Explainable Alert Engine |
| 14–15 | 🔲  | REST API + WebSockets |
| 16–18 | 🔲  | Next.js Frontend |
| 19–20 | 🔲  | Testing + Multi-node simulation |

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot connect to EMQX` | Broker not running | `docker compose up -d` |
| `ModuleNotFoundError: app` | Wrong working directory | Run from `backend/` |
| `ModuleNotFoundError: simulator` | Wrong working directory | Run from `subsense/` root |
| `paho.mqtt.reasoncodes` import error | paho-mqtt < 2.0 | `pip install paho-mqtt>=2.1.0` |
| `asyncio_mode` warning in pytest | Missing pytest.ini | Already included in `backend/pytest.ini` |
