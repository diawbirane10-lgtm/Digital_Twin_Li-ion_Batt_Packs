from fastapi.testclient import TestClient
from digital_twin.api.serverless import app
from digital_twin.api import dashboard as d

client=TestClient(app)
def test_checkpoint_survives_cold_start():
    before=len(d.sessions)
    config={'ns':2,'np':2,'soc':.8,'temperature':25}
    first=client.post('/api/simulation',json={'configuration':config}).json()
    assert len(d.sessions)==before
    second=client.post('/api/simulation',json={'configuration':config,'checkpoint':first['checkpoint'],'step':{'seconds':10,'c_rate':1}})
    assert second.status_code==200
    result=second.json();assert result['state']['timestamp']==10
    third=client.post('/api/simulation',json={'configuration':config,'checkpoint':result['checkpoint'],'step':{'seconds':10,'c_rate':1}}).json()
    assert third['state']['timestamp']==20
    assert third['state']['pack_voltage']<result['state']['pack_voltage']
    assert len(d.sessions)==before

def test_corrupt_checkpoint_rejected():
    config={'ns':1,'np':1};first=client.post('/api/simulation',json={'configuration':config}).json()
    first['checkpoint']['p']=[-1]*9
    assert client.post('/api/simulation',json={'configuration':config,'checkpoint':first['checkpoint']}).status_code==422
