from diagnostics.telemetry import analyse_csv
from fastapi.testclient import TestClient
from digital_twin.api.dashboard import app
import pytest

LIMITS={'temperature_c':55,'cell_spread_v':.1}

def test_energy_and_sign_convention():
    csv='time_s,pack_voltage_v,pack_current_a\n0,100,10\n3600,100,10\n'
    result=analyse_csv(csv,'positive_discharge',LIMITS,{})
    assert result['metrics']['discharge_wh']==1000
    assert result['metrics']['discharge_ah']==10
    reverse=analyse_csv(csv,'negative_discharge',LIMITS,{})
    assert reverse['metrics']['charge_wh']==1000
    assert reverse['capabilities']['soh']=='insufficient_evidence'

def test_evidence_and_no_oem_claim():
    csv='time_s,pack_voltage_v,pack_current_a,temperature_c,cell_min_v,cell_max_v\n0,400,10,25,3.5,3.6\n1,400,10,60,3.5,3.8\n'
    result=analyse_csv(csv,'positive_discharge',LIMITS,{})
    assert {f['code'] for f in result['findings']}=={'temperature','cell_spread'}
    assert result['capabilities']['weak_cell_localisation']=='insufficient_evidence'

@pytest.mark.parametrize('csv',[
 'time_s,pack_voltage_v,pack_current_a\n0,100,nan\n1,100,1\n',
 'time_s,pack_voltage_v,pack_current_a\n1,100,1\n0,100,1\n',
 'time_s,pack_voltage_v,pack_current_a,soc_pct\n0,100,1,101\n1,100,1,90\n'])
def test_invalid_data_rejected(csv):
    with pytest.raises(ValueError): analyse_csv(csv,'positive_discharge',LIMITS,{})

def test_endpoint_and_source_registry():
    client=TestClient(app)
    assert len(client.get('/diagnostics/sources').json())>=4
    assert client.post('/diagnostics/analyse',json={'csv_text':'bad','current_convention':'positive_discharge'}).status_code==422


def test_charge_discharge_crossing_split():
    csv='time_s,pack_voltage_v,pack_current_a\n0,100,-10\n3600,100,10\n'
    result=analyse_csv(csv,'positive_discharge',LIMITS,{})
    assert result['metrics']['discharge_ah']==2.5
    assert result['metrics']['charge_ah']==2.5
    assert result['metrics']['discharge_wh']==250
