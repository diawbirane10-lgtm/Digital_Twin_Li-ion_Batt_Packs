"""
Dashboard Streamlit — Digital Twin Li-ion Battery Pack
Version simplifiée : EKF + SOH + Pack physique, vue 3D intégrée

Lancer : streamlit run visualization/dashboard/app.py
"""

import json
import time
import sys
from io import StringIO
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Trouve la racine du repo (contient ml/models/ecm_b0005.json)
# Fonctionne que app.py soit à la racine (Streamlit Cloud) ou dans visualization/dashboard/ (local)
ROOT = Path(__file__).resolve().parent
for _ in range(4):
    if (ROOT / "ml" / "models" / "ecm_b0005.json").exists():
        break
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from digital_twin.core.twin_engine import BatteryDigitalTwin

# ── Config page ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Battery Digital Twin",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
header[data-testid="stHeader"],
div[data-testid="stToolbar"],
#MainMenu, footer { display: none !important; }

.main { background-color: #080c18; }
.block-container { padding-top: 0.8rem; padding-bottom: 0.4rem; }

div[data-testid="metric-container"] {
  background: linear-gradient(135deg, #131b2e 0%, #0d1220 100%);
  border: 1px solid #1e2d4d;
  border-radius: 12px;
  padding: 12px 16px;
  box-shadow: 0 2px 10px rgba(0,212,170,0.05);
}
.chrono-box {
  background: linear-gradient(135deg,#00120e,#001a14);
  border: 1.5px solid #00d4aa;
  border-radius: 14px;
  padding: 8px 14px;
  text-align: center;
  font-family: 'Courier New', monospace;
  color: #00d4aa;
  font-weight: bold;
}
.chrono-time  { font-size: 1.75rem; line-height: 1.1; }
.chrono-label { font-size: 0.72rem; color: #7bc4b0; margin-top: 2px; }
.alert-critical {
  background: #1f0505; border: 1px solid #cc3333;
  border-radius: 8px; padding: 7px 13px; color: #ff7070; margin: 3px 0;
}
.alert-warning {
  background: #1f1005; border: 1px solid #cc7700;
  border-radius: 8px; padding: 7px 13px; color: #ffaa44; margin: 3px 0;
}
.status-ok {
  background: #031410; border: 1px solid #00d4aa55;
  border-radius: 8px; padding: 7px 13px; color: #00d4aa; margin: 3px 0;
}
h1 { color: #00d4aa !important; margin-bottom: 0 !important; }
h2, h3 { color: #6e93d6 !important; }
.stTabs [data-baseweb="tab"] { color: #8899bb !important; font-size: .9rem; }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  color: #00d4aa !important;
  border-bottom: 2px solid #00d4aa !important;
}
[data-testid="stSidebar"] { background: #0c1220; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h4 { color: #00d4aa !important; }
</style>
""", unsafe_allow_html=True)


# ── ECM ───────────────────────────────────────────────────────────────────────
@st.cache_resource
def load_ecm() -> dict:
    with open(ROOT / "ml" / "models" / "ecm_b0005.json") as f:
        return json.load(f)

ecm = load_ecm()


def build_twin(ns: int, np_: int, T_init: float = 25.0) -> BatteryDigitalTwin:
    twin = BatteryDigitalTwin(ecm_params=ecm, pack_ns=ns, pack_np=np_)
    twin.pack.set_temperature(T_init)
    return twin


# ── Helpers physiques ─────────────────────────────────────────────────────────
def capacity_factor(T_C: float) -> float:
    if T_C >= 25.0:
        return min(1.02, 1.0 + 0.0005 * (T_C - 25.0))
    return max(0.40, 1.0 - 0.008 * (25.0 - T_C))


def cycle_life_estimate(T_C: float, C_rate: float) -> int:
    af = float(np.exp(6000.0 * (1.0 / 298.15 - 1.0 / (T_C + 273.15))))
    return max(50, int(800.0 / af / max(0.1, C_rate) ** 0.45))


# ── Session state ─────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "twin":      lambda: build_twin(12, 4, 25.0),
        "run":       False,
        "sim_t":     0.0,
        "n_cycles":  0,
        "cycle_dir": "discharge",
        "last_ns":   12,
        "last_np":   4,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v() if callable(v) else v

_init_state()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Paramètres")

    # Topologie
    st.markdown("#### 🔋 Topologie du pack")
    c_ns, c_np = st.columns(2)
    with c_ns:
        ns  = st.selectbox("Série Ns",      [4, 6, 8, 12, 16, 24], index=3)
    with c_np:
        np_ = st.selectbox("Parallèle Np",  [1, 2, 3, 4, 6, 8],   index=3)

    Q_nom = ecm["Q_nom_Ah"]
    V_nom = ns * 3.6
    E_nom = ns * np_ * Q_nom * 3.6
    st.caption(f"{ns * np_} cellules · **{V_nom:.0f} V** · **{E_nom:.1f} Wh** nominaux")

    st.markdown("---")

    # Température
    st.markdown("#### 🌡️ Température ambiante")
    T_amb = st.slider("T ambiante (°C)", min_value=0, max_value=55,
                      value=25, step=1)
    cap_f  = capacity_factor(T_amb)
    cl_est = cycle_life_estimate(T_amb, 1.0)
    st.caption(
        f"Capacité dispo : **{cap_f * 100:.0f}%**  |  "
        f"Durée de vie estimée : **~{cl_est} cycles**"
    )

    st.markdown("---")

    # Profil courant
    st.markdown("#### ⚡ Profil de courant")
    C_rate = st.slider("C-rate", min_value=0.1, max_value=3.0, value=1.0, step=0.1)
    mode   = st.radio("Mode", ["Décharge", "Charge", "Cycle auto"], horizontal=True)

    speed_opts  = {"1×": 1, "10×": 10, "60×": 60, "600×": 600}
    speed_label = st.select_slider("Vitesse de simulation",
                                   options=list(speed_opts.keys()), value="10×")
    speed_mult  = speed_opts[speed_label]
    sim_per_s   = speed_mult  # secondes simulées par seconde réelle
    st.caption(f"1 s réel ≈ **{speed_mult} s** simulés")

    st.markdown("---")

    # Contrôles
    c_r, c_rst = st.columns(2)
    with c_r:
        run_toggle = st.toggle("▶ Run", value=st.session_state.run, key="run_tog")
    with c_rst:
        reset_btn = st.button("🔄 Reset", use_container_width=True)

    st.markdown("---")

    # Export CSV
    st.markdown("#### 💾 Export CSV")
    df_hist_export = st.session_state.twin.history_df()
    if not df_hist_export.empty:
        cols_export = [c for c in
                       ["timestamp", "soc", "soh", "voltage", "current",
                        "temperature", "pack_voltage", "V_cell_min",
                        "V_cell_max", "T_max", "soc_imbalance"]
                       if c in df_hist_export.columns]
        df_out = df_hist_export[cols_export].copy()
        df_out.insert(0, "power_W",
                      df_out["pack_voltage"] * df_out["current"])

        buf = StringIO()
        buf.write(f"# Digital Twin Li-ion — Export simulation\n")
        buf.write(f"# Ns={ns}  Np={np_}  T_amb={T_amb}°C  C_rate={C_rate}  mode={mode}\n")
        buf.write(f"# Cellules={ns*np_}  V_nom={V_nom:.1f}V  E_nom={E_nom:.1f}Wh\n")
        buf.write(f"# Cycles complétés={st.session_state.n_cycles}\n")
        buf.write(f"# Q_nom_Ah={Q_nom}  R0={ecm['R0_ohm']}  R1={ecm['R1_ohm']}\n")
        buf.write("#\n")
        df_out.to_csv(buf, index=False)

        st.download_button(
            label="📥 Télécharger l'historique",
            data=buf.getvalue(),
            file_name="battery_twin_export.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.button("📥 Télécharger (aucune donnée)", disabled=True,
                  use_container_width=True)

    st.markdown("---")
    st.caption("🔬 ECM 2RC · EKF · SOH physique · NASA B0005")


# ── Rebuild twin si topologie change ─────────────────────────────────────────
topo_changed = (ns != st.session_state.last_ns or np_ != st.session_state.last_np)
if topo_changed or reset_btn:
    st.session_state.twin      = build_twin(ns, np_, float(T_amb))
    st.session_state.sim_t     = 0.0
    st.session_state.n_cycles  = 0
    st.session_state.cycle_dir = "discharge"
    st.session_state.last_ns   = ns
    st.session_state.last_np   = np_
    st.rerun()

st.session_state.run = run_toggle
twin = st.session_state.twin


# ── Header ────────────────────────────────────────────────────────────────────
col_h, col_t = st.columns([5, 1])
with col_h:
    dot = "🟢" if st.session_state.run else "⚫"
    st.markdown(
        f'<h1>{dot} Digital Twin — Pack Li-ion {ns}S×{np_}P</h1>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"{ns * np_} cellules 18650 NMC · {V_nom:.0f} V · {E_nom:.1f} Wh · "
        f"T ambiante : **{T_amb}°C** · "
        f"Capacité disponible : **{cap_f*100:.0f}%** · "
        f"Cycles terminés : **{st.session_state.n_cycles}**"
    )
with col_t:
    ss = int(st.session_state.sim_t)
    st.markdown(
        f'<div class="chrono-box">'
        f'<div class="chrono-time">⏱ {ss//3600:02d}:{(ss%3600)//60:02d}:{ss%60:02d}</div>'
        f'<div class="chrono-label">Temps simulé · {speed_label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Placeholders (mis à jour à chaque rerun) ──────────────────────────────────
ph_metrics = st.empty()
ph_alerts  = st.empty()
ph_tabs    = st.empty()


# ── Plotly helpers ─────────────────────────────────────────────────────────────
_L = dict(
    template="plotly_dark",
    paper_bgcolor="#080c18",
    plot_bgcolor="#0f1525",
    font=dict(color="#9aaecf", family="Inter,Arial,sans-serif"),
    margin=dict(l=44, r=16, t=44, b=36),
)
_G = dict(gridcolor="#1e2d4d", showgrid=True)


def _ln(color, width=2, dash=None):
    d = dict(color=color, width=width)
    if dash:
        d["dash"] = dash
    return d


# ── 3D pack visualization (Plotly, in-browser) ────────────────────────────────
def make_3d_pack(twin_ref: BatteryDigitalTwin, metric: str = "soc") -> go.Figure:
    cells = twin_ref.pack.cells
    _ns, _np = twin_ref.pack.ns, twin_ref.pack.np_

    xs, ys, zs, colors, texts = [], [], [], [], []
    cscale = {"soc": "RdYlGn", "temp": "thermal", "voltage": "Viridis"}[metric]
    cbar   = {"soc": "SOC (%)", "temp": "T (°C)", "voltage": "V (V)"}[metric]
    zrange = {"soc": (0, 100), "temp": (0, 65), "voltage": (2.5, 4.3)}[metric]

    for i, cell in enumerate(cells):
        row = i // _np   # série
        col = i % _np    # parallèle
        xs.append(col)
        ys.append(row)
        val = {"soc": cell.state.soc * 100,
               "temp": cell.state.temp,
               "voltage": cell.state.voltage}[metric]
        zs.append(val)
        colors.append(val)
        texts.append(
            f"<b>S{row+1}–P{col+1}</b><br>"
            f"SOC : {cell.state.soc*100:.1f}%<br>"
            f"T   : {cell.state.temp:.1f}°C<br>"
            f"V   : {cell.state.voltage:.3f} V"
        )

    fig = go.Figure()

    # Tiges verticales (effet barre 3D)
    for x, y, z in zip(xs, ys, zs):
        fig.add_trace(go.Scatter3d(
            x=[x, x], y=[y, y], z=[0, z],
            mode="lines",
            line=dict(color="rgba(130,150,190,0.3)", width=3),
            showlegend=False, hoverinfo="skip",
        ))

    # Marqueurs cellules
    fig.add_trace(go.Scatter3d(
        x=xs, y=ys, z=zs,
        mode="markers",
        marker=dict(
            size=11 if _ns * _np > 24 else 14,
            color=colors,
            colorscale=cscale,
            cmin=zrange[0], cmax=zrange[1],
            showscale=True,
            colorbar=dict(title=cbar, thickness=14, len=0.65, x=1.0),
            symbol="square",
            opacity=0.92,
            line=dict(color="rgba(200,220,255,0.25)", width=1),
        ),
        text=texts,
        hoverinfo="text",
        name="Cellules",
    ))

    # Plan de base
    fig.add_trace(go.Scatter3d(
        x=[i % _np for i in range(_ns * _np)],
        y=[i // _np for i in range(_ns * _np)],
        z=[0] * (_ns * _np),
        mode="markers",
        marker=dict(size=3, color="rgba(80,100,140,0.35)"),
        showlegend=False, hoverinfo="skip",
    ))

    ratio_x = max(0.5, _np / max(_ns, _np))
    ratio_y = max(0.5, _ns / max(_ns, _np))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title=f"Parallèle (1→{_np})",
                       gridcolor="#1e2d4d", backgroundcolor="#0d1220",
                       showbackground=True),
            yaxis=dict(title=f"Série (1→{_ns})",
                       gridcolor="#1e2d4d", backgroundcolor="#0d1220",
                       showbackground=True),
            zaxis=dict(title=cbar,
                       gridcolor="#1e2d4d", backgroundcolor="#0d1220",
                       showbackground=True, range=list(zrange)),
            bgcolor="#080c18",
            camera=dict(eye=dict(x=1.5, y=-1.6, z=1.1)),
            aspectmode="manual",
            aspectratio=dict(x=ratio_x, y=ratio_y, z=0.65),
        ),
        paper_bgcolor="#080c18",
        font=dict(color="#9aaecf"),
        margin=dict(l=0, r=0, t=30, b=0),
        height=480,
        showlegend=False,
    )
    return fig


# ── Render frame ──────────────────────────────────────────────────────────────
def render_frame():
    state   = twin.state
    history = twin.history_df()

    # Métriques
    with ph_metrics.container():
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("⚡ SOC", f"{state.soc * 100:.1f}%",
                  delta=f"σ = {state.soc_std * 100:.2f}%", delta_color="off")
        c2.metric("🏥 SOH", f"{state.soh * 100:.2f}%",
                  delta=f"{st.session_state.n_cycles} cycles terminés")
        c3.metric("🌡️ T cellule", f"{state.T_max:.1f}°C",
                  delta=f"Cap : {cap_f * 100:.0f}%", delta_color="off")
        c4.metric("🔌 V pack", f"{state.pack_voltage:.2f} V",
                  delta=f"cell : {state.V_cell_min:.3f}–{state.V_cell_max:.3f} V",
                  delta_color="off")
        P_kW = abs(state.pack_voltage * state.current) / 1000.0
        c5.metric("⚡ Puissance", f"{P_kW:.3f} kW",
                  delta=f"{C_rate:.1f}C", delta_color="off")
        c6.metric("⚖️ Déséquilibre", f"{state.soc_imbalance * 100:.3f}%",
                  delta="OK" if state.soc_imbalance < 0.05 else "élevé",
                  delta_color="normal" if state.soc_imbalance < 0.05 else "inverse")

    # Alertes BMS
    with ph_alerts.container():
        if state.alerts:
            for a in state.alerts:
                cls = ("alert-critical"
                       if any(x in a for x in ("OVP", "UVP", "SOC"))
                       else "alert-warning")
                st.markdown(f'<div class="{cls}">⚠️ {a}</div>',
                            unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="status-ok">✅ BMS — Tous paramètres nominaux</div>',
                unsafe_allow_html=True,
            )

    # Onglets
    with ph_tabs.container():
        tab1, tab2, tab3 = st.tabs([
            "📊 Temps réel",
            "🔋 Vue 3D du pack",
            "📈 Dégradation & cycles",
        ])

        # ── Tab 1 : Historique temps réel ──────────────────────────────────
        with tab1:
            if len(history) > 1:
                t_min = history["timestamp"] / 60.0
                fig = make_subplots(2, 2,
                    subplot_titles=("SOC (%)", "Tension pack (V)",
                                    "Température cellule (°C)", "Courant (A)"),
                    vertical_spacing=0.20, horizontal_spacing=0.10)

                # SOC
                fig.add_trace(go.Scatter(
                    x=t_min, y=history["soc"] * 100,
                    line=_ln("#00d4aa"), fill="tozeroy",
                    fillcolor="rgba(0,212,170,0.07)", name="SOC EKF",
                ), row=1, col=1)
                fig.add_hline(y=20, line_dash="dot", line_color="#ff4444",
                              annotation_text="SOC min 20%",
                              annotation_font_size=9, row=1, col=1)

                # Tension
                fig.add_trace(go.Scatter(
                    x=t_min, y=history["pack_voltage"],
                    line=_ln("#7b9de0"), name="V pack",
                ), row=1, col=2)
                if "V_cell_min" in history.columns:
                    fig.add_trace(go.Scatter(
                        x=t_min, y=history["V_cell_min"],
                        line=_ln("#ff6b6b", 1.2, "dot"), name="V min",
                    ), row=1, col=2)
                    fig.add_trace(go.Scatter(
                        x=t_min, y=history["V_cell_max"],
                        line=_ln("#55efc4", 1.2, "dot"), name="V max",
                    ), row=1, col=2)

                # Température
                fig.add_trace(go.Scatter(
                    x=t_min, y=history["T_max"],
                    line=_ln("#ff9f43"), fill="tozeroy",
                    fillcolor="rgba(255,159,67,0.07)", name="T max",
                ), row=2, col=1)
                fig.add_hline(y=55, line_dash="dot", line_color="#ff4444",
                              annotation_text="OTP 55°C",
                              annotation_font_size=9, row=2, col=1)
                fig.add_hline(y=T_amb, line_dash="dash", line_color="#888",
                              annotation_text=f"T amb {T_amb}°C",
                              annotation_font_size=9, row=2, col=1)

                # Courant
                fig.add_trace(go.Scatter(
                    x=t_min, y=history["current"],
                    line=_ln("#a29bfe"), fill="tozeroy",
                    fillcolor="rgba(162,155,254,0.06)", name="I (A)",
                ), row=2, col=2)
                fig.add_hline(y=0, line_dash="dot", line_color="#555",
                              row=2, col=2)

                fig.update_layout(**_L, height=440, showlegend=False)
                for r in [1, 2]:
                    for c in [1, 2]:
                        fig.update_xaxes(**_G, title_text="t (min)", row=r, col=c)
                        fig.update_yaxes(**_G, row=r, col=c)
                st.plotly_chart(fig, use_container_width=True)

                # SOC progress bar
                soc_pct = int(state.soc * 100)
                bar_color = "#00d4aa" if soc_pct > 30 else ("#ffd700" if soc_pct > 15 else "#ff4444")
                st.markdown(
                    f"<div style='background:#1a2540;border-radius:8px;height:18px;'>"
                    f"<div style='background:{bar_color};width:{soc_pct}%;height:100%;"
                    f"border-radius:8px;transition:width 0.3s;'></div></div>"
                    f"<p style='color:#9aaecf;font-size:0.8rem;margin:2px 0 0 4px;'>"
                    f"SOC : {soc_pct}%</p>",
                    unsafe_allow_html=True,
                )
            else:
                st.info("▶ Activez **Run** dans la barre latérale pour démarrer la simulation.")

        # ── Tab 2 : Vue 3D du pack ─────────────────────────────────────────
        with tab2:
            st.markdown(
                f"##### Topologie {ns}S×{np_}P — {ns * np_} cellules 18650 NMC"
            )
            col_3d, col_opt = st.columns([4, 1])
            with col_opt:
                metric_3d = st.radio(
                    "Variable",
                    ["soc", "temp", "voltage"],
                    format_func=lambda x: {
                        "soc":     "SOC (%)",
                        "temp":    "Température (°C)",
                        "voltage": "Tension (V)",
                    }[x],
                    key="metric_3d_radio",
                )
                st.markdown("---")
                st.caption(
                    "**Navigation 3D**\n"
                    "- Clic gauche : rotation\n"
                    "- Scroll : zoom\n"
                    "- Clic droit : déplacement\n"
                    "- Survol cellule : détails"
                )
            with col_3d:
                st.plotly_chart(
                    make_3d_pack(twin, metric_3d),
                    use_container_width=True,
                )

            # Heatmaps 2D (vue du dessus)
            _ns, _np = twin.pack.ns, twin.pack.np_
            socs_g  = np.array([c.state.soc     for c in twin.pack.cells]).reshape(_ns, _np)
            temps_g = np.array([c.state.temp    for c in twin.pack.cells]).reshape(_ns, _np)
            volts_g = np.array([c.state.voltage for c in twin.pack.cells]).reshape(_ns, _np)

            fig_hm = make_subplots(1, 3,
                subplot_titles=("SOC (%)", "Température (°C)", "Tension (V)"),
                horizontal_spacing=0.08)
            for ci, (data, cs, zr) in enumerate([
                (socs_g * 100, "RdYlGn", (0, 100)),
                (temps_g,      "thermal", (max(T_amb - 5, 0), min(T_amb + 25, 65))),
                (volts_g,      "Viridis", (2.5, 4.25)),
            ], 1):
                fig_hm.add_trace(go.Heatmap(
                    z=data, colorscale=cs, zmin=zr[0], zmax=zr[1],
                    text=[[f"{v:.2f}" for v in row] for row in data],
                    texttemplate="%{text}",
                    textfont=dict(size=8 if _ns * _np > 24 else 10, color="white"),
                    showscale=True,
                ), row=1, col=ci)
            fig_hm.update_layout(**_L, height=280,
                xaxis_title="Parallèle", yaxis_title="Série")
            st.plotly_chart(fig_hm, use_container_width=True)

        # ── Tab 3 : Dégradation SOH ────────────────────────────────────────
        with tab3:
            st.markdown("##### Dégradation SOH & durée de vie")

            cl_cur = cycle_life_estimate(T_amb, C_rate)
            cl_ref = cycle_life_estimate(25.0, 1.0)
            c1, c2, c3 = st.columns(3)
            c1.metric("RUL estimé", f"~{cl_cur} cycles",
                      delta=f"réf 25°C 1C : ~{cl_ref}",
                      delta_color="inverse" if cl_cur < cl_ref * 0.8 else "normal")
            c2.metric("SOH actuel", f"{twin.soh_est.soh * 100:.2f}%",
                      delta=f"{st.session_state.n_cycles} cycles")
            c3.metric("Q restante", f"{twin.soh_est.soh * Q_nom:.3f} Ah",
                      delta=f"vs {Q_nom:.3f} Ah neuf")

            soh_hist = list(twin.soh_est.soh_history)

            if len(soh_hist) > 1:
                fig_soh = go.Figure()
                cx = list(range(1, len(soh_hist) + 1))
                fig_soh.add_trace(go.Scatter(
                    x=cx, y=[s * 100 for s in soh_hist],
                    line=_ln("#00d4aa", 2), mode="lines+markers",
                    marker=dict(size=5), name="SOH mesuré",
                ))
                # Extrapolation linéaire vers EOL
                if len(soh_hist) >= 3:
                    z_fit = np.polyfit(cx, [s * 100 for s in soh_hist], 1)
                    if z_fit[0] < 0:
                        n_eol = max(len(soh_hist) + 1,
                                    int((80.0 - z_fit[1]) / z_fit[0]))
                        x_ext = list(range(len(soh_hist),
                                           min(n_eol + 20, len(soh_hist) + 1000)))
                        y_ext = [np.clip(np.polyval(z_fit, x), 0, 100) for x in x_ext]
                        fig_soh.add_trace(go.Scatter(
                            x=x_ext, y=y_ext,
                            line=_ln("#ffd700", 1.5, "dot"),
                            name=f"Projection (EOL ≈ cycle {n_eol})",
                        ))
                        fig_soh.add_vline(x=n_eol, line_dash="dash",
                                          line_color="#ff4444",
                                          annotation_text=f"EOL ~{n_eol}",
                                          annotation_font_size=10)
                fig_soh.add_hline(y=80, line_dash="dot", line_color="#ff4444",
                                  annotation_text="EOL 80% SOH")
                fig_soh.update_layout(**_L, height=320,
                    title="Évolution SOH par cycle",
                    xaxis=dict(title="Cycle #", **_G),
                    yaxis=dict(title="SOH (%)", range=[60, 101], **_G),
                    legend=dict(bgcolor="#0f1525", bordercolor="#1e2d4d"))
                st.plotly_chart(fig_soh, use_container_width=True)
            else:
                # Projection théorique basée sur les paramètres courants
                cyc_th  = np.arange(0, cl_cur + 50)
                soh_th  = np.clip(100.0 - cyc_th * (20.0 / cl_cur), 0, 100)
                fig_th  = go.Figure()
                fig_th.add_trace(go.Scatter(
                    x=cyc_th, y=soh_th,
                    line=_ln("#00d4aa", 2), fill="tozeroy",
                    fillcolor="rgba(0,212,170,0.06)",
                    name="Projection théorique",
                ))
                fig_th.add_hline(y=80, line_dash="dot", line_color="#ff4444",
                                 annotation_text="EOL 80%")
                fig_th.update_layout(**_L, height=320,
                    title=(f"Projection théorique — T={T_amb}°C, {C_rate:.1f}C "
                           f"→ ~{cl_cur} cycles jusqu'à EOL"),
                    xaxis=dict(title="Cycle #", **_G),
                    yaxis=dict(title="SOH (%)", **_G))
                st.plotly_chart(fig_th, use_container_width=True)
                st.info(
                    "Utilisez le mode **Cycle auto** + **▶ Run** pour "
                    "observer la dégradation réelle cycle par cycle."
                )


# ── Boucle de simulation ──────────────────────────────────────────────────────
if st.session_state.run:
    Q_eff = Q_nom * cap_f * np_        # Ah effectif (corrigé T)
    I_mag = Q_eff * C_rate              # A (amplitude)

    if mode == "Décharge":
        I = -I_mag
    elif mode == "Charge":
        I = +I_mag * 0.5
    else:  # Cycle auto
        soc_now = twin.state.soc
        if st.session_state.cycle_dir == "discharge" and soc_now <= 0.08:
            # Fin de décharge → enregistrer cycle → recharger
            twin.end_cycle(measured_capacity_Ah=Q_eff / max(1, np_) * 0.97)
            st.session_state.n_cycles += 1
            twin.reset(soc0=0.08)
            twin.pack.set_temperature(float(T_amb))
            st.session_state.cycle_dir = "charge"
        elif st.session_state.cycle_dir == "charge" and soc_now >= 0.95:
            st.session_state.cycle_dir = "discharge"
        I = -I_mag if st.session_state.cycle_dir == "discharge" else +I_mag * 0.5

    for _ in range(speed_mult):
        V_meas = twin.pack.pack_voltage + np.random.normal(0, 0.004)
        state  = twin.update(V_meas, I, float(T_amb), dt=1.0)
        st.session_state.sim_t += 1.0

        # Fin de décharge en mode Décharge / Charge simple
        if mode != "Cycle auto" and state.soc < 0.05 and I < 0:
            twin.end_cycle(measured_capacity_Ah=Q_eff / max(1, np_) * 0.97)
            st.session_state.n_cycles += 1
            twin.reset(soc0=1.0)
            twin.pack.set_temperature(float(T_amb))
            break

    render_frame()
    time.sleep(0.05)
    st.rerun()

else:
    render_frame()
    if not st.session_state.run:
        st.info(
            "▶ Activez **Run** dans la barre latérale pour démarrer la simulation. "
            "Réglez la topologie, la température et le C-rate, puis observez l'évolution en temps réel."
        )

