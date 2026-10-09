"""Stateless simulation transport. Client checkpoints are untrusted simulation inputs."""
from dataclasses import asdict
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field, ConfigDict
from digital_twin.api import dashboard as d
from digital_twin.core.twin_engine import TwinState
from simulation.pack.pack_simulator import CellState

class CellCheckpoint(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra='forbid')
    soc: float = Field(ge=0,le=1)
    vc1: float = Field(ge=-100,le=100)
    vc2: float = Field(ge=-100,le=100)
    temp: float = Field(ge=-100,le=200)
    voltage: float = Field(ge=-100,le=100)
    current: float = Field(ge=-1000,le=1000)
    cycle: int = Field(ge=0,le=100000)

class Checkpoint(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    cells: list[CellCheckpoint] = Field(max_length=192)
    x: list[float] = Field(min_length=3,max_length=3)
    p: list[float] = Field(min_length=9,max_length=9)
    time: float = Field(ge=0,le=20000)
    current: float = Field(ge=-1000,le=1000)

class Simulation(BaseModel):
    configuration: d.Configuration
    checkpoint: Checkpoint | None = None
    step: d.Advance | None = None

app=FastAPI(title='Battery Twin stateless API')
app.add_api_route('/api/health',d.health,methods=['GET'])
app.add_api_route('/api/diagnostics/sources',d.diagnostic_sources,methods=['GET'])
app.add_api_route('/api/diagnostics/analyse',d.diagnostic_analysis,methods=['POST'])

@app.post('/api/simulation')
def simulation(request: Simulation):
    with d.lock:
        initial=d.create(request.configuration)
        key=initial['session_id']
        try:
            session=d.sessions[key];twin=session['twin'];cp=request.checkpoint
            if cp:
                if len(cp.cells)!=len(twin.pack.cells):
                    raise d.HTTPException(422,'Topologie du checkpoint incohérente.')
                p=np.array(cp.p).reshape(3,3);x=np.array(cp.x).reshape(3,1)
                if not 0<=x[0,0]<=1 or np.max(np.abs(x[1:]))>100 or not np.allclose(p,p.T) or np.linalg.eigvalsh(p).min()<0 or p.max()>100:
                    raise d.HTTPException(422,'État Kalman invalide.')
                for cell,state in zip(twin.pack.cells,cp.cells):cell.state=CellState(**state.model_dump())
                twin.ekf.x=x;twin.ekf.P=p;twin.ekf._current_A=cp.current;twin._t=cp.time
                twin.state=d.snapshot(twin)
            if twin._t+(request.step.seconds if request.step else 0)>20000:
                raise d.HTTPException(422,'Limite de simulation : 20 000 secondes. Réinitialisez.')
            result=d.advance(key,request.step) if request.step else d.payload(session)
            result['checkpoint']={'cells':[asdict(c.state) for c in twin.pack.cells],'x':twin.ekf.x.ravel().tolist(),'p':twin.ekf.P.ravel().tolist(),'time':twin._t,'current':twin.ekf._current_A}
            result['session_id']='stateless'
            return result
        finally:d.sessions.pop(key,None)
