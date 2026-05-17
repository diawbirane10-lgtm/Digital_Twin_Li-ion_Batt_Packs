"""
Extended Kalman Filter (EKF) pour estimation du SOC de cellule Li-ion.

Modèle : ECM Thevenin 2RC
État   : x = [SOC, Vc1, Vc2]
Mesure : z = V_terminal

Convention courant : I < 0 en décharge, I > 0 en charge (NASA/standard BMS).
"""

import numpy as np


class BatteryEKF:
    """
    EKF pour estimation temps-réel de SOC sur modèle ECM 2RC.

    Usage minimal :
        ekf = BatteryEKF(R0=0.015, R1=0.01, C1=2000, R2=0.005, C2=20000,
                         Q_nom_Ah=2.0, ocv_poly_coeffs=[...])
        for t, i, v in zip(time, current, voltage):
            ekf.predict(i, dt)
            ekf.update(v)
            soc = ekf.soc
    """

    def __init__(
        self,
        R0: float,
        R1: float,
        C1: float,
        R2: float,
        C2: float,
        Q_nom_Ah: float,
        ocv_poly_coeffs: list,
        Q_noise: np.ndarray | None = None,
        R_noise: np.ndarray | None = None,
        soc0: float = 1.0,
    ):
        self.R0   = R0
        self.R1   = R1
        self.C1   = C1
        self.R2   = R2
        self.C2   = C2
        self.Q_As = Q_nom_Ah * 3600
        self._ocv = np.poly1d(ocv_poly_coeffs)

        # Matrices de bruit (ajustables)
        self.Q_noise = Q_noise if Q_noise is not None else np.diag([1e-6, 1e-6, 1e-6])
        self.R_noise = R_noise if R_noise is not None else np.array([[5e-4]])

        self.reset(soc0)

    # ── API publique ────────────────────────────────────────────────────

    def reset(self, soc0: float = 1.0):
        """Réinitialise l'état de l'EKF."""
        self.x = np.array([[soc0], [0.0], [0.0]])   # [SOC, Vc1, Vc2]
        self.P = np.diag([1e-3, 1e-3, 1e-3])        # Covariance initiale

    def predict(self, current_A: float, dt: float):
        """Étape de prédiction (modèle ECM discret)."""
        if dt <= 0:
            return
        soc, vc1, vc2 = self.x.flatten()
        tau1 = max(self.R1 * self.C1, 1e-9)
        tau2 = max(self.R2 * self.C2, 1e-9)
        a1   = np.exp(-dt / tau1)
        a2   = np.exp(-dt / tau2)

        # État prédit
        soc_p = float(np.clip(soc + current_A * dt / self.Q_As, 0.0, 1.0))
        vc1_p = a1 * vc1 + self.R1 * (1 - a1) * current_A
        vc2_p = a2 * vc2 + self.R2 * (1 - a2) * current_A
        self.x = np.array([[soc_p], [vc1_p], [vc2_p]])

        # Jacobien F = d(f)/d(x)  [3x3, linéaire → exact]
        F = np.array([
            [1.0, 0.0, 0.0],
            [0.0,  a1, 0.0],
            [0.0, 0.0,  a2],
        ])

        # Propagation covariance
        self.P = F @ self.P @ F.T + self.Q_noise

    def update(self, V_measured: float):
        """Étape de correction depuis la mesure de tension."""
        soc, vc1, vc2 = self.x.flatten()

        # Tension prédite par le modèle
        ocv_val  = float(self._ocv(soc))
        V_pred   = ocv_val + self.R0 * 0.0 + vc1 + vc2  # I déjà intégré dans Vc
        # Note : on utilise la tension OCV + Vc (R0*I est dans la prédiction)

        # Innovation
        y = V_measured - (ocv_val + vc1 + vc2)

        # Jacobien H = d(h)/d(x)  [1x3]
        docv_dsoc = float(self._ocv.deriv()(soc))
        H = np.array([[docv_dsoc, 1.0, 1.0]])

        # Gain de Kalman
        S = H @ self.P @ H.T + self.R_noise
        K = self.P @ H.T @ np.linalg.inv(S)           # [3x1]

        # Correction état et covariance
        self.x = self.x + K * y
        self.x[0, 0] = float(np.clip(self.x[0, 0], 0.0, 1.0))  # SOC ∈ [0,1]
        I3 = np.eye(3)
        self.P = (I3 - K @ H) @ self.P

    # ── Propriétés pratiques ────────────────────────────────────────────

    @property
    def soc(self) -> float:
        return float(self.x[0, 0])

    @property
    def vc1(self) -> float:
        return float(self.x[1, 0])

    @property
    def vc2(self) -> float:
        return float(self.x[2, 0])

    @property
    def soc_std(self) -> float:
        """Incertitude 1-sigma sur le SOC."""
        return float(np.sqrt(self.P[0, 0]))

    def state_dict(self) -> dict:
        return {"soc": self.soc, "vc1": self.vc1, "vc2": self.vc2,
                "soc_std": self.soc_std}
