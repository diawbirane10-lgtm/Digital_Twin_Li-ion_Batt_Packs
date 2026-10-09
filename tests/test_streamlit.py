from pathlib import Path
from streamlit.testing.v1 import AppTest

ENTRY=Path(__file__).resolve().parents[1]/'app.py'

def start():
    app=AppTest.from_file(str(ENTRY),default_timeout=20).run()
    assert not app.exception
    return app

def test_primary_app_step_reset_and_navigation():
    app=start()
    app.button[3].click().run()
    assert not app.exception
    assert app.session_state['snapshot']['state']['timestamp']==10
    app.radio[0].set_value('Cellules').run()
    assert not app.exception
    assert len(app.dataframe)==1
    app.radio[0].set_value('Simulation').run()
    app.button[0].click().run()
    assert app.session_state['snapshot']['state']['timestamp']==0
    assert app.session_state['history']==[]

def test_diagnostic_synthetic_invalid_and_navigation_pause():
    app=start()
    app.radio[0].set_value('Diagnostic').run()
    app.button[0].click().run()
    app.button[1].click().run()
    assert not app.exception
    report=app.session_state['report']
    assert report['metadata']['data_kind']=='synthetic'
    assert any(f['code']=='cell_spread' for f in report['findings'])
    app.text_area[0].set_value('invalid').run()
    app.button[1].click().run()
    assert app.session_state['report'] is None
    assert any('Colonnes requises' in e.value for e in app.error)
    assert not app.session_state['running']
