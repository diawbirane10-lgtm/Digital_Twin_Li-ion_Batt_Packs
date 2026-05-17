"""
Digital Twin Engine — noyau du jumeau numérique Li-ion.

Synchronise en continu :
  Mesures réelles (V, I, T)  ←→  Modèle physique (ECM 2RC + EKF + SOH)

Usage :
    twin = BatteryDigitalTwin(ecm_params=ecm, pack_ns=12, pack_np=4)
    twin.update(voltage=3.85, current=-1.5, temperature=28.0, dt=1.0)
    print(twin.state)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

from estimation.soc.kalman.ekf import BatteryEKF
from estimation.soh.physics.soh_estimator import SOHEstimator
from simulation.pack.pack_simulator import PackSimulator, CellParams


@dataclass
class TwinState:
    """Snapshot complet de l'état du jumeau numérique."""
    timestamp:     float = 0.0
    soc:           float = 1.0
    soc_std:       float = 0.0
    soh:           float = 1.0
    rul_cycles:    Optional[int] = None
    voltage:       float = 0.0
    current:       float = 0.0
    temperature:   float = 25.0
    pack_voltage:  float = 0.0
    V_cell_min:    float = 0.0
    V_cell_max:    float = 0.0
    T_max:         float = 25.0
    soc_imbalance: float = 0.0
    alerts:        list  = field(default_factory=list)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class BatteryDigitalTwin:
    """
    Jumeau numérique d'un pack Li-ion.

    Composants :
    - EKF   : estimation SOC en temps réel (Extended Kalman Filter)
    - Pack  : simulation Ns×Np cellules avec déséquilibre thermique
    - SOH   : suivi de dégradation cycle par cycle (Coulomb counting)
    - BMS   : vérification des seuils de protection
    """

    def __init__(
        self,
        ecm_params: dict,
        pack_ns: int = 12,
        pack_np: int = 4,
        bms_limits: Optional[dict] = None,
    ):
        self._ecm = ecm_params
        poly      = ecm_params["ocv_poly_coeffs"]

        # EKF — estimation SOC
        self.ekf = BatteryEKF(
            R0=ecm_params["R0_ohm"],
            R1=ecm_params["R1_ohm"],
            C1=ecm_params["C1_F"],
            R2=ecm_params["R2_ohm"],
            C2=ecm_params["C2_F"],
            Q_nom_Ah=ecm_params["Q_nom_Ah"],
            ocv_poly_coeffs=poly,
            Q_noise=np.diag([1e-6, 1e-6, 1e-6]),
            R_noise=np.array([[5e-4]]),
        )

        # Pack simulator — Ns × Np cellules
        base = CellParams(
            R0=ecm_params["R0_ohm"],
            R1=ecm_params["R1_ohm"],
            C1=ecm_params["C1_F"],
            R2=ecm_params["R2_ohm"],
            C2=ecm_params["C2_F"],
            Q_nom_Ah=ecm_params["Q_nom_Ah"],
        )
        self.pack = PackSimulator(pack_ns, pack_np, base, poly)

        # SOH — dégradation par cycle
        self.soh_est = SOHEstimator(Q_nominal=ecm_params["Q_nom_Ah"])

        # BMS — seuils de protection
        self.bms = bms_limits or {
            "V_cell_max": 4.25,
            "V_cell_min": 2.45,
            "T_max":      55.0,
            "SOC_min":    0.05,
        }

        self.state    = TwinState()
        self._t       = 0.0
        self._history: list[TwinState] = []

    # ── Mise à jour principale ──────────────────────────────────────────

    def update(
        self,
        voltage:     float,
        current:     float,
        temperature: float,
        dt:          float = 1.0,
    ) -> TwinState:
        """
        Ingère une mesure (V, I, T) et met à jour l'état du twin.

        Args:
            voltage     : tension terminale mesurée (V)
            current     : courant (A) — I < 0 = décharge
            temperature : température ambiante (°C)
            dt          : pas de temps (s)
        """
        self._t += dt

        # 1. EKF — estimation SOC (modèle cellule unique)
        #    Le twin reçoit des grandeurs PACK → convertir en grandeurs cellule
        V_cell = voltage / self.pack.ns          # tension par cellule
        I_cell = current / max(1, self.pack.np_) # courant par cellule
        self.ekf.predict(I_cell, dt)
        self.ekf.update(V_cell)

        # 2. Pack — simulation physique Ns×Np
        pack_snap = self.pack.step(current, dt, temperature)

        # 3. BMS — alertes de protection
        alerts = self._check_bms(pack_snap)

        # 4. Mise à jour état global
        self.state = TwinState(
            timestamp     = self._t,
            soc           = self.ekf.soc,
            soc_std       = self.ekf.soc_std,
            soh           = self.soh_est.soh,
            rul_cycles    = self.soh_est.rul_cycles,
            voltage       = voltage,
            current       = current,
            temperature   = temperature,
            pack_voltage  = pack_snap["V_pack"],
            V_cell_min    = pack_snap["V_cell_min"],
            V_cell_max    = pack_snap["V_cell_max"],
            T_max         = pack_snap["T_max"],
            soc_imbalance = pack_snap["SOC_imbalance"],
            alerts        = alerts,
        )
        self._history.append(self.state)
        return self.state

    def end_cycle(self, measured_capacity_Ah: Optional[float] = None):
        """Enregistre la fin d'un cycle de décharge et met à jour le SOH."""
        if measured_capacity_Ah is not None:
            self.soh_est.add_cycle(measured_capacity_Ah)

    def reset(self, soc0: float = 1.0):
        """Réinitialise SOC et historique (topologie conservée)."""
        self.ekf.reset(soc0)
        self.pack.reset(soc0)
        self._t       = 0.0
        self._history = []

    # ── Historique ──────────────────────────────────────────────────────

    def history_df(self):
        import pandas as pd
        return pd.DataFrame([s.to_dict() for s in self._history])

    # ── Construction depuis fichiers de config ──────────────────────────

    @classmethod
    def from_config(cls, battery_yaml: str, pack_yaml: str) -> "BatteryDigitalTwin":
        with open(battery_yaml) as f:
            pack_cfg = yaml.safe_load(f)
        with open(pack_yaml) as f:
            pack_params = yaml.safe_load(f)

        ecm_path = Path("ml/models/ecm_b0005.json")
        with open(ecm_path) as f:
            ecm = json.load(f)

        return cls(
            ecm_params=ecm,
            pack_ns=pack_params["pack"]["series"],
            pack_np=pack_params["pack"]["parallel"],
            bms_limits={
                "V_cell_max": pack_params["bms"]["overvoltage_V"],
                "V_cell_min": pack_params["bms"]["undervoltage_V"],
                "T_max":      pack_params["bms"]["overtemperature_C"],
                "SOC_min":    0.05,
            },
        )

    # ── BMS interne ─────────────────────────────────────────────────────

    def _check_bms(self, pack_snap: dict) -> list[str]:
        alerts = []
        if pack_snap["V_cell_max"] > self.bms["V_cell_max"]:
            alerts.append(f"OVP: V_cell = {pack_snap['V_cell_max']:.3f} V")
        if pack_snap["V_cell_min"] < self.bms["V_cell_min"]:
            alerts.append(f"UVP: V_cell = {pack_snap['V_cell_min']:.3f} V")
        if pack_snap["T_max"] > self.bms["T_max"]:
            alerts.append(f"OTP: T = {pack_snap['T_max']:.1f} °C")
        if self.ekf.soc < self.bms["SOC_min"]:
            alerts.append(f"SOC critique: {self.ekf.soc * 100:.1f}%")
        return alerts
