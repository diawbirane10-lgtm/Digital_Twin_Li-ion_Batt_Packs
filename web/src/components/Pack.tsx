import { useState } from "react";
import type { Snapshot, Cell } from "../api";
export default function Pack({ data }: { data: Snapshot | null }) {
  const [metric, setMetric] = useState<"soc" | "temperature" | "voltage">(
    "soc",
  );
  const [selected, setSelected] = useState(0);
  const cell = data?.cells.find((c) => c.id === selected);
  const value = (c: Cell) => (metric === "soc" ? c.soc * 100 : c[metric]);
  const ns = data?.configuration.ns || 12,
    np = data?.configuration.np || 4;
  return (
    <section className="panel pack-panel">
      <div className="panel-heading">
        <h2>
          Carte du pack{" "}
          <span>
            ({ns}S × {np}P)
          </span>
        </h2>
        <select
          aria-label="Grandeur des cellules"
          value={metric}
          onChange={(e) => setMetric(e.target.value as typeof metric)}
        >
          <option value="soc">Charge (%)</option>
          <option value="temperature">Température (°C)</option>
          <option value="voltage">Tension (V)</option>
        </select>
      </div>
      {!data ? (
        <div className="empty">
          Connectez le moteur pour consulter les cellules.
        </div>
      ) : (
        <>
          <div
            className="cell-grid"
            style={{
              gridTemplateColumns: `repeat(${Math.min(ns, 12)}, minmax(46px,1fr))`,
            }}
          >
            {data.cells
              .slice()
              .sort((a, b) => a.col - b.col || a.row - b.row)
              .map((c) => {
                const abnormal = c.temperature > 55 || c.voltage > 4.25 || c.voltage < 2.45;
                return (
                  <button
                    key={c.id}
                    className={`cell ${selected === c.id ? "selected" : ""} ${abnormal ? "abnormal" : ""}`}
                    onClick={() => setSelected(c.id)}
                    aria-label={`Cellule S${c.row + 1} P${c.col + 1}, ${value(c).toFixed(2)}`}
                  >
                    <span>
                      S{c.row + 1}·P{c.col + 1}
                    </span>
                    <strong>
                      {abnormal ? "⚠ " : ""}{value(c).toFixed(metric === "voltage" ? 2 : 1)}
                    </strong>
                  </button>
                );
              })}
          </div>
          <div className="cell-detail">
            <strong>
              Cellule S{(cell?.row || 0) + 1} · P{(cell?.col || 0) + 1}
            </strong>
            <span>{((cell?.soc || 0) * 100).toFixed(1)} %</span>
            <span>{cell?.voltage.toFixed(3)} V</span>
            <span>{cell?.temperature.toFixed(2)} °C</span>
            <span>{cell?.current.toFixed(2)} A</span>
          </div>
          <p className="caption">
            {data.cells.length} cellules simulées · Cliquez sur une cellule pour
            l’inspecter.
          </p>
        </>
      )}
    </section>
  );
}
