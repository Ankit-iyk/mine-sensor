# SUBSENSE

SUBSENSE is a predictive mine-subsidence monitoring research prototype that
collects sensor or simulator telemetry, extracts backend features, and
combines anomaly detection with risk assessment and alerts. It is not a
certified mine-safety system.

## Architecture

Sensors and simulator -> MQTT -> FastAPI backend -> signal processing and
feature extraction -> AI engine (Isolation Forest and baseline deviation) ->
risk engine and alerts -> WebSocket -> Next.js dashboard.

## Hardware design

![SUBSENSE sensor node hardware design (Cirkit Designer)](docs/images/hardware-design.jpg)

This is the circuit design for one sensor node.

| Component | Role |
|---|---|
| ESP32-S3-WROOM-1 development board | Microcontroller; reads sensors and publishes telemetry |
| MPU6050 accelerometer/gyroscope module | Tilt and acceleration sensing over I2C |
| SW-420-type vibration sensor module | Digital output for vibration events |
| Piezo buzzer | Audible alert |
| Red, yellow and green LEDs, each with a 220 ohm resistor | SAFE / WARNING / DANGER status indication |

Sensor axes `ax`, `ay` and `az` map to backend telemetry fields `accel_x`,
`accel_y` and `accel_z`; tilt and vibration use `tilt_x`, `tilt_y` and
`vibration` in the backend and AI engine.

The circuit was designed and simulated in Cirkit Designer; this repository
does not contain a `firmware/` folder.

## AI engine

`ai_engine/adapter.py` implements the backend `AnomalyDetector` interface and
maps backend features to the Isolation Forest inputs, including backend
baseline deviation. `backend/app/ml/loader.py` loads the trained model from
`ai_engine/models/isolation_forest.joblib` and falls back to the mock detector
if the model is missing or cannot be loaded.

## Results

The reproducible evaluation in [docs/evaluation/results.md](docs/evaluation/results.md)
compares fixed thresholds, statistical/temporal baselines, learned detectors,
and the current system on the same backend feature pipeline. Its fair ablations
apply the same persistence/spatial wrapper when comparing baseline deviation
with and without the Isolation Forest. Baseline deviation plus temporal
persistence and spatial corroboration carries most demonstrated detection;
the report shows the Isolation Forest's incremental value per scenario rather
than assuming it helps. Vibration and sensor-failure detection remain limited.
These are synthetic results, not field-performance claims. Reproduce the report
with `python -m ai_engine.evaluation.run_all --seeds 30`.

The latest full validation for this revision reports **102 AI-engine tests
passed** and **117 backend tests passed**. Rerun the test commands below for
current results.

## Known limitations

- Persistent anomalies and isolated vibration events are only weakly detected.
- About 7% of normal readings receive a false `MICRO_ANOMALY` label.
- The model is trained on simulated data only, not real ESP32 readings.
- The final gradual-tilt risk is WARNING (score 45), not DANGER.
- The full Docker + MQTT + dashboard chain was not run end to end.

## How to run

### Setup

Prerequisites: Python 3.12+ and Docker Desktop for the broker and database
services.

From the repository root, create and activate a virtual environment and
install backend dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

Create the backend environment file:

```powershell
copy backend\.env.example backend\.env
```

Set a private `HARDWARE_DEVICE_KEY` in `backend\.env` before using hardware
telemetry. REST clients send it as `X-Hardware-Device-Key`; MQTT hardware
payloads include a `hardware_device_key` field. A missing or invalid key
downgrades `source="hardware"` to `unknown`, which never reports LIVE. Use TLS
for REST/MQTT and restrict broker access; the shared key is not a substitute
for transport encryption or per-device credentials.

### Docker, backend, simulator, and dashboard

From the repository root, start EMQX and TimescaleDB:

```powershell
docker compose up -d
```

Wait for the services to initialize. EMQX dashboard: http://localhost:18083.

In a new terminal, activate the virtual environment and start the backend:

```powershell
cd backend
..\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify the health endpoint at http://localhost:8000/api/health.

In another terminal, run the simulator from its package root:

```powershell
cd simulator
python -m simulator.main --scenario normal
```

Other supported simulator examples:

```powershell
python -m simulator.main --scenario gradual_tilt --duration 120
python -m simulator.main --scenario sensor_failure --dry-run
```

The dashboard is a separate Next.js application. In another terminal:

```powershell
cd dashboard
npm install
npm run dev
```

Open http://localhost:3000.

### Docker-free demo and retraining

From the repository root, run the in-process demo without Docker, MQTT, or
database writes:

```powershell
python scripts/demo_inprocess.py
```

Retrain the model using normal simulator data processed through the backend
feature pipeline:

```powershell
python -m ai_engine.training.train_from_backend
```

### Real sensor recordings

See [docs/data-collection-protocol.md](docs/data-collection-protocol.md) for
the stationary and controlled-event protocol. To capture serial JSON lines,
install optional `pyserial` and run (replace `COM4` with the ESP32's port):

```powershell
python -m pip install pyserial
python tools/log_serial_to_csv.py --port COM4 --baudrate 115200 --output readings.csv
```

Attach reviewed labels with `--label-file labels.csv`. For a stationary CSV,
compute the noise floor and empirical threshold outputs:

```powershell
python -m ai_engine.evaluation.noise_floor readings.csv --output-dir docs/evaluation/real
```

### Tests

Run the AI-engine tests from the repository root:

```powershell
python -m pytest ai_engine/tests -q
```

Run the backend tests from `backend/`:

```powershell
cd backend
python -m pytest -q
```

## Branches and team

- `ai_engine/` is the AI/ML layer.
- `backend/`, `dashboard/` and `simulator/` are the platform components.
- `ai-ml-development` is the submission branch.
