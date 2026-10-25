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
compares methods on the same backend feature pipeline. The latest report uses
12 test seeds per scenario and noise set; the learned methods were trained on
event-free nominal, baseline-drift nuisance, and shifted-noise examples using
disjoint seeds. Fair Isolation Forest comparisons use the same persistence
and spatial wrapper for the full system and the baseline-deviation-only
counterfactual.

The Isolation Forest adds value in some tested conditions, but not uniformly.
For gradual tilt under simulator noise, adding it changes F1 from **0.967**
[0.961, 0.973] to **0.945** [0.941, 0.948], while reducing nuisance false
alarms from **264.348** [238.386, 290.309] to **6.087** [0.000, 13.271] per
hour. For step tilt, F1 changes from **0.874** [0.852, 0.896] to **0.877**
[0.858, 0.897], with no event-recall difference. Under distribution shift,
the full system improves gradual-tilt F1 from **0.595** [0.578, 0.612] to
**0.885** [0.871, 0.899] and step-tilt F1 from **0.225** [0.210, 0.239] to
**0.689** [0.643, 0.735], with lower false-alarm rates than the no-forest
baseline. These are synthetic results; confidence intervals and all scenarios
are in the evaluation report.

The checked gradual-tilt comparisons also correct prior wording: simulator
normal-control false alarms are tied for the unwrapped z-score and current
system (**0/hour** each), while nuisance false alarms are **0.870** [0.000,
2.783] vs **45.217** [34.147, 56.287] per hour, respectively. Removing
temporal persistence raises F1 from **0.945** [0.941, 0.948] to **0.958**
[0.954, 0.962] and nuisance false alarms from **6.087** [0.000, 13.271] to
**45.217** [34.147, 56.287] per hour; event recall remains 1.000 for both.

Simple specialized baselines win in important cases: the fixed tilt threshold
has the best step-tilt F1 on both noise sets, while vibration-only threshold
leads on shifted-noise vibration bursts and the stuck-sensor check leads on
simulator sensor failure; Isolation Forest alone leads on simulator vibration
bursts. The winning method varies by scenario; no single detector wins
everywhere. Reproduce the full default run with
`python -m ai_engine.evaluation.run_all --seeds 30`. The checked-in report was
generated with 12 test seeds; this run took **176.39 minutes**, so it exceeded
the 20-minute target.

Run both test suites with the commands below.

## Known limitations

- All evaluation results use synthetic data; no real ESP32 recording has been
  evaluated, so the results do not establish field performance.
- Evaluation performance changes under the shifted-noise test. The current
  system + persistence/spatial wrapper averages **38.270** [21.825, 54.715]
  false alarms/hour on shifted normal controls in the 12-seed run; see the
  per-method report table.
- Vibration and stuck-sensor results are from specialized evaluation baselines,
  not improvements to production detector behavior.
- A short 12-seed run was used for the checked-in report because larger runs
  exceeded the 20-minute target; its confidence intervals are correspondingly
  less stable than a larger study.
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
