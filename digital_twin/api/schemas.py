"""Schémas Pydantic pour l'API FastAPI du Digital Twin."""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Requêtes ──────────────────────────────────────────────────────────────────

class UpdateRequest(BaseModel):
    """Corps de POST /twin/update."""
    voltage:     float = Field(..., ge=0.0, le=6.0,    description="Tension mesurée (V)")
    current:     float = Field(..., ge=-20.0, le=20.0, description="Courant (A) — I<0 décharge")
    temperature: float = Field(25.0, ge=-40.0, le=80.0, description="T ambiante (°C)")
    dt:          float = Field(1.0,  ge=0.01, le=60.0,  description="Pas de temps (s)")

    model_config = {
        "json_schema_extra": {
            "example": {"voltage": 3.85, "current": -2.0, "temperature": 30.0, "dt": 1.0}
        }
    }


class EndCycleRequest(BaseModel):
    """Corps de POST /twin/end_cycle."""
    measured_capacity_Ah: Optional[float] = Field(
        None, ge=0.0, le=10.0,
        description="Capacité déchargée mesurée (Ah). None = utilise la valeur interne."
    )


class ResetRequest(BaseModel):
    """Corps de POST /twin/reset."""
    soc0: float = Field(1.0, ge=0.0, le=1.0, description="SOC initial après reset [0–1]")


class ConfigRequest(BaseModel):
    """Corps de POST /twin/configure."""
    pack_ns: int   = Field(12, ge=1, le=100, description="Cellules en série")
    pack_np: int   = Field(4,  ge=1, le=50,  description="Branches parallèles")
    T_init:  float = Field(25.0, ge=-40.0, le=80.0, description="Température initiale (°C)")


# ── Réponses ──────────────────────────────────────────────────────────────────

class TwinStateResponse(BaseModel):
    """État complet du jumeau numérique."""
    timestamp:     float
    soc:           float = Field(..., description="SOC estimé EKF [0–1]")
    soc_std:       float = Field(..., description="Incertitude SOC (écart-type σ)")
    soh:           float = Field(..., description="SOH actuel [0–1]")
    rul_cycles:    Optional[int]  = Field(None, description="RUL estimé (cycles)")
    voltage:       float
    current:       float
    temperature:   float
    pack_voltage:  float
    V_cell_min:    float
    V_cell_max:    float
    T_max:         float
    soc_imbalance: float
    alerts:        List[str]


class HistoryResponse(BaseModel):
    """Historique de simulation (séries temporelles)."""
    n_points:      int
    timestamps:    List[float]
    soc:           List[float]
    soh:           List[float]
    pack_voltage:  List[float]
    T_max:         List[float]
    current:       List[float]
    soc_imbalance: List[float]
    alerts_count:  List[int]


class PackInfoResponse(BaseModel):
    """Informations statiques du pack."""
    ns:           int
    np_:          int
    n_cells:      int
    V_nominal:    float
    E_nominal_Wh: float
    Q_nom_Ah:     float


class HealthResponse(BaseModel):
    """Health check de l'API."""
    status:     str  = "ok"
    version:    str  = "1.0.0"
    twin_ready: bool
