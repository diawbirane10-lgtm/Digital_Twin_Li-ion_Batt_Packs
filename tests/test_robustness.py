import numpy as np
import pytest
from diagnostics.telemetry import analyse_csv


def analyse(t,v,i):
    text='time_s,pack_voltage_v,pack_current_a\n'+'\n'.join(f'{a},{b},{c}' for a,b,c in zip(t,v,i))
    return analyse_csv(text,'positive_discharge',{'temperature_c':55,'cell_spread_v':.1},{})

@pytest.mark.parametrize('seed',range(20))
def test_noise_energy_and_sign_invariance(seed):
    rng=np.random.default_rng(seed);t=np.arange(3601);v=np.full(len(t),400.);i=10+rng.normal(0,.2,len(t))
    result=analyse(t,v,i)['metrics'];opposite=analyse(t,v,-i)['metrics']
    assert abs(result['discharge_wh']-4000)/4000 < .002
    assert result['discharge_wh']==pytest.approx(opposite['charge_wh'])
    assert result['charge_wh']==0

def test_missing_chunk_flagged():
    t=np.concatenate([np.arange(100),np.arange(200,300)])
    result=analyse(t,np.full(len(t),400),np.full(len(t),10))
    assert result['metrics']['sampling_gaps']==1
    assert any(f['code']=='sampling_gaps' for f in result['findings'])

@pytest.mark.parametrize('timestamp',[float('nan'),float('inf'),0,-1])
def test_invalid_time_rejected(timestamp):
    with pytest.raises(ValueError):analyse([0,timestamp],[400,400],[10,10])

@pytest.mark.parametrize('line',['0,400,10,999','0,400'])
def test_ragged_csv_rejected(line):
    with pytest.raises(ValueError):
        analyse_csv('time_s,pack_voltage_v,pack_current_a\n'+line+'\n1,400,10','positive_discharge',{'temperature_c':55,'cell_spread_v':.1},{})
