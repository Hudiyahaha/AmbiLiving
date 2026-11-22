/**
 * Client for the AmbiLiving backend (FastAPI, `ml/api/`, decision D16).
 *
 * Start it from ml/ with `py -m api`. Set NEXT_PUBLIC_AMBILIVING_API to use
 * another address. Every caller has a fallback to the bundled files, so the
 * dashboard still works when the API is not running.
 */
import type { ExportedAnomalies } from "@/data/homes/realAnomalies";
import type { ExportedDay } from "@/data/homes/realData";
import type { ReplayIndex, ReplayScenario } from "@/types/replay";

export const API_BASE = (
  process.env.NEXT_PUBLIC_AMBILIVING_API ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const TIMEOUT_MS = 8000;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const { timeoutMs = TIMEOUT_MS, signal, ...rest } = init ?? {};
  const signals = [AbortSignal.timeout(timeoutMs), ...(signal ? [signal] : [])];
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      signal: AbortSignal.any(signals),
    });
  } catch (err) {
    if (signal?.aborted) throw err;
    throw new ApiError(`AmbiLiving API not reachable at ${API_BASE}`);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : res.statusText;
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; homes: string[] }>("/health", { timeoutMs: 3000 }),
  day: (home: string) => request<ExportedDay>(`/homes/${encodeURIComponent(home)}/day`),
  anomalies: (home: string) =>
    request<ExportedAnomalies>(`/homes/${encodeURIComponent(home)}/anomalies`),
  replayIndex: () => request<ReplayIndex>("/replay"),
  scenario: (home: string, id: string) =>
    request<ReplayScenario>(
      `/replay/${encodeURIComponent(home)}/${encodeURIComponent(id)}`,
      { timeoutMs: 20000 },
    ),
  feeds: (home: string) =>
    request<FeedScenario[]>(`/homes/${encodeURIComponent(home)}/feeds`),
  createSimulation: (home: string, body: SimulationRequest) =>
    request<SimulationMeta>(`/homes/${encodeURIComponent(home)}/simulations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  simulation: (id: string) =>
    request<SimulationMeta>(`/simulations/${encodeURIComponent(id)}`),
  controlSimulation: (id: string, action: "pause" | "resume" | "speed", speed?: number) =>
    request<SimulationMeta>(`/simulations/${encodeURIComponent(id)}/control`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, speed }),
    }),
  deleteSimulation: (id: string) =>
    fetch(`${API_BASE}/simulations/${encodeURIComponent(id)}`, { method: "DELETE" }).catch(
      () => undefined,
    ),
  simulationStreamUrl: (id: string) =>
    `${API_BASE}/simulations/${encodeURIComponent(id)}/stream`,
  recognise: (home: string, body: RecogniseRequest, signal?: AbortSignal) =>
    request<RecogniseResponse>(`/homes/${encodeURIComponent(home)}/recognise`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
      // The first call loads the model (a couple of seconds).
      timeoutMs: 15000,
    }),
};

// ---- simulated live homes (ml/api/simulate.py, decision D19)

export interface FeedScenario {
  id: string;
  title: string;
  day: string;
  kind: string;
}

export interface SimulationRequest {
  scenario: string;
  /** Simulated seconds per real second */
  speed: number;
  /** Second of the day to start at */
  startAt: number;
}

export type SimulationStatus = "starting" | "running" | "paused" | "finished" | "error";

export interface SimulationMeta {
  simulation: string;
  session: string;
  home: string;
  scenario: string;
  title: string;
  kind: string;
  day: string;
  dayLabel: string;
  injected: { target: string; start: number; end: number; note: string } | null;
  typical: {
    detected: number | null;
    notified: number | null;
    surfaced: number | null;
    thisOneCaught: boolean | null;
  } | null;
  status: SimulationStatus;
  error: string | null;
  speed: number;
  startAt: number;
  /** Simulated second of the day */
  clock: number;
  recogniser: string;
  episodeRule: string;
  routineLearnedFrom: string;
}

/** [second of day, sensor id, CASAS state ON/OFF/OPEN/CLOSE] */
export type LiveEvent = [number, string, string];
/** [second of day, activity, confidence] */
export type LivePrediction = [number, string, number];

export interface LiveEpisode {
  activity: string;
  start: number;
  end: number;
  confidence: number | null;
  predictions: number;
  sensors: string[];
}

export interface LiveAlert {
  id: string;
  raisedAt: number;
  time: number;
  kind: string;
  activity: string;
  title: string;
  observed: string;
  expected: string;
  reason: string;
  severity?: string;
  tier: "notify" | "summary" | "insight";
  delivered: boolean;
  inSummary?: boolean;
}

export interface LiveCurrent {
  activity: string;
  confidence: number;
  at: number;
  episode: string;
  episodeSince: number | null;
}

export interface SimulationSnapshot extends SimulationMeta {
  type: "snapshot";
  events: LiveEvent[];
  predictions: LivePrediction[];
  episodes: LiveEpisode[];
  alerts: LiveAlert[];
  current: LiveCurrent | null;
}

export interface SimulationTick {
  type: "tick";
  status: SimulationStatus;
  error: string | null;
  speed?: number;
  clock: number;
  eventsFrom?: number;
  predictionsFrom?: number;
  events?: LiveEvent[];
  predictions?: LivePrediction[];
  episodes?: LiveEpisode[];
  alerts?: LiveAlert[];
  newAlerts?: string[];
  current?: LiveCurrent | null;
}

export interface RecogniseRequest {
  events: { timestamp: string; sensor: string; state: string }[];
  every?: number;
  top?: number;
}

export interface Recognised {
  timestamp: string;
  eventIndex: number;
  activity: string;
  confidence: number;
  top: { activity: string; confidence: number }[];
}

export interface RecogniseResponse {
  home: string;
  model: string;
  windowEvents: number;
  events: number;
  unknownSensorStates: string[];
  current: Recognised;
  history: Recognised[] | null;
}
