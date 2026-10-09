"""Session-isolated API for the web IHM; run one worker (in-memory sessions)."""
import json
import os
import time
from pathlib import Path
from threading import RLock
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from digital_twin.core.twin_engine import BatteryDigitalTwin, TwinState

ROOT = Path(__file__).resolve().parents[2]
ECM = json.loads((ROOT / 'ml/models/ecm_b0005.json').read_text())
app = FastAPI(title='Battery Twin Dashboard', version='2.0.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('DASHBOARD_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','), allow_methods=['GET','POST','DELETE'], allow_headers=['Content-Type'])
lock = RLock()
sessions = {}
TTL = 3600

class Configuration(BaseModel):
    ns: int = Field(12, ge=1, le=24)
    np: int = Field(4, ge=1, le=8)
    temperature: float = Field(25, ge=0, le=55)
    soc: float = Field(1, ge=0.05, le=1)

class Advance(BaseModel):
    seconds: int = Field(10, ge=1, le=120)
    c_rate: float = Field(1, ge=0.1, le=3)
    mode: Literal['discharge','charge'] = 'discharge'


def lookup(key):
    now = time.monotonic()
    for expired in [k for k,v in sessions.items() if now-v['access'] > TTL]:
        del sessions[expired]
    if key not in sessions:
        raise HTTPException(404, 'Session expirée. Créez une nouvelle simulation.')
    sessions[key]['access'] = now
    return sessions[key]


def snapshot(twin):
    pack = twin.pack._pack_state()
    return TwinState(timestamp=twin._t, soc=twin.ekf.soc, soc_std=twin.ekf.soc_std,
        soh=twin.soh_est.soh, rul_cycles=twin.soh_est.rul_cycles,
        voltage=pack['V_pack'], current=pack['I_pack'], temperature=pack['T_mean'],
        pack_voltage=pack['V_pack'], V_cell_min=pack['V_cell_min'], V_cell_max=pack['V_cell_max'],
        T_max=pack['T_max'], soc_imbalance=pack['SOC_imbalance'], alerts=twin._check_bms(pack))


def payload(session):
    twin = session['twin']
    cells = [dict(id=i, row=i//twin.pack.np_, col=i%twin.pack.np_, soc=c.state.soc,
        voltage=c.state.voltage, temperature=c.state.temp, current=c.state.current)
        for i,c in enumerate(twin.pack.cells)]
    history = twin._history
    stride = max(1, (len(history)+599)//600)
    sampled = history[::stride]
    if history and sampled[-1] is not history[-1]: sampled.append(history[-1])
    return dict(state=twin.state.to_dict(), cells=cells, history=[s.to_dict() for s in sampled],
        configuration=session['config'].model_dump(), limits=twin.bms, stop_reason=session['stop'],
        cycle_count=len(twin.soh_est.soh_history), cycle_history=twin.soh_est.soh_history.tolist())

@app.get('/health')
def health(): return {'status':'ok', 'version':'2.0.0'}

@app.post('/sessions')
def create(config: Configuration):
    with lock:
        # Remove idle sessions before enforcing resource cap.
        now=time.monotonic()
        for key in [k for k,v in sessions.items() if now-v['access']>TTL]: del sessions[key]
        if len(sessions)>=32: raise HTTPException(503, 'Capacité atteinte. Réessayez plus tard.')
        twin=BatteryDigitalTwin(ECM, config.ns, config.np)
        twin.reset(config.soc)
        twin.pack.set_temperature(config.temperature)
        twin.state=snapshot(twin)
        key=str(uuid4())
        sessions[key]={'twin':twin,'config':config,'access':now,'stop':None,'capacity':0.0,'cycle_recorded':False}
        return {'session_id':key, **payload(sessions[key])}

@app.get('/sessions/{key}')
def state(key: str):
    with lock: return payload(lookup(key))

@app.post('/sessions/{key}/advance')
def advance(key: str, request: Advance):
    with lock:
        session=lookup(key)
        twin=session['twin']
        session['stop']=None
        factor=min(1.02,1+0.0005*(session['config'].temperature-25)) if session['config'].temperature>=25 else max(0.4,1-0.008*(25-session['config'].temperature))
        magnitude=ECM['Q_nom_Ah']*factor*twin.pack.np_*request.c_rate
        current=-magnitude if request.mode=='discharge' else magnitude*0.5
        for _ in range(request.seconds):
            if (request.mode=='discharge' and twin.pack.pack_soc<=0.05) or (request.mode=='charge' and twin.pack.pack_soc>=0.95):
                session['stop']='Limite de charge atteinte'
                break
            result=twin.update(twin.pack.pack_voltage,current,session['config'].temperature,1)
            if current<0: session['capacity']+=-current/twin.pack.np_/3600
            if result.alerts:
                session['stop']='Protection BMS déclenchée'
                break
        # A simulated partial discharge is not an experimental SOH measurement.
        # Do not infer capacity aging from a model with fixed cell parameters.
        # Bound history storage independently of response downsampling.
        if len(twin._history)>20000: twin._history=twin._history[-20000:]
        twin.pack.history=twin.pack.history[-20000:]
        return payload(session)

@app.delete('/sessions/{key}')
def delete(key: str):
    with lock: sessions.pop(key,None)
    return {'deleted':True}

# Telemetry analysis is independent from the NASA simulation model.
from diagnostics.telemetry import analyse_csv

class DiagnosticRequest(BaseModel):
    csv_text: str = Field(..., min_length=1, max_length=5_000_000)
    current_convention: Literal['positive_discharge','negative_discharge']
    temperature_threshold_c: float = Field(55, ge=-20, le=100)
    cell_spread_threshold_v: float = Field(0.1, ge=0.001, le=2)
    vehicle: str = Field('Non précisé', max_length=160)
    source: str = Field('Import utilisateur', max_length=500)
    data_kind: Literal['measured','synthetic'] = 'measured'

@app.get('/diagnostics/sources')
def diagnostic_sources():
    return json.loads((ROOT / 'diagnostics/sources.json').read_text())

@app.post('/diagnostics/analyse')
def diagnostic_analysis(request: DiagnosticRequest):
    try:
        return analyse_csv(request.csv_text, request.current_convention,
            {'temperature_c':request.temperature_threshold_c,'cell_spread_v':request.cell_spread_threshold_v},
            {'vehicle':request.vehicle,'source':request.source,'data_kind':request.data_kind})
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
