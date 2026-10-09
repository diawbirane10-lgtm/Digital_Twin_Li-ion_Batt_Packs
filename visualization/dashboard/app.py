"""Primary Streamlit IHM; shared simulation and diagnostics with the web version."""
import html
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
for _ in range(4):
    if (ROOT/'ml/models/ecm_b0005.json').exists(): break
    ROOT=ROOT.parent
sys.path.insert(0,str(ROOT))
from digital_twin.api.serverless import Simulation, simulation
from diagnostics.telemetry import analyse_csv

st.set_page_config(page_title='Battery Twin',page_icon='🔋',layout='wide')
st.markdown('''<style>
[data-testid="stAppViewContainer"] { background:#f7f9fc; color:#13233e; }
[data-testid="stSidebar"] { background:#101d31; }
[data-testid="stSidebar"] * { color:#e4ebf3; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] a, [data-testid="stSidebar"] a * { color:#13233e!important; }
[data-testid="stApp"] * { border-radius:0!important; }
.block-container { padding-top:2rem; max-width:1600px; }
button, input, textarea, select, [data-baseweb="select"] > div,
[data-testid="stMetric"], [data-testid="stAlert"],
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stFileUploaderDropzone"]
{ border-radius:0!important; }
[data-testid="stMetric"] { background:white;border:1px solid #dce3eb;padding:16px; }
h1,h2,h3 { color:#13233e!important; }
.operator { border:1px solid #dce3eb;border-left:4px solid #667789;background:white;padding:14px 18px;margin:12px 0 22px; }
.operator.attention { border-left-color:#ad7000; }
.cell-grid { display:grid;gap:7px;overflow-x:auto; }
.cell { min-width:70px;border:1px solid #cbd4de;background:#e5e9ed;padding:10px;text-align:center; }
.cell.abnormal { border:2px solid #ad7000;background:#fff0cc; }
.cell strong { display:block;font-size:17px;margin-top:5px; }
@media(max-width:640px){.block-container{padding:1rem}.cell{min-width:60px}}
</style>''',unsafe_allow_html=True)

if 'configuration' not in st.session_state:
    st.session_state.configuration=dict(ns=12,np=4,temperature=25.,soc=1.)
    st.session_state.snapshot=simulation(Simulation(configuration=st.session_state.configuration))
    st.session_state.history=[]
    st.session_state.running=False
if 'report' not in st.session_state: st.session_state.report=None

with st.sidebar:
    st.title('Battery Twin')
    st.caption('Jumeau numérique de batteries')
    page=st.radio('Navigation',['Vue d’ensemble','Cellules','Analyse','Simulation','Diagnostic'],label_visibility='collapsed')
    st.divider()
    st.caption('Streamlit · Application principale')
    st.link_button('Ouvrir la version web Vercel','https://battery-twin-birane.vercel.app',width='stretch')
    st.caption('Birane Diaw · ECM 2RC / EKF · Données NASA')

if page=='Diagnostic': st.session_state.running=False
st.title(page)
st.caption('Mesures importées · Analyse multi-marques' if page=='Diagnostic' else 'Modèle laboratoire NASA B0005 · Simulation électrique et thermique')


def chart(frame,column,label,unit,scale=1):
    fig=go.Figure(go.Scatter(x=frame['timestamp'],y=frame[column]*scale,mode='lines',line=dict(color='#536577',width=2),name=label))
    fig.update_layout(template='plotly_white',height=300,margin=dict(l=35,r=20,t=20,b=35),xaxis_title='Temps simulé (s)',yaxis_title=f'{label} ({unit})',paper_bgcolor='white',plot_bgcolor='white')
    st.plotly_chart(fig,width='stretch')


def advance():
    try:
        old=st.session_state.snapshot
        result=simulation(Simulation(configuration=st.session_state.configuration,checkpoint=old['checkpoint'],step={'seconds':st.session_state.get('step_seconds',10),'c_rate':st.session_state.get('c_rate',1.),'mode':'charge' if st.session_state.get('mode','Décharge')=='Charge' else 'discharge'}))
        st.session_state.snapshot=result
        st.session_state.history=(st.session_state.history+result['history'])[-20000:]
        if result['stop_reason']:st.session_state.running=False
    except Exception as exc:
        st.session_state.running=False
        st.error(f'Simulation arrêtée : {exc}')


if page=='Diagnostic':
    st.markdown('<div class="operator"><b>Analyse hors ligne · télémétrie importée</b><br>Seuils analyste · aucune qualification constructeur</div>',unsafe_allow_html=True)
    left,right=st.columns([2,1])
    with left,st.container(border=True):
        st.subheader('Importer une télémétrie')
        upload=st.file_uploader('Fichier CSV',type=['csv'])
        if st.button('Charger un exemple synthétique'):
            st.session_state.csv_text='time_s,pack_voltage_v,pack_current_a,temperature_c,cell_min_v,cell_max_v\n0,400,30,30,3.70,3.73\n60,398,35,32,3.66,3.72\n120,396,40,36,3.59,3.73\n180,397,-10,38,3.62,3.75\n240,398,-15,39,3.66,3.76'
            st.session_state.data_kind='Synthétiques'
            st.session_state.report=None
        text=st.text_area('Mesures CSV',key='csv_text',height=180)
        vehicle=st.text_input('Véhicule / module','Non renseigné')
        source=st.text_input('Source des mesures','Non renseignée')
        kind=st.selectbox('Nature des données',['Mesurées','Synthétiques'],key='data_kind')
        convention=st.selectbox('Convention du courant',['Positif = décharge','Négatif = décharge'])
        a,b=st.columns(2)
        temp=a.number_input('Seuil température (°C)',min_value=-20.,max_value=100.,value=55.)
        spread=b.number_input('Seuil dispersion (mV)',min_value=1.,max_value=2000.,value=100.)
        if st.button('Analyser les mesures',type='primary'):
            st.session_state.report=None
            try:
                if upload is not None and upload.size>5_000_000:raise ValueError('Fichier limité à 5 Mo.')
                content=upload.getvalue().decode('utf-8-sig') if upload is not None else text
                st.session_state.report=analyse_csv(content,'positive_discharge' if convention.startswith('Positif') else 'negative_discharge',{'temperature_c':temp,'cell_spread_v':spread/1000},{'vehicle':vehicle,'source':source,'data_kind':'measured' if kind=='Mesurées' else 'synthetic'})
            except (ValueError,UnicodeError) as exc:st.error(str(exc))
        if upload is not None:st.caption('Le fichier sélectionné est utilisé en priorité sur le texte CSV.')
    with right,st.container(border=True):
        st.subheader('Ce que l’analyse permet')
        st.write('Contrôler la chronologie et les valeurs, intégrer Ah/Wh, détecter des dépassements de température ou de dispersion des tensions.')
        st.subheader('Preuves supplémentaires nécessaires')
        st.write('SOH, durée de vie et localisation d’une cellule faible nécessitent des mesures et un protocole adaptés.')
        st.code('time_s,pack_voltage_v,pack_current_a',language=None)
        st.caption('Optionnels : temperature_c, soc_pct, cell_min_v et cell_max_v ensemble. Maximum 20 000 lignes / 5 Mo.')
    report=st.session_state.report
    if report:
        with st.container(border=True):
            st.subheader('Rapport d’analyse')
            st.caption(f"{report['metadata']['vehicle']} · {report['metadata']['data_kind']} · {report['metrics']['samples']} mesures")
            m=report['metrics'];cols=st.columns(4)
            for col,label,key,unit in zip(cols,['Énergie déchargée','Énergie chargée','Charge déchargée','Température maximale'],['discharge_wh','charge_wh','discharge_ah','max_temperature_c'],['Wh','Wh','Ah','°C']):
                col.metric(label,'—' if m[key] is None else f'{m[key]:.3f} {unit}')
            for finding in report['findings']:
                with st.container(border=True):
                    st.markdown(('⚠ ' if finding['severity']=='warning' else '')+'**'+finding['title']+'**')
                    st.write('Preuve : '+finding['evidence']);st.caption('Interprétation : '+finding['limitation'])
            for note in report['notes']:st.caption(note)
            st.caption('Empreinte SHA-256 : '+report['sha256'])
            st.download_button('Exporter le rapport JSON',json.dumps(report,ensure_ascii=False,indent=2),'battery-diagnostic-report.json','application/json')
    with st.expander('Sources de référence · statut réel des données'):
        for item in json.loads((ROOT/'diagnostics/sources.json').read_text()):
            st.markdown(f"**[{item['title']}]({item['url']})**")
            st.caption(f"{item['institution']} · {item['level']}")
            st.write(item['status']);st.caption('Licence : '+item['license'])
else:
    with st.expander('Configuration et commandes',expanded=page=='Simulation'):
        with st.form('configuration_form'):
            cols=st.columns(4);config=st.session_state.configuration
            ns=cols[0].number_input('Cellules en série',1,24,int(config['ns']))
            np_=cols[1].number_input('Branches parallèles',1,8,int(config['np']))
            temperature=cols[2].number_input('Température initiale (°C)',0.,55.,float(config['temperature']))
            soc=cols[3].number_input('Charge initiale (%)',5.,100.,float(config['soc']*100))
            if st.form_submit_button('Appliquer et réinitialiser'):
                st.session_state.running=False
                st.session_state.configuration=dict(ns=ns,np=np_,temperature=temperature,soc=soc/100)
                st.session_state.snapshot=simulation(Simulation(configuration=st.session_state.configuration))
                st.session_state.history=[]
        a,b,c=st.columns(3)
        a.selectbox('Mode',['Décharge','Charge'],key='mode')
        b.slider('Courant (C-rate)',.1,3.,1.,.1,key='c_rate')
        c.selectbox('Secondes simulées par pas',[1,10,60,120],index=1,key='step_seconds')
        a,b,c=st.columns(3)
        if a.button('Démarrer',width='stretch'):st.session_state.running=True
        if b.button('Pause',width='stretch'):st.session_state.running=False
        if c.button('Avancer un pas',width='stretch'):st.session_state.running=False;advance()

    @st.fragment(run_every=.5 if st.session_state.running else None)
    def render_simulation():
        if st.session_state.running:advance()
        result=st.session_state.snapshot;s=result['state']
        attention=s['alerts'] or result['stop_reason']
        status='⚠ '+(' · '.join(s['alerts']) or result['stop_reason']) if attention else 'Aucune alerte BMS simulée · ne certifie pas la santé'
        st.markdown(f'<div class="operator {"attention" if attention else ""}"><b>Mode simulation · valeurs calculées</b><br>{html.escape(status)} · Temps : {s["timestamp"]:.0f} s</div>',unsafe_allow_html=True)
        cols=st.columns(4)
        cols[0].metric('Charge estimée (SOC)',f'{s["soc"]*100:.1f} %')
        cols[0].caption(f'Incertitude estimée σ {s["soc_std"]*100:.2f} %')
        cols[1].metric('Tension pack',f'{s["pack_voltage"]:.2f} V')
        cols[2].metric('Température maximale',f'{s["T_max"]:.2f} °C')
        cols[3].metric('Courant pack',f'{s["current"]:.2f} A')
        st.caption('SOH initial : hypothèse non mesurée · RUL indisponible sans essais de capacité. Courant négatif = décharge dans le simulateur.')
        history=pd.DataFrame(st.session_state.history)
        if page in ['Vue d’ensemble','Analyse','Simulation']:
            with st.container(border=True):
                st.subheader('Tendances')
                if history.empty:st.info('Ouvrez Configuration et commandes pour démarrer ou avancer un pas.')
                else:
                    choices={'Charge estimée (%)':('soc','Charge','%',100),'Tension pack (V)':('pack_voltage','Tension','V',1),'Température (°C)':('T_max','Température','°C',1),'Courant (A)':('current','Courant','A',1)}
                    metric=st.selectbox('Grandeur',list(choices));chart(history,*choices[metric])
        if page in ['Vue d’ensemble','Cellules']:
            with st.container(border=True):
                st.subheader('Carte du pack')
                metric=st.selectbox('Grandeur des cellules',['Charge (%)','Température (°C)','Tension (V)'])
                cells=result['cells'];width=min(result['configuration']['ns'],12);tiles=[]
                for cell in sorted(cells,key=lambda c:(c['col'],c['row'])):
                    abnormal=cell['temperature']>55 or cell['voltage']>4.25 or cell['voltage']<2.45
                    value=cell['soc']*100 if metric.startswith('Charge') else cell['temperature'] if metric.startswith('Temp') else cell['voltage']
                    tiles.append(f'<div class="cell {"abnormal" if abnormal else ""}">S{cell["row"]+1}·P{cell["col"]+1}<strong>{"⚠ " if abnormal else ""}{value:.2f}</strong></div>')
                st.markdown(f'<div class="cell-grid" style="grid-template-columns:repeat({width},minmax(70px,1fr))">'+''.join(tiles)+'</div>',unsafe_allow_html=True)
                selected=st.selectbox('Inspecter une cellule',range(len(cells)),format_func=lambda i:f'S{cells[i]["row"]+1} · P{cells[i]["col"]+1}')
                st.dataframe(pd.DataFrame([cells[selected]]),hide_index=True,width='stretch')
        if not history.empty:
            st.download_button('Exporter l’historique CSV',history.to_csv(index=False),'battery-twin-history.csv','text/csv')
        if attention and st.session_state.running:st.session_state.running=False
    render_simulation()
st.caption('Résultats exploratoires · aucune commande envoyée à un véhicule')
