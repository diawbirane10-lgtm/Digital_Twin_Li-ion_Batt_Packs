"""
Simulateur de pack Li-ion — topologie Ns x Np.

Chaque cellule est modélisée par un ECM 2RC indépendant avec variation
de capacité et de résistance (manufacturing spread) pour simuler le
déséquilibre réel d'un pack.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CellParams:
    R0: float = 0.015
    R1: float = 0.010
    C1: float = 2000.0
    R2: float = 0.005
    C2: float = 20000.0
    Q_nom_Ah: float = 2.0
    soc0: float = 1.0


@dataclass
class CellState:
    soc:  float = 1.0
    vc1:  float = 0.0
    vc2:  float = 0.0
    temp: float = 25.0
    voltage: float = 0.0
    current: float = 0.0
    cycle:   int   = 0


class CellSimulator:
    """ECM 2RC pour une cellule unique."""

    def __init__(self, params: CellParams, ocv_poly_coeffs: list, cell_id: int = 0):
        self.p    = params
        self._ocv = np.poly1d(ocv_poly_coeffs)
        self.id   = cell_id
        self.state = CellState(soc=params.soc0)
        self.state.voltage = float(self._ocv(params.soc0))

    @staticmethod
    def _capacity_factor(T_C: float) -> float:
        """Facteur de capacité disponible Li-ion NMC vs température."""
        if T_C >= 25.0:
            return min(1.02, 1.0 + 0.0005 * (T_C - 25.0))
        return max(0.40, 1.0 - 0.008 * (25.0 - T_C))

    def step(self, current_A: float, dt: float, T_ambient: float = 25.0) -> CellState:
        """Avance d'un pas de temps dt secondes."""
        p  = self.p
        st = self.state
        tau1 = max(p.R1 * p.C1, 1e-9)
        tau2 = max(p.R2 * p.C2, 1e-9)
        a1   = np.exp(-dt / tau1)
        a2   = np.exp(-dt / tau2)

        # Capacité effective corrigée par la température (Li-ion perd de la capacité au froid)
        Q_As = p.Q_nom_Ah * 3600 * self._capacity_factor(T_ambient)

        st.soc = float(np.clip(st.soc + current_A * dt / Q_As, 0.0, 1.0))
        st.vc1 = a1 * st.vc1 + p.R1 * (1 - a1) * current_A
        st.vc2 = a2 * st.vc2 + p.R2 * (1 - a2) * current_A

        ocv = float(self._ocv(st.soc))
        st.voltage = ocv + p.R0 * current_A + st.vc1 + st.vc2
        st.current = current_A

        # Modèle thermique 0D corrigé — masse thermique réaliste 18650 (~40 J/K)
        m_cp    = 40.0  # J/K — masse thermique d'une cellule 18650
        h_coeff = 2.5   # W/K — convection naturelle
        P_joule = (p.R0 + p.R1 + p.R2) * current_A ** 2
        dT      = (P_joule - h_coeff * (st.temp - T_ambient)) / m_cp
        st.temp = st.temp + dT * dt
        return st

    def reset(self, soc0: Optional[float] = None):
        soc = soc0 if soc0 is not None else self.p.soc0
        self.state = CellState(soc=soc)
        self.state.voltage = float(self._ocv(soc))


class PackSimulator:
    """
    Simulateur de pack Ns × Np cellules Li-ion.

    Les cellules en série partagent le même courant.
    Les groupes en parallèle partagent la même tension.

    Args:
        ns              : nombre de cellules en série
        np_             : nombre de branches parallèles
        base_params     : paramètres nominaux d'une cellule
        ocv_poly_coeffs : coefficients polynôme OCV(SOC)
        capacity_spread : écart-type relatif sur Q_nom (manufacturing spread)
        resistance_spread: écart-type relatif sur R0
        seed            : graine aléatoire pour reproductibilité
    """

    def __init__(
        self,
        ns: int,
        np_: int,
        base_params: CellParams,
        ocv_poly_coeffs: list,
        capacity_spread: float = 0.02,
        resistance_spread: float = 0.05,
        seed: int = 42,
    ):
        self.ns  = ns
        self.np_ = np_
        self.n_cells = ns * np_
        rng = np.random.default_rng(seed)

        self.cells: list[CellSimulator] = []
        for i in range(self.n_cells):
            p = CellParams(
                R0      = base_params.R0 * (1 + rng.normal(0, resistance_spread)),
                R1      = base_params.R1,
                C1      = base_params.C1,
                R2      = base_params.R2,
                C2      = base_params.C2,
                Q_nom_Ah= base_params.Q_nom_Ah * (1 + rng.normal(0, capacity_spread)),
                soc0    = base_params.soc0,
            )
            self.cells.append(CellSimulator(p, ocv_poly_coeffs, cell_id=i))

        self.history: list[dict] = []
        self.t = 0.0

    # ── Accès cellules ──────────────────────────────────────────────────

    def cell_grid(self) -> np.ndarray:
        """Retourne les cellules en grille [ns, np_]."""
        return np.array(self.cells).reshape(self.ns, self.np_)

    # ── Simulation ──────────────────────────────────────────────────────

    def step(self, pack_current_A: float, dt: float, T_ambient: float = 25.0) -> dict:
        """
        Avance le pack d'un pas dt.
        pack_current_A : courant total du pack (convention I < 0 = décharge).
        Chaque cellule en série reçoit pack_current_A / np_ (courant parallèle).
        """
        cell_current = pack_current_A / self.np_

        for cell in self.cells:
            cell.step(cell_current, dt, T_ambient)

        self.t += dt
        state = self._pack_state()
        self.history.append(state)
        return state

    def simulate(
        self,
        current_profile: np.ndarray,
        dt: float = 1.0,
        T_ambient: float = 25.0,
    ) -> list[dict]:
        """Simulation complète sur un profil de courant."""
        self.history = []
        self.t = 0.0
        for I in current_profile:
            self.step(I, dt, T_ambient)
        return self.history

    def set_temperature(self, T: float):
        """Initialise toutes les cellules à la température T (°C) immédiatement."""
        for cell in self.cells:
            cell.state.temp = float(T)

    def reset(self, soc0: float = 1.0):
        self.t = 0.0
        self.history = []
        for cell in self.cells:
            cell.reset(soc0)

    # ── État agrégé du pack ─────────────────────────────────────────────

    def _pack_state(self) -> dict:
        grid = self.cell_grid()  # [ns, np_]

        # Tension pack = somme des tensions moyennes de chaque rang série
        V_per_row   = np.mean([[c.state.voltage for c in row] for row in grid], axis=1)
        V_pack      = float(np.sum(V_per_row))

        socs    = np.array([c.state.soc  for c in self.cells])
        temps   = np.array([c.state.temp for c in self.cells])
        voltages= np.array([c.state.voltage for c in self.cells])

        return {
            "t":            self.t,
            "V_pack":       V_pack,
            "I_pack":       self.cells[0].state.current * self.np_,
            "SOC_mean":     float(socs.mean()),
            "SOC_min":      float(socs.min()),
            "SOC_max":      float(socs.max()),
            "SOC_imbalance": float(socs.max() - socs.min()),
            "T_mean":       float(temps.mean()),
            "T_max":        float(temps.max()),
            "V_cell_min":   float(voltages.min()),
            "V_cell_max":   float(voltages.max()),
            "socs":         socs.tolist(),
            "temps":        temps.tolist(),
            "voltages":     voltages.tolist(),
        }

    @property
    def pack_soc(self) -> float:
        return float(np.mean([c.state.soc for c in self.cells]))

    @property
    def pack_voltage(self) -> float:
        grid = self.cell_grid()
        return float(sum(np.mean([c.state.voltage for c in row]) for row in grid))
