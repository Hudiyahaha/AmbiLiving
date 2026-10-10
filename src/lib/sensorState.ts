import type {
  DoorState,
  MotionState,
  SensorDefinition,
  SensorEvent,
  SensorStateValue,
} from "@/types/home";

/** Convert "HH:MM:SS" to seconds for ordering. */
export function timeToSeconds(time: string): number {
  const [h, m, s] = time.split(":").map(Number);
  return h * 3600 + m * 60 + (s || 0);
}

export function secondsToTime(total: number): string {
  const clamped = Math.max(0, Math.floor(total));
  const h = Math.floor(clamped / 3600);
  const m = Math.floor((clamped % 3600) / 60);
  const s = clamped % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function formatClock(time: string): string {
  const [h, m, s] = time.split(":").map(Number);
  const period = h >= 12 ? "PM" : "AM";
  const hour12 = h % 12 || 12;
  return `${hour12}:${String(m).padStart(2, "0")}:${String(s ?? 0).padStart(2, "0")} ${period}`;
}

export function formatSensorState(
  sensor: SensorDefinition,
  state: SensorStateValue | undefined,
): string {
  if (state === undefined) {
    if (sensor.type === "motion") return "INACTIVE";
    if (sensor.type === "door") return "CLOSED";
    return "—";
  }
  if (typeof state === "number") return `${state.toFixed(1)}°C`;
  return String(state).toUpperCase();
}

export function defaultStateForSensor(
  sensor: SensorDefinition,
): SensorStateValue {
  if (sensor.type === "motion") return "inactive";
  if (sensor.type === "door") return "closed";
  return 21.5;
}

/**
 * Replay events up to (and including) `timestamp` and return the latest
 * state per sensor. Home-agnostic — works for any event list.
 */
export function getSensorStatesAtTime(
  sensors: SensorDefinition[],
  events: SensorEvent[],
  timestamp: string,
): Record<string, SensorStateValue> {
  const cutoff = timeToSeconds(timestamp);
  const states: Record<string, SensorStateValue> = {};

  for (const sensor of sensors) {
    // Temperature stays unset until a reading appears in the stream
    if (sensor.type !== "temperature") {
      states[sensor.id] = defaultStateForSensor(sensor);
    }
  }

  for (const event of events) {
    if (timeToSeconds(event.timestamp) > cutoff) break;
    states[event.sensorId] = event.state;
  }

  return states;
}

export function isSensorVisuallyActive(
  sensor: SensorDefinition,
  state: SensorStateValue | undefined,
): boolean {
  if (state === undefined) return false;
  if (sensor.type === "motion") return state === ("active" satisfies MotionState);
  if (sensor.type === "door") return state === ("open" satisfies DoorState);
  // Temperature: active only once a reading exists in the stream
  return typeof state === "number";
}

export function countEventsForSensor(
  events: SensorEvent[],
  sensorId: string,
): number {
  return events.filter((e) => e.sensorId === sensorId).length;
}

export function lastEventTimeForSensor(
  events: SensorEvent[],
  sensorId: string,
  atOrBefore: string,
): string | null {
  const cutoff = timeToSeconds(atOrBefore);
  let last: string | null = null;
  for (const event of events) {
    if (event.sensorId !== sensorId) continue;
    if (timeToSeconds(event.timestamp) > cutoff) break;
    last = event.timestamp;
  }
  return last;
}
