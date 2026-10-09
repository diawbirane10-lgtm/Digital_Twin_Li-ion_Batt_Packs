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
async function http<T>(
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

const stateless = (import.meta as unknown as { env: Record<string, string> }).env.VITE_STATELESS_API === "1";
let checkpoint: unknown = null;
let configuration: unknown = null;
let history: State[] = [];
export async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  if (!stateless || !path.startsWith("/sessions")) return http<T>(path,method,body);
  if (method === "DELETE") return {} as T;
  const creating = path === "/sessions";
  if (creating) { configuration = body; checkpoint = null; history = []; }
  const result = await http<Snapshot & { checkpoint: unknown }>("/simulation", "POST", {configuration, checkpoint, step: creating ? undefined : body});
  checkpoint = result.checkpoint;
  history = [...history,...result.history].slice(-20000);
  const stride = Math.max(1, Math.ceil(history.length/600));
  const sampled = history.filter((_,i)=>i%stride===0 || i===history.length-1);
  return {...result,history:sampled} as T;
}
