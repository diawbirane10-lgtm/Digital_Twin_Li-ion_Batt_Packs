export interface State {
  timestamp: number;
  soc: number;
  soc_std: number;
  soh: number;
  rul_cycles: number | null;
  pack_voltage: number;
  current: number;
  T_max: number;
  soc_imbalance: number;
  alerts: string[];
  V_cell_min: number;
  V_cell_max: number;
}
export interface Cell {
  id: number;
  row: number;
  col: number;
  soc: number;
  voltage: number;
  temperature: number;
  current: number;
}
export interface Config {
  ns: number;
  np: number;
  temperature: number;
  soc: number;
}
export interface Snapshot {
  session_id?: string;
  state: State;
  cells: Cell[];
  history: State[];
  configuration: Config;
  limits: {
    V_cell_max: number;
    V_cell_min: number;
    T_max: number;
    SOC_min: number;
  };
  stop_reason: string | null;
  cycle_count: number;
  cycle_history: number[];
}
const base =
  (import.meta as unknown as { env: Record<string, string> }).env
    .VITE_API_URL || "/api";
export async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(base + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    let message = "API indisponible";
    try {
      const result = await response.json();
      message =
        typeof result.detail === "string"
          ? result.detail
          : `Requête refusée (${response.status})`;
    } catch {
      /* HTTP error */
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
