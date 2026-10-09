import { useState, useEffect, useRef } from "react";
import type { State } from "../api";
export type Metric = "soc" | "pack_voltage" | "T_max" | "current";
export const metrics: Record<
  Metric,
  { label: string; unit: string; color: string }
> = {
  soc: { label: "Charge estimée", unit: "%", color: "#0d9488" },
  pack_voltage: { label: "Tension pack", unit: "V", color: "#5472dc" },
  T_max: { label: "Température maximale", unit: "°C", color: "#e59135" },
  current: { label: "Courant pack", unit: "A", color: "#9470ce" },
};
export default function Chart({
  history,
  metric,
}: {
  history: State[];
  metric: Metric;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const container = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(740);
  useEffect(() => {
    const observer = new ResizeObserver((entries) =>
      setWidth(Math.max(260, entries[0].contentRect.width)),
    );
    if (container.current) observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  const plotWidth = width - 90;
  const meta = metrics[metric];
  const value = (s: State) => s[metric] * (metric === "soc" ? 100 : 1);
  const values = history.map(value);
  let low = metric === "soc" ? 0 : Math.min(...values, 0),
    high = metric === "soc" ? 100 : Math.max(...values, 1);
  if (metric !== "soc" && values.length) {
    low = Math.min(...values);
    high = Math.max(...values);
    const margin = Math.max((high - low) * 0.15, 0.1);
    low -= margin;
    high += margin;
  }
  const firstTime = history[0]?.timestamp || 0;
  const lastTime = history.at(-1)?.timestamp || 0;
  const x = (i: number) =>
    52 +
    (((history[i]?.timestamp || 0) - firstTime) /
      Math.max(1, lastTime - firstTime)) *
      plotWidth;
  const y = (v: number) => 245 - ((v - low) / (high - low)) * 205;
  const line = history.map((s, i) => `${x(i)},${y(value(s))}`).join(" ");
  return (
    <div className="chart" ref={container}>
      <svg
        viewBox={`0 0 ${width} 295`}
        role="img"
        aria-label={`${meta.label}, ${history.length} points`}
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id={`fill-${metric}`} x1="0" y1="0" x2="0" y2="1">
            <stop stopColor={meta.color} stopOpacity=".2" />
            <stop offset="1" stopColor={meta.color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {Array.from({ length: 6 }, (_, i) => {
          const v = low + ((high - low) * i) / 5;
          return (
            <g key={i}>
              <line
                x1="52"
                x2={width - 38}
                y1={y(v)}
                y2={y(v)}
                stroke="var(--border)"
              />
              <text x="43" y={y(v) + 4} textAnchor="end">
                {v.toFixed(metric === "soc" ? 0 : 1)}
              </text>
            </g>
          );
        })}
        {Array.from({ length: 7 }, (_, i) => (
          <g key={i}>
            <line
              x1={52 + (i * plotWidth) / 6}
              x2={52 + (i * plotWidth) / 6}
              y1="40"
              y2="245"
              stroke="var(--border)"
            />
            <text x={52 + (i * plotWidth) / 6} y="267" textAnchor="middle">
              {((firstTime + ((lastTime - firstTime) * i) / 6) / 60).toFixed(1)}
            </text>
          </g>
        ))}
        {history.length > 1 && (
          <>
            <polygon
              points={`52,245 ${line} ${width - 38},245`}
              fill={`url(#fill-${metric})`}
            />
            <polyline
              points={line}
              fill="none"
              stroke={meta.color}
              strokeWidth="2.8"
              strokeLinejoin="round"
            />
            {history.map((s, i) => (
              <circle
                key={i}
                cx={x(i)}
                cy={y(value(s))}
                r="8"
                fill="transparent"
                onMouseEnter={() => setHover(i)}
              />
            ))}
          </>
        )}
        <text x={width / 2} y="290" textAnchor="middle">
          Temps simulé (min)
        </text>
      </svg>
      {history.length < 2 && (
        <div className="chart-empty">
          <strong>Lancez une simulation</strong>
          <span>Les résultats du moteur Python apparaîtront ici.</span>
        </div>
      )}
      {hover !== null && history[hover] && (
        <div className="chart-tooltip">
          {(history[hover].timestamp / 60).toFixed(2)} min ·{" "}
          {value(history[hover]).toFixed(2)} {meta.unit}
        </div>
      )}
    </div>
  );
}
