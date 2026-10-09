import { useEffect, useState } from "react";
import { Upload, Download, FileCheck2, Database } from "lucide-react";
import { request } from "../api";
interface Finding {
  code: string;
  severity: string;
  title: string;
  evidence: string;
  limitation: string;
}
interface Report {
  sha256: string;
  metadata: { vehicle: string; source: string; data_kind: string };
  metrics: {
    samples: number;
    duration_s: number;
    discharge_wh: number;
    charge_wh: number;
    discharge_ah: number;
    charge_ah: number;
    max_temperature_c: number | null;
    max_cell_spread_v: number | null;
  };
  findings: Finding[];
  capabilities: Record<string, string>;
  notes: string[];
}
interface Source {
  id: string;
  title: string;
  institution: string;
  level: string;
  url: string;
  use: string;
  status: string;
  license: string;
}
const demo =
  "time_s,pack_voltage_v,pack_current_a,temperature_c,soc_pct,cell_min_v,cell_max_v\n0,400,30,30,80,3.70,3.73\n60,398,35,32,79,3.66,3.72\n120,396,40,36,78,3.59,3.73\n180,397,-10,38,78.5,3.62,3.75\n240,398,-15,39,79,3.66,3.76\n";
function download(name: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
export default function Diagnostic() {
  const [csv, setCsv] = useState(""),
    [vehicle, setVehicle] = useState(""),
    [source, setSource] = useState(""),
    [kind, setKind] = useState("measured"),
    [convention, setConvention] = useState("positive_discharge"),
    [temp, setTemp] = useState(55),
    [spread, setSpread] = useState(100),
    [report, setReport] = useState<Report | null>(null),
    [sources, setSources] = useState<Source[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [fileName, setFileName] = useState("");
  useEffect(() => {
    request<Source[]>("/diagnostics/sources")
      .then(setSources)
      .catch(() => setError("Catalogue indisponible : démarrez l’API Python."));
  }, []);
  async function analyse() {
    setBusy(true);
    setError("");
    setReport(null);
    try {
      setReport(
        await request<Report>("/diagnostics/analyse", "POST", {
          csv_text: csv,
          current_convention: convention,
          temperature_threshold_c: temp,
          cell_spread_threshold_v: spread / 1000,
          vehicle: vehicle || "Non précisé",
          source: source || fileName || "Import utilisateur",
          data_kind: kind,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analyse impossible");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="diagnostic-intro">
        <h2>Diagnostic sur données de batterie</h2>
        <p>
          Importez des mesures de véhicule, de module ou de cellule. Chaque
          constat indique ses preuves et ses limites. Le modèle NASA de
          simulation n’est pas utilisé pour interpréter ces fichiers.
        </p>
      </div>
      <div className="dashboard-grid">
        <div>
          <section className="panel">
            <div className="panel-heading">
              <h2>
                <Upload size={20} /> Importer une télémétrie
              </h2>
              <button
                className="secondary"
                onClick={() =>
                  download(
                    "battery-telemetry-template.csv",
                    "time_s,pack_voltage_v,pack_current_a,temperature_c,soc_pct,cell_min_v,cell_max_v\n",
                    "text/csv",
                  )
                }
              >
                Modèle CSV
              </button>
            </div>
            <label className="upload-zone">
              Choisir un fichier CSV
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  if (file.size > 5_000_000) {
                    setError("Fichier limité à 5 Mo.");
                    return;
                  }
                  setCsv(await file.text());
                  setFileName(file.name);
                  setKind("measured");
                  setReport(null);
                  setError("");
                }}
              />
            </label>
            <p className="caption">
              {fileName || "Aucun fichier choisi"} · CSV séparé par virgules ·
              temps en secondes · tension pack en V · courant en A.
            </p>
            <label className="text-label">
              Mesures CSV
              <textarea
                aria-label="Mesures CSV"
                value={csv}
                onChange={(e) => {
                  setCsv(e.target.value);
                  setReport(null);
                }}
                placeholder="time_s,pack_voltage_v,pack_current_a…"
                rows={7}
              />
            </label>
            <div className="form-grid">
              <label>
                Véhicule / module
                <input
                  value={vehicle}
                  placeholder="Modèle et variante si connus"
                  onChange={(e) => setVehicle(e.target.value)}
                />
              </label>
              <label>
                Source des mesures
                <input
                  value={source}
                  placeholder="DOI, fichier ou acquisition"
                  onChange={(e) => setSource(e.target.value)}
                />
              </label>
            </div>
            <label className="form-row">
              <span>Nature des données</span>
              <select value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="measured">Mesures</option>
                <option value="synthetic">Synthétiques</option>
              </select>
            </label>
            <label className="form-row">
              <span>Convention du courant</span>
              <select
                value={convention}
                onChange={(e) => setConvention(e.target.value)}
              >
                <option value="positive_discharge">Positif = décharge</option>
                <option value="negative_discharge">Négatif = décharge</option>
              </select>
            </label>
            <div className="form-grid">
              <label>
                Seuil température (°C)
                <input
                  type="number"
                  min="-20"
                  max="100"
                  value={temp}
                  onChange={(e) => setTemp(Number(e.target.value))}
                />
              </label>
              <label>
                Seuil dispersion (mV)
                <input
                  type="number"
                  min="1"
                  max="2000"
                  value={spread}
                  onChange={(e) => setSpread(Number(e.target.value))}
                />
              </label>
            </div>
            <p className="caption">
              Seuils d’analyse réglables, sans validation constructeur. Les
              colonnes optionnelles absentes rendent certains diagnostics
              indisponibles.
            </p>
            <div className="actions">
              <button
                className="primary"
                disabled={!csv || busy}
                onClick={() => void analyse()}
              >
                <FileCheck2 size={18} />
                {busy ? "Analyse en cours…" : "Analyser les mesures"}
              </button>
              <button
                className="secondary"
                disabled={busy}
                onClick={() => {
                  setCsv(demo);
                  setKind("synthetic");
                  setVehicle("Pack fictif — démonstration");
                  setSource("Scénario synthétique fourni");
                  setFileName("");
                  setReport(null);
                }}
              >
                Charger un exemple synthétique
              </button>
            </div>
          </section>
        </div>
        <div>
          <section className="panel model-note">
            <h2>Ce que l’analyse permet</h2>
            <p>
              Contrôler les unités et la chronologie, intégrer l’énergie de
              charge/décharge et identifier des dépassements de température ou
              de dispersion des tensions.
            </p>
            <h3>Ce qui exige davantage de preuves</h3>
            <p>
              Le SOH, la durée de vie restante et la localisation d’une cellule
              faible nécessitent des mesures et un protocole adaptés. Aucun
              pourcentage de santé n’est inventé à partir d’une simple trace de
              conduite.
            </p>
            <p>
              Les sources sont liées au niveau cellule, module ou véhicule. Leur
              présence au catalogue ne signifie pas qu’un modèle constructeur
              est calibré.
            </p>
          </section>
          <section className="panel model-note">
            <h2>Format attendu</h2>
            <p>
              <code>time_s, pack_voltage_v, pack_current_a</code>
            </p>
            <p>
              Optionnels :{" "}
              <code>temperature_c, soc_pct, cell_min_v, cell_max_v</code>. Les
              deux tensions cellule doivent être fournies ensemble.
            </p>
            <p>
              Maximum 20 000 lignes, 5 Mo. Les fichiers sont analysés en mémoire
              et ne sont pas enregistrés par cette API.
            </p>
          </section>
        </div>
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {report && (
        <section className="panel">
          <div className="panel-heading">
            <h2>
              <FileCheck2 size={20} /> Rapport d’analyse
            </h2>
            <button
              className="secondary"
              onClick={() =>
                download(
                  "battery-diagnostic-report.json",
                  JSON.stringify(report, null, 2),
                  "application/json",
                )
              }
            >
              <Download size={17} /> Exporter le rapport
            </button>
          </div>
          <p className="report-origin">
            {report.metadata.vehicle} ·{" "}
            {report.metadata.data_kind === "synthetic"
              ? "Données synthétiques"
              : "Mesures déclarées par l’utilisateur"}{" "}
            · {report.metrics.samples} points ·{" "}
            {(report.metrics.duration_s / 60).toFixed(2)} min
          </p>
          <div className="metrics diagnostic-metrics">
            {[
              [
                "Énergie déchargée",
                report.metrics.discharge_wh.toFixed(2),
                "Wh",
              ],
              ["Énergie chargée", report.metrics.charge_wh.toFixed(2), "Wh"],
              [
                "Charge déchargée",
                report.metrics.discharge_ah.toFixed(3),
                "Ah",
              ],
              [
                "Température max",
                report.metrics.max_temperature_c?.toFixed(2) ?? "Indisponible",
                "°C",
              ],
            ].map(([label, value, unit]) => (
              <div className="metric" key={label}>
                <div>
                  <h2>{label}</h2>
                  <strong>
                    {value}
                    <small>{unit}</small>
                  </strong>
                </div>
              </div>
            ))}
          </div>
          <div className="findings">
            {report.findings.map((f) => (
              <article key={f.code} className={`finding ${f.severity}`}>
                <h3>{f.title}</h3>
                <p>
                  <strong>Preuve : </strong>
                  {f.evidence}
                </p>
                <p>
                  <strong>Interprétation : </strong>
                  {f.limitation}
                </p>
              </article>
            ))}
          </div>
          <div className="capabilities">
            <span>SOH : preuves insuffisantes</span>
            <span>RUL : preuves insuffisantes</span>
            <span>Cellule faible : non localisée</span>
          </div>
          <p className="caption">
            Empreinte du fichier : <code>{report.sha256}</code>
          </p>
          {report.notes.map((n) => (
            <p className="caption" key={n}>
              {n}
            </p>
          ))}
        </section>
      )}
      <section className="panel">
        <div className="panel-heading">
          <h2>
            <Database size={20} /> Sources de référence
          </h2>
        </div>
        <div className="source-list">
          {sources.map((s) => (
            <article key={s.id}>
              <div>
                <h3>
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.title} ↗
                  </a>
                </h3>
                <p>
                  {s.institution} · {s.level}
                </p>
                <p>{s.use}</p>
              </div>
              <div>
                <strong>{s.status}</strong>
                <p>{s.license}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
