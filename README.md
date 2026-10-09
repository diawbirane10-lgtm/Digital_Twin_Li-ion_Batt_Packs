# Digital Twin — Li-ion Battery Packs

**Multi-Physics Simulation · State Estimation · BMS — Python**

A physics-based digital twin for Li-ion battery packs, built from scratch as a first
digital twin project. The pack topology (Ns×Np) is fully configurable; all results
shown are based on the NASA B0005 cell (18650 NMC, 2 Ah).

---

## What it does

| Component | Description |
|-----------|-------------|
| **ECM 2RC** | Equivalent circuit model (R₀ + 2 RC branches) identified on NASA B0005 |
| **EKF** | Extended Kalman Filter — real-time SOC estimation (single-cell) |
| **SOH** | State of Health via Coulomb counting, cycle by cycle |
| **RUL** | Remaining Useful Life estimate (Arrhenius model, temperature + C-rate) |
| **Pack simulator** | Ns×Np cell grid with thermal model and inter-cell imbalance |
| **BMS** | Overvoltage, undervoltage, overtemperature and low-SOC protection |
| **Dashboard** | Streamlit — real-time plots, 3D pack view (Plotly), CSV export |
| **REST API** | FastAPI — 10 endpoints (update, state, history, cells, reset…) |

---

## Project Structure

```
digital-twin/
├── estimation/
│   ├── soc/kalman/ekf.py          # Extended Kalman Filter
│   └── soh/physics/soh_estimator.py  # Coulomb counting + RUL
├── simulation/
│   └── pack/pack_simulator.py      # Ns×Np pack + thermal model
├── digital_twin/
│   ├── core/twin_engine.py         # Main orchestrator
│   └── api/main.py                 # FastAPI REST API
├── visualization/
│   └── dashboard/app.py            # Streamlit dashboard
├── ml/models/ecm_b0005.json        # Identified ECM parameters
├── notebooks/                      # Step-by-step Jupyter notebooks
├── configs/                        # YAML configuration files
├── data/exports/                   # Simulation data exports (CSV)
├── app.py                          # Streamlit Cloud entrypoint
└── requirements.txt
```

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the dashboard
streamlit run visualization/dashboard/app.py
# or double-click lancer_dashboard.bat (Windows)
```

---

## Notebooks

| # | Topic |
|---|-------|
| 01 | Data exploration — NASA B0005 discharge cycles |
| 02 | ECM 2RC simulation and parameter identification |
| 03 | SOC estimation with Extended Kalman Filter |

---

## Dataset

**NASA Battery Dataset — cell B0005** (NASA PCoE, 2007)
- Chemistry: LCO/NMC 18650
- Nominal capacity: 2.0 Ah
- Protocol: 1C charge/discharge cycles at 25 °C
- Used for: ECM identification (R₀, R₁, C₁, R₂, C₂, OCV polynomial)

---

## Simulation results (4S×4P, 40 °C, 1C discharge, 180 s)

| Metric | Initial | Final |
|--------|---------|-------|
| SOC | 100.0 % | 94.93 % |
| V_pack | 16.20 V | 15.49 V |
| V_cell | 4.050 V | 3.870 V |
| T_max | 40.000 °C | 40.008 °C |
| SOH (after 3 cycles) | — | 97.73 % |

---

## Tech stack

`Python` `Streamlit` `FastAPI` `NumPy` `Pandas` `Plotly` `PyYAML`

---

## Deployment

Dashboard live on **Streamlit Community Cloud** — topology (Ns, Np),
temperature and C-rate are fully interactive.

## New web IHM (V2)

React/TypeScript dashboard connected to an isolated FastAPI simulation session.
See [setup and limitations](docs/DASHBOARD_V2.md) and
[industry review and contribution opportunities](docs/INDUSTRIAL_CONTRIBUTION.md).
The existing Streamlit entrypoint remains available.
