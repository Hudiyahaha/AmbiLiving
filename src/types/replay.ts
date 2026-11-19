/**
 * Live-demo replays written by `python -m har.replay` (run from ml/) into
 * public/replay/. All times are seconds since midnight of the replayed day.
 */

export type ReplayTier = "notify" | "summary" | "insight";

export interface ReplayAlert {
  /** First minute at which the live pipeline, given only data so far, raised it */
  raisedAt: number;
  /** When the deviation itself happened or crossed its threshold */
  time: number;
  kind: string;
  activity: string;
  title: string;
  observed: string;
  expected: string;
  reason: string;
  tier: ReplayTier;
  /** False for notifications held back by the 2-hour cool-down or summary items over the cap */
  delivered: boolean;
  inSummary?: boolean;
  /** Matches the injected deviation under the evaluation's matching rule */
  explainsInjection?: boolean;
}

export interface ReplayScenario {
  home: string;
  id: string;
  title: string;
  kind: string;
  day: string;
  injected: { target: string; start: number; end: number; note: string } | null;
  typical: {
    detected: number | null;
    notified: number | null;
    surfaced: number | null;
    thisOneCaught: boolean | null;
  } | null;
  sensors: string[];
  /** [seconds, sensor index, state index] */
  events: [number, number, number][];
  states: string[];
  /** Dataset activity names; predictions, episodes and annotations index into it */
  labels: string[];
  /** [seconds, label index, confidence]: one BiLSTM prediction every 10th event */
  predictions: [number, number, number][];
  /** [start, end, label index]: the live predictions grouped into episodes */
  episodes: [number, number, number][];
  /** [start, end, label index]: the dataset's own annotations, for checking */
  annotations: [number, number, number][];
  /** Most likely activities in each half hour of this resident's usual day */
  usual: string[][];
  /** Activities that happen on most days, with their usual first time */
  daily: { activity: string; usualFirst: string; pDay: number }[];
  summaryAt: number;
  alerts: ReplayAlert[];
}

export interface ReplayScenarioRef {
  id: string;
  title: string;
  day: string;
  kind: string;
  file: string;
  reproduced: boolean;
  notRaisedLive: number;
}

export interface ReplayHome {
  recogniser: string;
  recogniserMacroF1: number;
  routineLearnedFrom: string;
  falseAlertsPerDay: number;
  detectionRate: number;
  urgentNotified: number;
  scenarios: ReplayScenarioRef[];
}

export type ReplayIndex = Record<string, ReplayHome>;
