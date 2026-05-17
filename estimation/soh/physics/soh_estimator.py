"""
Estimateur SOH basé sur la dégradation de capacité.
SOH(n) = Q_n / Q_nominal
"""
import numpy as np
import pandas as pd
from pathlib import Path


class SOHEstimator:
    """
    Estime le SOH et le RUL (Remaining Useful Life) d'une cellule.

    Usage :
        est = SOHEstimator(Q_nominal=2.0, eol_threshold=0.80)
        est.add_cycle(cycle_capacity_Ah)
        print(est.soh, est.rul_cycles)
    """

    def __init__(self, Q_nominal: float = 2.0, eol_threshold: float = 0.80):
        self.Q_nom      = Q_nominal
        self.eol        = eol_threshold
        self._capacities: list[float] = []

    def add_cycle(self, capacity_Ah: float):
        self._capacities.append(capacity_Ah)

    @property
    def soh(self) -> float:
        if not self._capacities:
            return 1.0
        return float(self._capacities[-1] / self.Q_nom)

    @property
    def soh_history(self) -> np.ndarray:
        return np.array(self._capacities) / self.Q_nom

    @property
    def rul_cycles(self) -> int | None:
        """Estimation linéaire du RUL (cycles jusqu'à EOL)."""
        h = self.soh_history
        if len(h) < 5:
            return None
        x = np.arange(len(h))
        slope, intercept = np.polyfit(x, h, 1)
        if slope >= 0:
            return None
        rul = int((self.eol - h[-1]) / slope)
        return max(0, rul)

    def to_dataframe(self) -> pd.DataFrame:
        h = self.soh_history
        return pd.DataFrame({
            "cycle":       np.arange(1, len(h) + 1),
            "capacity_Ah": np.array(self._capacities),
            "soh":         h,
            "soh_pct":     h * 100,
        })
