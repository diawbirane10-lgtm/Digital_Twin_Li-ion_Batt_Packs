# Digital Twin for Li-ion Battery Packs

A complete Python-based Digital Twin framework for Li-ion battery packs, covering:
- Physics-based simulation (ECM, electrochemical models via PyBaMM)
- State estimation: SOC, SOH, SOP, SOT
- Machine learning: LSTM, TCN-LSTM, XGBoost, EKF/UKF
- BMS simulation: cell balancing, protection
- Real-time dashboard (Streamlit)
- 3D pack visualization (PyVista)
- REST API (FastAPI)

---

## Project Structure

```
battery-digital-twin/
├── data/               # Raw & processed datasets (NASA, CALCE, Oxford)
├── simulation/         # ECM, electrochemical, thermal, pack models
├── estimation/         # SOC, SOH, SOP, SOT estimators
├── ml/                 # Training pipelines, saved models, experiments
├── bms/                # BMS logic: balancing, protection, controller
├── digital_twin/       # Twin engine, sync loop, REST API
├── visualization/      # Dashboard, 3D viewer, plots
├── notebooks/          # Step-by-step Jupyter notebooks
├── configs/            # YAML configuration files
├── tests/              # Unit and integration tests
└── docs/               # Architecture docs, reports
```

---

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download datasets (see data/raw/*/README.md)

# 4. Start with the notebooks (in order)
jupyter lab notebooks/
```

---

## Learning Roadmap

| Phase | Topic | Notebook |
|-------|-------|----------|
| 1 | Data exploration & visualization | 01_data_exploration |
| 2 | ECM simulation (Thevenin 2RC) | 02_ecm_simulation |
| 3 | SOC estimation with EKF | 03_soc_kalman |
| 4 | SOC estimation with LSTM | 04_soc_lstm |
| 5 | SOH estimation & RUL | 05_soh_estimation |
| 6 | ML training pipeline | 06_ml_training_pipeline |
| 7 | Pack simulation (12S4P) | 07_pack_simulation |
| 8 | 3D visualization | 08_3d_visualization |

---

## Datasets
| Dataset | Chemistry | Size | Best For |
|---------|-----------|------|----------|
| NASA PCoE (B0005-B0018) | LCO 18650 | ~8 MB | SOC, SOH, RUL baseline |
| CALCE CS2 | LCO | ~20 MB | SOH degradation patterns |
| Oxford | LFP pouch | ~50 MB | Calendar aging, LFP chemistry |

---

## Target Hardware (for context)
This twin is designed around a **12S4P NMC pack** (43.2V / 10Ah) — representative
of small EV / stationary storage systems studied at research centers.
