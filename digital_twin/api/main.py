"""
FastAPI REST — Digital Twin Li-ion Battery Pack

Endpoints :
  GET  /health              — statut de l'API
  GET  /twin/info           — informations du pack (topologie, tension nominale)
  POST /twin/update         — nouvelle mesure (V, I, T) → état mis à jour
  GET  /twin/state          — état courant du twin
  GET  /twin/history        — historique complet (ou N derniers points)
  POST /twin/end_cycle      — enregistrer fin de cycle → MAJ SOH
  POST /twin/reset          — réinitialiser SOC et historique
  POST /twin/configure      — reconfigurer topologie Ns × Np
  GET  /twin/cells          — état individuel de chaque cellule
  POST /twin/simulate_batch — injecter un batch de mesures
  GET  /docs                — Swagger UI (auto-généré par FastAPI)

Lancer :
  uvicorn digital_twin.api.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from digital_twin.core.twin_engine import BatteryDigitalTwin
from digital_twin.api.schemas import (
    UpdateRequest, EndCycleRequest, ResetRequest, ConfigRequest,
    TwinStateResponse, HistoryResponse,
    PackInfoResponse, HealthResponse,
)

# ── Initialisation ────────────────────────────────────────────────────────────

def _load_twin(ns: int = 12, np_: int = 4) -> BatteryDigitalTwin:
    ecm_path = ROOT / "ml" / "models" / "ecm_b0005.json"
    with open(ecm_path) as f:
        ecm = json.load(f)
    return BatteryDigitalTwin(ecm_params=ecm, pack_ns=ns, pack_np=np_)


_twin: BatteryDigitalTwin = _load_twin()

# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "Battery Digital Twin API",
    description = (
        "API REST du jumeau numérique Li-ion 18650 NMC.\n\n"
        "Estimation SOC (EKF), SOH (Coulomb counting physique), "
        "simulation pack Ns×Np avec déséquilibre thermique.\n\n"
        "Données de référence : NASA Battery Dataset B0005."
    ),
    version  = "1.0.0",
    docs_url = "/docs",
    redoc_url= "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Système"])
def health():
    """Statut de l'API et disponibilité du twin."""
    return HealthResponse(status="ok", version="1.0.0", twin_ready=True)


# ── Pack info ─────────────────────────────────────────────────────────────────

@app.get("/twin/info", response_model=PackInfoResponse, tags=["Pack"])
def pack_info():
    """Informations statiques du pack (topologie, tensions nominales)."""
    pack = _twin.pack
    ecm  = _twin._ecm
    V_nom = pack.ns * 3.6
    E_nom = pack.ns * pack.np_ * ecm["Q_nom_Ah"] * 3.6
    return PackInfoResponse(
        ns           = pack.ns,
        np_          = pack.np_,
        n_cells      = pack.n_cells,
        V_nominal    = round(V_nom, 2),
        E_nominal_Wh = round(E_nom, 2),
        Q_nom_Ah     = ecm["Q_nom_Ah"],
    )


# ── Mise à jour ───────────────────────────────────────────────────────────────

@app.post("/twin/update", response_model=TwinStateResponse, tags=["Twin"])
def update(req: UpdateRequest):
    """
    Ingère une mesure (V, I, T) et retourne l'état mis à jour.

    - EKF estime le SOC à partir de la tension et du courant.
    - Le simulateur pack avance d'un pas dt.
    - Le BMS vérifie les seuils de protection (OVP, UVP, OTP, SOC min).
    """
    try:
        state = _twin.update(
            voltage     = req.voltage,
            current     = req.current,
            temperature = req.temperature,
            dt          = req.dt,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return _state_to_response(state)


@app.get("/twin/state", response_model=TwinStateResponse, tags=["Twin"])
def get_state():
    """État courant du jumeau numérique (dernière mise à jour)."""
    return _state_to_response(_twin.state)


# ── Historique ────────────────────────────────────────────────────────────────

@app.get("/twin/history", response_model=HistoryResponse, tags=["Twin"])
def get_history(last_n: int = 0):
    """
    Historique de simulation.
    last_n=0 → historique complet ; last_n=N → N derniers points.
    """
    df = _twin.history_df()
    if df.empty:
        return HistoryResponse(
            n_points=0, timestamps=[], soc=[], soh=[], pack_voltage=[],
            T_max=[], current=[], soc_imbalance=[], alerts_count=[],
        )
    if last_n > 0:
        df = df.tail(last_n)
    return HistoryResponse(
        n_points      = len(df),
        timestamps    = df["timestamp"].tolist(),
        soc           = df["soc"].tolist(),
        soh           = df["soh"].tolist(),
        pack_voltage  = df["pack_voltage"].tolist(),
        T_max         = df["T_max"].tolist(),
        current       = df["current"].tolist(),
        soc_imbalance = df["soc_imbalance"].tolist(),
        alerts_count  = [len(a) if isinstance(a, list) else 0
                         for a in df["alerts"].tolist()],
    )


# ── Cycle & Reset ─────────────────────────────────────────────────────────────

@app.post("/twin/end_cycle", tags=["Twin"])
def end_cycle(req: EndCycleRequest):
    """Enregistre la fin d'un cycle de décharge et met à jour le SOH."""
    _twin.end_cycle(measured_capacity_Ah=req.measured_capacity_Ah)
    return {
        "message":     "Cycle enregistré",
        "cycle_count": len(_twin.soh_est.soh_history),
        "soh":         round(_twin.soh_est.soh, 4),
    }


@app.post("/twin/reset", tags=["Twin"])
def reset(req: ResetRequest):
    """Réinitialise le twin (SOC, historique). Ne modifie pas la topologie."""
    _twin.reset(soc0=req.soc0)
    return {"message": "Twin réinitialisé", "soc0": req.soc0}


@app.post("/twin/configure", tags=["Twin"])
def configure(req: ConfigRequest):
    """Reconfigure la topologie du pack (Ns × Np) et réinitialise le twin."""
    global _twin
    ecm_path = ROOT / "ml" / "models" / "ecm_b0005.json"
    with open(ecm_path) as f:
        ecm = json.load(f)
    _twin = BatteryDigitalTwin(ecm_params=ecm, pack_ns=req.pack_ns, pack_np=req.pack_np)
    _twin.pack.set_temperature(req.T_init)
    return {
        "message":   f"Pack reconfiguré : {req.pack_ns}S×{req.pack_np}P",
        "n_cells":   req.pack_ns * req.pack_np,
        "V_nominal": round(req.pack_ns * 3.6, 2),
    }


# ── État individuel des cellules ──────────────────────────────────────────────

@app.get("/twin/cells", tags=["Pack"])
def get_cells():
    """État individuel de chaque cellule du pack (SOC, T, V, I)."""
    cells = []
    for i, c in enumerate(_twin.pack.cells):
        row = int(i // _twin.pack.np_)
        col = int(i % _twin.pack.np_)
        cells.append({
            "id":      i,
            "row_s":   row,
            "col_p":   col,
            "soc":     round(c.state.soc,     4),
            "voltage": round(c.state.voltage, 4),
            "temp":    round(c.state.temp,    2),
            "current": round(c.state.current, 4),
        })
    return {
        "n_cells": len(cells),
        "ns":      _twin.pack.ns,
        "np":      _twin.pack.np_,
        "cells":   cells,
    }


# ── Simulation batch ──────────────────────────────────────────────────────────

@app.post("/twin/simulate_batch", tags=["Twin"])
def simulate_batch(measurements: list[UpdateRequest]):
    """
    Injecte un batch de mesures en une seule requête.
    Retourne l'état final après les N mesures.
    Utile pour rejouer un profil enregistré.
    """
    if not measurements:
        raise HTTPException(status_code=400, detail="Liste de mesures vide")
    if len(measurements) > 86400:
        raise HTTPException(status_code=400, detail="Maximum 86 400 mesures par batch")

    for m in measurements:
        _twin.update(m.voltage, m.current, m.temperature, m.dt)

    return {
        "message":     f"{len(measurements)} mesures traitées",
        "final_state": _state_to_response(_twin.state).model_dump(),
    }


# ── Helper ────────────────────────────────────────────────────────────────────

def _state_to_response(state) -> TwinStateResponse:
    return TwinStateResponse(
        timestamp     = round(state.timestamp, 2),
        soc           = round(state.soc,           4),
        soc_std       = round(state.soc_std,        5),
        soh           = round(state.soh,            4),
        rul_cycles    = state.rul_cycles,
        voltage       = round(state.voltage,        4),
        current       = round(state.current,        4),
        temperature   = round(state.temperature,    2),
        pack_voltage  = round(state.pack_voltage,   4),
        V_cell_min    = round(state.V_cell_min,     4),
        V_cell_max    = round(state.V_cell_max,     4),
        T_max         = round(state.T_max,          2),
        soc_imbalance = round(state.soc_imbalance,  5),
        alerts        = state.alerts,
    )


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("digital_twin.api.main:app", host="0.0.0.0", port=8000, reload=True)
