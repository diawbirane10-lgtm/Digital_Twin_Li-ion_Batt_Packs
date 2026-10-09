# Battery Twin — Li-ion Pack Simulation & Telemetry Diagnostics

**Physics-based simulation · SOC estimation · Traceable battery-data analysis**

**Primary application: Streamlit** · [Alternative web dashboard](https://battery-twin-birane.vercel.app)

Battery Twin combines a configurable lithium-ion pack simulator with an independent CSV telemetry-analysis workflow. The primary application is Streamlit, rebuilt with square panels, operator-status information and simulation/diagnostic workflows. The React/TypeScript dashboard and Python FastAPI backend remain available as an alternative on Vercel.

This is an engineering demonstrator. Laboratory validation does not establish vehicle-level diagnostic accuracy or OEM qualification.

## Two workflows

| Workflow | Available features | Evidence and limits |
|---|---|---|
| **Simulation** | Configurable series/parallel topology, charge/discharge, electrical and thermal trends, cell inspection, simulated BMS alerts, CSV export | ECM parameters based on NASA B0005. Cells have fixed parameters; the simulator does not generate validated physical aging. |
| **Telemetry diagnostics** | CSV validation, Ah/Wh integration, temperature and cell-voltage-spread threshold checks, sampling-gap detection, JSON report with source-file SHA-256 | Independent of the NASA simulation model. Threshold crossings support investigation; they do not certify a fault or battery health. |

The simulation uses a two-RC equivalent circuit model and an Extended Kalman Filter for state-of-charge (SOC) estimation. The EKF includes the ohmic voltage term and a Joseph-form covariance update.

The capacity-based state-of-health (SOH) estimator computes measured cycle capacity divided by nominal capacity when suitable capacity observations are supplied. Without them, the initial SOH is an assumption. The remaining-useful-life (RUL) module uses a simple linear capacity trend after sufficient cycle observations; it is not a validated lifetime prediction. The CSV diagnostic does not infer SOH, RUL or weak-cell localisation from insufficient evidence.

## Dashboard

- **Overview:** pack values, estimated SOC uncertainty and simulated BMS state.
- **Cells:** individual simulated cell values and series/parallel identification.
- **Analysis:** time-based trends.
- **Simulation:** topology, initial conditions and charge/discharge controls.
- **Diagnostic:** measurement import, findings with evidence and limitations, report export.

Square geometry, neutral normal-state graphics, textual anomaly indications and a persistent operator-status banner follow the project's [HMI philosophy](docs/HMI_PHILOSOPHY.md), inspired by ISA-101. No certified standards compliance is claimed.

## Run locally

Requires Python and Node.js/npm.

```bash
python -m pip install -r requirements.txt
npm --prefix web ci
```

Start the primary Streamlit application:

```bash
python -m streamlit run app.py
```

The existing Streamlit Cloud entrypoint remains app.py. If the hosted app tracks this repository's main branch, it can rebuild from the updated code without creating another app.

For the alternative React interface, start the Python API:

```bash
python -m uvicorn digital_twin.api.dashboard:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
npm --prefix web run dev
```

Open the URL printed by Vite, normally http://localhost:5173. Vite proxies /api requests to the Python server. The local session API requires one worker because its simulation sessions are held in memory.

The Streamlit dashboard can also be launched directly:

```bash
streamlit run visualization/dashboard/app.py
```

## Telemetry CSV

Required columns:

```csv
time_s,pack_voltage_v,pack_current_a
0,400,10
60,398,10
```

Optional columns: temperature_c, soc_pct, cell_min_v, cell_max_v. Supply both cell-voltage columns together. Choose the current sign convention explicitly. Timestamps must increase strictly, values must be finite, and units must match the column names.

Integrated charge and energy describe the imported window, not automatically total capacity or SOH. Gaps are reported, but values between measurements are interpolated. The included example is synthetic and is labelled accordingly.

See [diagnostic scope and source catalogue](docs/EV_DIAGNOSTIC.md). Tesla, BMW and other source references are research candidates; their presence in the catalogue does not mean their archives are integrated or their vehicles are calibrated. No OBD/CAN connection or vehicle control is implemented.

## Validation

| Check | Recorded result |
|---|---|
| Python suite | 41 tests passed, including primary Streamlit navigation, simulation reset and CSV diagnostics |
| Frontend | TypeScript/Vite production build passed |
| Measured-data benchmark | 636 NASA discharge cycles, four laboratory cells, 185,721 samples |
| Integrated charge versus NASA capacity labels | Mean absolute difference 0.01303 Ah; maximum 0.02802 Ah |
| Robustness | Current-noise scenarios across 20 seeds, sign invariance, sampling gaps, malformed/non-finite data and checkpoint validation |
| Browser checks | Desktop/mobile diagnostic, invalid import, report export; no horizontal overflow or JavaScript errors observed |
| Production checks | API health, simulation continuation, diagnostic energy calculation and square CSS verified |

These are numerical and software checks. The benchmark has no independent SOC ground truth or annotated vehicle faults. Capacity-label differences may reflect different integration windows and end-of-discharge criteria. Passing tests does not establish field diagnostic reliability.

Reproduce the checks:

```bash
python -m pip install pytest httpx
python -m pytest -q
python -m validation.benchmark
npm --prefix web run build
```

[Benchmark results](validation/nasa_results.json) include the dataset fingerprint and per-cell aggregates. See the [validation report](docs/ENGINEERING_VALIDATION.md). No complete lint/coverage gate or GitHub CI pipeline is currently configured.

## Repository map

| Path | Purpose |
|---|---|
| web/ | React/TypeScript interface |
| digital_twin/core/twin_engine.py | Simulation and estimator orchestration |
| digital_twin/api/dashboard.py | Local session API and CSV diagnostics |
| digital_twin/api/serverless.py | Stateless simulation transport for Vercel |
| api/index.py | Hosted API entrypoint |
| estimation/ | SOC EKF and capacity-based SOH/RUL modules |
| simulation/ | Pack electrical and thermal model |
| diagnostics/ | CSV analysis, NASA adapter and source catalogue |
| validation/ | Reproducible measured-data benchmark |
| tests/ | API, numerical and robustness tests |
| ml/models/ecm_b0005.json | Existing NASA B0005 ECM parameter set |
| data/processed/ | Processed NASA laboratory datasets |
| notebooks/ | Original exploration and modelling notebooks |
| visualization/dashboard/ | Primary Streamlit interface |
| docs/ | Scope, architecture, HMI philosophy and validation |
| vercel.json | Integrated frontend/API deployment configuration |

## Deployment and limitations

**Streamlit is the primary application**, with its existing app.py entrypoint preserved. The exact existing Streamlit Cloud URL is not recorded in this repository; no replacement URL is invented here.

Alternative web application: **https://battery-twin-birane.vercel.app**

The hosted simulation exchanges validated JSON checkpoints with the client instead of relying on durable process memory. Checkpoints are editable simulation inputs, not authenticated measurement evidence. History is kept in the browser tab and is lost on reload; export it to retain it. Simulation is limited to 20,000 seconds.

The local CSV limit is 5 MB / 20,000 rows; the hosted platform's 4.5 MB request-body limit can reject smaller CSVs after JSON encoding. The current production function uses a reduced Python dependency set; research/Streamlit dependencies remain in requirements.txt. See [setup and deployment details](docs/DASHBOARD_V2.md).

## Industrial direction

Current uses: laboratory trial comparison, teaching, model exploration and descriptive telemetry review. Vehicle maintenance, second-life assessment and fleet monitoring require further datasets, calibrated models, independently documented reference measurements and annotated faults.

See [industrial context and contribution opportunities](docs/INDUSTRIAL_CONTRIBUTION.md). Priorities include native dataset adapters, validation outside calibration data, sensor-bias assessment and explicit out-of-domain detection.

Engineering verification was informed by [affaan-m/ECC verification-loop](https://github.com/affaan-m/ECC/blob/main/skills/verification-loop/SKILL.md). No ECC hooks or executable framework were installed.

## Technology

Python · FastAPI · NumPy · Pandas · React · TypeScript · Vite · Vercel
Primary IHM: Streamlit · Plotly
Research: Jupyter · PyArrow
