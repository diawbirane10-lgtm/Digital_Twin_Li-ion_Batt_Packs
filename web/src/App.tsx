import { useEffect, useRef, useState } from "react";
import {
  Battery,
  HeartPulse,
  Zap,
  Thermometer,
  LayoutDashboard,
  Grid2X2,
  ChartNoAxesCombined,
  FlaskConical,
  Download,
  Play,
  Pause,
  RotateCcw,
  ShieldCheck,
  Menu,
  Sun,
  Moon,
  PlugZap,
} from "lucide-react";
import { request, type Config, type Snapshot } from "./api";
import Chart, { metrics, type Metric } from "./components/Chart";
import Pack from "./components/Pack";
const initial: Config = { ns: 12, np: 4, temperature: 25, soc: 1 };
const pages = ["Vue d’ensemble", "Cellules", "Analyse", "Simulation"];
const icons = [LayoutDashboard, Grid2X2, ChartNoAxesCombined, FlaskConical];
function exportCSV(data: Snapshot) {
  const fields = [
    "timestamp",
    "soc",
    "soh",
    "pack_voltage",
    "current",
    "T_max",
    "soc_imbalance",
  ] as const;
  const rows = [
    fields.join(","),
    ...data.history.map((s) => fields.map((k) => s[k]).join(",")),
  ];
  const url = URL.createObjectURL(
    new Blob([rows.join("\n")], { type: "text/csv" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = "battery-twin-history.csv";
  a.click();
  URL.revokeObjectURL(url);
}
export default function App() {
  const [data, setData] = useState<Snapshot | null>(null),
    [config, setConfig] = useState(initial),
    [page, setPage] = useState(0),
    [running, setRunning] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [metric, setMetric] = useState<Metric>("soc"),
    [rate, setRate] = useState(1),
    [speed, setSpeed] = useState(10),
    [mode, setMode] = useState("discharge"),
    [dark, setDark] = useState(false),
    [menu, setMenu] = useState(false);
  const session = useRef<string | null>(null),
    inFlight = useRef(false),
    live = useRef(false);
  const s = data?.state;
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);
  async function connect() {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setRunning(false);
    live.current = false;
    setError("");
    try {
      const previous = session.current;
      const result = await request<Snapshot>("/sessions", "POST", config);
      session.current = result.session_id!;
      setData(result);
      if (previous)
        await request(`/sessions/${previous}`, "DELETE").catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connexion impossible");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  useEffect(() => {
    void connect();
    return () => {
      live.current = false;
    };
  }, []);
  async function step() {
    if (!session.current || inFlight.current) return;
    inFlight.current = true;
    try {
      const result = await request<Snapshot>(
        `/sessions/${session.current}/advance`,
        "POST",
        { seconds: speed, c_rate: rate, mode },
      );
      setData(result);
      if (result.stop_reason) {
        setRunning(false);
        live.current = false;
      }
    } catch (e) {
      setRunning(false);
      live.current = false;
      setError(e instanceof Error ? e.message : "Erreur de simulation");
    } finally {
      inFlight.current = false;
    }
  }
  useEffect(() => {
    live.current = running;
    if (!running) return;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      if (!live.current) return;
      await step();
      if (live.current) timer = setTimeout(tick, 250);
    };
    timer = setTimeout(tick, 50);
    return () => {
      live.current = false;
      clearTimeout(timer);
    };
  }, [running, speed, rate, mode]);
  const dirty =
    !!data && JSON.stringify(config) !== JSON.stringify(data.configuration);
  const controls = (
    <section className="panel controls">
      <div className="panel-heading">
        <h2>
          <FlaskConical size={20} /> Commandes de simulation
        </h2>
      </div>
      <fieldset disabled={running || busy}>
        <legend>Configuration du pack</legend>
        <div className="form-grid">
          <label>
            Série (S)
            <input
              type="number"
              min="1"
              max="24"
              value={config.ns}
              onChange={(e) =>
                setConfig({ ...config, ns: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Parallèle (P)
            <input
              type="number"
              min="1"
              max="8"
              value={config.np}
              onChange={(e) =>
                setConfig({ ...config, np: Number(e.target.value) })
              }
            />
          </label>
        </div>
        <label className="form-row">
          <span>
            <Thermometer size={17} /> Température ambiante
          </span>
          <input
            aria-label="Température ambiante"
            type="number"
            min="0"
            max="55"
            value={config.temperature}
            onChange={(e) =>
              setConfig({ ...config, temperature: Number(e.target.value) })
            }
          />
          <small>°C</small>
        </label>
        <label className="form-row">
          <span>
            <Battery size={17} /> Charge initiale
          </span>
          <input
            aria-label="Charge initiale"
            type="number"
            min="5"
            max="100"
            value={Math.round(config.soc * 100)}
            onChange={(e) =>
              setConfig({ ...config, soc: Number(e.target.value) / 100 })
            }
          />
          <small>%</small>
        </label>
      </fieldset>
      <label className="form-row">
        <span>
          <Zap size={17} /> C-rate
        </span>
        <input
          aria-label="C-rate"
          disabled={running}
          type="number"
          min="0.1"
          max="3"
          step="0.1"
          value={rate}
          onChange={(e) => setRate(Number(e.target.value))}
        />
        <small>C</small>
      </label>
      <label className="form-row">
        <span>Profil de simulation</span>
        <select
          disabled={running}
          value={mode}
          onChange={(e) => setMode(e.target.value)}
        >
          <option value="discharge">Décharge</option>
          <option value="charge">Charge</option>
        </select>
      </label>
      <label className="form-row">
        <span>Avance par pas</span>
        <select
          disabled={running}
          value={speed}
          onChange={(e) => setSpeed(Number(e.target.value))}
        >
          {[1, 10, 60, 120].map((n) => (
            <option key={n} value={n}>
              {n} s simulées
            </option>
          ))}
        </select>
      </label>
      <div className="actions">
        <button
          className="primary"
          disabled={!data || busy || dirty}
          onClick={() => setRunning(!running)}
        >
          {running ? <Pause size={17} /> : <Play size={17} />}{" "}
          {running ? "Mettre en pause" : "Démarrer la simulation"}
        </button>
        <button
          className="secondary"
          disabled={busy || running || inFlight.current}
          onClick={() => void connect()}
        >
          <RotateCcw size={16} />
          {dirty ? "Appliquer la configuration" : "Réinitialiser"}
        </button>
      </div>
      {dirty && (
        <p className="caption">Appliquez la configuration avant de démarrer.</p>
      )}
      <p className="caption">
        Courant de charge : ½ du C-rate sélectionné. Arrêt aux limites SOC et
        aux alertes BMS.
      </p>
    </section>
  );
  const protections = (
    <section className="panel">
      <div className="panel-heading">
        <h2>
          <ShieldCheck size={20} /> Protections BMS
        </h2>
      </div>
      <dl className="limits">
        <div>
          <dt>Tension cellule max</dt>
          <dd>{data?.limits.V_cell_max.toFixed(2) || "—"} V</dd>
        </div>
        <div>
          <dt>Tension cellule min</dt>
          <dd>{data?.limits.V_cell_min.toFixed(2) || "—"} V</dd>
        </div>
        <div>
          <dt>Température max</dt>
          <dd>{data?.limits.T_max || "—"} °C</dd>
        </div>
        <div>
          <dt>Charge minimale</dt>
          <dd>{data ? (data.limits.SOC_min * 100).toFixed(0) : "—"} %</dd>
        </div>
      </dl>
      <div className={`bms-status ${s?.alerts.length ? "warning" : ""}`}>
        <ShieldCheck size={23} />
        <div>
          <strong>
            {!data
              ? "En attente du moteur"
              : s?.alerts.length
                ? "Protection déclenchée"
                : "Aucune alerte active"}
          </strong>
          <p>
            {s?.alerts.join(" · ") ||
              data?.stop_reason ||
              "Surveillance du modèle de pack simulé."}
          </p>
        </div>
      </div>
    </section>
  );
  return (
    <div className="app">
      <aside className={menu ? "open" : ""}>
        <div className="brand">
          <Battery size={34} />
          <div>
            <strong>Battery Twin</strong>
            <span>Jumeau numérique de batteries</span>
          </div>
        </div>
        <nav aria-label="Navigation principale">
          {pages.map((p, i) => {
            const Icon = icons[i];
            return (
              <button
                key={p}
                className={page === i ? "active" : ""}
                onClick={() => {
                  setPage(i);
                  setMenu(false);
                }}
              >
                <Icon size={20} />
                {p}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <span>Li-ion 18650 · NASA B0005</span>
          <span>ECM 2RC · Estimation EKF</span>
          <a
            href="https://github.com/diawbirane10-lgtm/Digital_Twin_Li-ion_Batt_Packs"
            target="_blank"
            rel="noreferrer"
          >
            Birane Diaw ↗
          </a>
        </div>
      </aside>
      <main>
        <header>
          <div className="heading">
            <button
              className="icon mobile-menu"
              aria-label="Ouvrir le menu"
              aria-expanded={menu}
              onClick={() => setMenu(!menu)}
            >
              <Menu />
            </button>
            <div>
              <h1>{pages[page]}</h1>
              <p>
                Jumeau numérique <span>· Li-ion 18650</span>
              </p>
            </div>
          </div>
          <div className="header-actions">
            <span className={`connection ${error ? "offline" : ""}`}>
              <i />
              {error
                ? "API indisponible"
                : data
                  ? "API connectée"
                  : "Connexion…"}
            </span>
            <button
              className="icon"
              aria-label={
                dark ? "Activer le thème clair" : "Activer le thème sombre"
              }
              onClick={() => setDark(!dark)}
            >
              {dark ? <Sun size={19} /> : <Moon size={19} />}
            </button>
            <button
              className="secondary"
              disabled={!data?.history.length}
              onClick={() => data && exportCSV(data)}
            >
              <Download size={17} /> Exporter CSV
            </button>
          </div>
        </header>
        {error && (
          <div className="error" role="alert">
            <PlugZap size={20} />
            <span>{error}. Vérifiez que l’API Python est démarrée.</span>
            <button onClick={() => void connect()} disabled={busy}>
              Reconnecter
            </button>
          </div>
        )}
        <div className="metrics">
          {[
            {
              label: "Charge (SOC)",
              value: s ? (s.soc * 100).toFixed(1) : "—",
              unit: "%",
              Icon: Battery,
              detail: s
                ? `Incertitude σ ${(s.soc_std * 100).toFixed(2)} %`
                : "Estimation Kalman",
            },
            {
              label: "Santé (SOH)",
              value: s ? (s.soh * 100).toFixed(2) : "—",
              unit: "%",
              Icon: HeartPulse,
              detail: data?.cycle_count
                ? `${data.cycle_count} cycles de capacité disponibles`
                : "Hypothèse initiale · non mesurée",
            },
            {
              label: "Tension pack",
              value: s ? s.pack_voltage.toFixed(2) : "—",
              unit: "V",
              Icon: Zap,
              detail: data
                ? `${data.configuration.ns}S × ${data.configuration.np}P · ${data.cells.length} cellules`
                : "Topologie configurable",
            },
            {
              label: "Température max",
              value: s ? s.T_max.toFixed(2) : "—",
              unit: "°C",
              Icon: Thermometer,
              detail: s
                ? `Déséquilibre SOC ${(s.soc_imbalance * 100).toFixed(3)} %`
                : "Modèle thermique",
            },
          ].map((m) => (
            <section className="metric" key={m.label}>
              <div className="metric-icon">
                <m.Icon size={23} />
              </div>
              <div>
                <h2>{m.label}</h2>
                <strong>
                  {m.value}
                  <small>{m.unit}</small>
                </strong>
                <p>{m.detail}</p>
              </div>
            </section>
          ))}
        </div>
        {page === 0 && (
          <div className="dashboard-grid">
            <div>
              <section className="panel">
                <div className="panel-heading">
                  <h2>
                    <ChartNoAxesCombined size={20} /> Évolution de la charge
                  </h2>
                  <select
                    aria-label="Grandeur du graphique"
                    value={metric}
                    onChange={(e) => setMetric(e.target.value as Metric)}
                  >
                    {Object.entries(metrics).map(([key, v]) => (
                      <option key={key} value={key}>
                        {v.label} ({v.unit})
                      </option>
                    ))}
                  </select>
                </div>
                <Chart history={data?.history || []} metric={metric} />
                <div className="chart-footer">
                  <span>
                    <i />{" "}
                    {running ? "Simulation en cours" : "Simulation en pause"}
                  </span>
                  <strong>
                    {((s?.timestamp || 0) / 60).toFixed(2)} min simulées
                  </strong>
                </div>
              </section>
              <Pack data={data} />
            </div>
            <div>
              {controls}
              {protections}
            </div>
          </div>
        )}
        {page === 1 && (
          <>
            <Pack data={data} />
            <section className="panel">
              <div className="panel-heading">
                <h2>État individuel des cellules</h2>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      {[
                        "Cellule",
                        "Charge (%)",
                        "Tension (V)",
                        "Température (°C)",
                        "Courant (A)",
                      ].map((v) => (
                        <th key={v}>{v}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data?.cells.map((c) => (
                      <tr key={c.id}>
                        <td>
                          S{c.row + 1} · P{c.col + 1}
                        </td>
                        <td>{(c.soc * 100).toFixed(2)}</td>
                        <td>{c.voltage.toFixed(3)}</td>
                        <td>{c.temperature.toFixed(2)}</td>
                        <td>{c.current.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
        {page === 2 && (
          <>
            <div className="analysis-grid">
              {(Object.keys(metrics) as Metric[]).map((m) => (
                <section className="panel" key={m}>
                  <div className="panel-heading">
                    <h2>
                      {metrics[m].label} ({metrics[m].unit})
                    </h2>
                  </div>
                  <Chart history={data?.history || []} metric={m} />
                </section>
              ))}
            </div>
            <section className="panel model-note">
              <h2>Interpréter les résultats</h2>
              <p>
                Le SOC est estimé par filtre de Kalman étendu. Le SOH reste à sa
                valeur initiale dans ce scénario : le modèle de cellule ne
                simule pas encore le vieillissement. Il doit être alimenté par
                des capacités mesurées pour suivre une dégradation réelle. Les
                mesures de cette interface proviennent du modèle physique :
                elles ne constituent pas une validation expérimentale
                indépendante.
              </p>
              <p>
                L’export contient les points affichés, échantillonnés à environ
                600 points. La température et le vieillissement restent des
                modèles simplifiés.
              </p>
            </section>
          </>
        )}
        {page === 3 && (
          <div className="dashboard-grid">
            <div>
              {controls}
              <section className="panel model-note">
                <h2>Un banc virtuel pour explorer un pack</h2>
                <p>
                  Comparez l’effet de la topologie, de la température ambiante
                  et du courant sur la charge, la tension et les différences
                  entre cellules.
                </p>
                <h3>Applications possibles</h3>
                <p>
                  Étude préliminaire de petits packs de mobilité électrique,
                  démonstration pédagogique d’un BMS et exploration de modules
                  de stockage stationnaire.
                </p>
                <h3>Périmètre du modèle</h3>
                <p>
                  Paramètres identifiés sur la cellule NASA B0005. Ce modèle
                  n’est pas qualifié pour dimensionner une batterie automobile
                  ou ferroviaire réelle. Les écarts entre cellules sont simulés.
                </p>
              </section>
            </div>
            <div>
              {protections}
              <section className="panel model-note">
                <h2>État de la session</h2>
                <p>
                  {data
                    ? `${data.configuration.ns}S × ${data.configuration.np}P · ${data.cells.length} cellules`
                    : "Aucune session connectée"}
                </p>
                <p>Temps simulé : {s?.timestamp.toFixed(0) || 0} s</p>
                <p>
                  Puissance électrique :{" "}
                  {s ? (s.pack_voltage * s.current).toFixed(1) : "—"} W
                </p>
                <p>
                  Durée de vie restante : {s?.rul_cycles ?? "Non estimée"}{" "}
                  {s?.rul_cycles != null ? "cycles" : ""}
                </p>
                <p>
                  Chaque session dispose de son propre moteur. Elle expire après
                  une heure d’inactivité.
                </p>
              </section>
            </div>
          </div>
        )}
        <footer>
          Battery Twin <span>·</span> Simulation physique & estimation d’état{" "}
          <span>·</span> Résultats exploratoires
        </footer>
      </main>
    </div>
  );
}
