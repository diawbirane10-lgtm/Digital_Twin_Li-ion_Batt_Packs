import numpy as np
from fastapi.testclient import TestClient
from digital_twin.api.dashboard import app, sessions
from estimation.soc.kalman.ekf import BatteryEKF

client=TestClient(app)

def test_sessions_and_physics():
    first=client.post('/sessions',json={'ns':4,'np':2,'temperature':30,'soc':1}).json()
    second=client.post('/sessions',json={'ns':12,'np':4}).json()
    assert first['state']['pack_voltage']>10
    assert len(first['cells'])==8
    result=client.post('/sessions/'+first['session_id']+'/advance',json={'seconds':60,'c_rate':1,'mode':'discharge'})
    assert result.status_code==200
    result=result.json()
    assert result['state']['timestamp']==60
    assert result['cells'][0]['soc']<first['cells'][0]['soc']
    assert result['state']['current']<0
    assert client.get('/sessions/'+second['session_id']).json()['state']['timestamp']==0
    assert result['cycle_count']==0

def test_validation_and_limit():
    assert client.post('/sessions',json={'ns':1000}).status_code==422
    state=client.post('/sessions',json={'soc':0.05}).json()
    result=client.post('/sessions/'+state['session_id']+'/advance',json={'seconds':120}).json()
    assert result['stop_reason']
    assert result['state']['timestamp']==0
    assert client.post('/sessions/'+state['session_id']+'/advance',json={'seconds':121}).status_code==422
    assert client.get('/sessions/not-found').status_code==404

def test_ekf_ohmic_drop_is_not_charge_error():
    ekf=BatteryEKF(.1,.01,1000,.01,1000,2,[1,3],soc0=.8)
    ekf.predict(-2,1)
    before=ekf.soc
    voltage=3+before-.2+ekf.vc1+ekf.vc2
    ekf.update(voltage)
    assert abs(ekf.soc-before)<1e-10
    assert np.all(np.linalg.eigvalsh(ekf.P)>=0)
