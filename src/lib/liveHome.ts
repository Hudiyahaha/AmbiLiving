/**
 * Turns a live feed (useLiveFeed) into the HomeEnvironment shape the pages use, so
 * Dashboard, Activity History and Routine deviations show live data unchanged.
 */
import type { LiveAlert, LiveEpisode, LiveEvent } from "@/lib/api";
import { secondsToTime } from "@/lib/sensorState";
import type { LiveFeed } from "@/hooks/useLiveFeed";
import type {
  ActivityClass,
  AnomalyRecord,
  HomeEnvironment,
  RecognizedActivity,
  SensorEvent,
  SensorStateValue,
} from "@/types/home";

const STATE: Record<string, SensorStateValue> = {
  ON: "active",
  OFF: "inactive",
  OPEN: "open",
  CLOSE: "closed",
};

const SEVERITY = { notify: "high", summary: "medium", insight: "low" } as const;
export const SUMMARY_AT = 21 * 3600;

export function activityLabel(classes: ActivityClass[], raw: string): string {
  return classes.find((c) => c.id === raw.toLowerCase())?.label ?? raw.replace(/_/g, " ");
}

export function liveEvents(events: LiveEvent[]): SensorEvent[] {
  return events.map(([t, sensorId, state]) => ({
    timestamp: secondsToTime(t),
    sensorId,
    state: STATE[state] ?? state,
  }));
}

function episodeId(home: string, ep: LiveEpisode) {
  return `${home}-live-${Math.round(ep.start * 1000)}`;
}

export function liveActivities(
  home: string,
  classes: ActivityClass[],
  episodes: LiveEpisode[],
): RecognizedActivity[] {
  return episodes.map((ep) => ({
    id: episodeId(home, ep),
    activityId: ep.activity.toLowerCase(),
    label: activityLabel(classes, ep.activity),
    start: secondsToTime(ep.start),
    end: secondsToTime(Math.min(ep.end, 86399)),
    durationMinutes: Math.max(0, ep.end - ep.start) / 60,
    confidence: ep.confidence ?? 0,
    sensorIds: ep.sensors,
    dayLabel: "Today",
  }));
}

/** How a deviation reached (or will reach) the caregiver, decision D15. */
export function deliveryLabel(a: LiveAlert, clock: number): string {
  if (a.tier === "notify") {
    return a.delivered ? "Sent as notification" : "Not re-sent (2-hour cool-down)";
  }
  if (a.tier === "summary") {
    if (a.raisedAt > SUMMARY_AT) return "In tomorrow's evening summary";
    if (clock < SUMMARY_AT) return a.inSummary ? "For the 21:00 summary" : "Dashboard only (summary full)";
    return a.inSummary ? "In evening summary" : "Dashboard only";
  }
  return "Dashboard only";
}

export function liveAnomalies(
  alerts: LiveAlert[],
  dayLabel: string,
  clock: number,
): AnomalyRecord[] {
  return [...alerts]
    .sort((a, b) => b.raisedAt - a.raisedAt)
    .map((a) => ({
      id: a.id,
      title: a.title,
      observed: a.observed,
      expected: a.expected,
      reason: a.reason,
      severity: SEVERITY[a.tier],
      relatedActivityId: a.activity.toLowerCase(),
      timestamp: `${dayLabel} · raised ${secondsToTime(a.raisedAt).slice(0, 5)}`,
      requiresAttention: a.tier === "notify" && a.delivered,
      delivery: deliveryLabel(a, clock),
    }));
}

/** `events` may be passed pre-converted (they only grow, so callers memoise them). */
export function toLiveHome(
  home: HomeEnvironment,
  feed: LiveFeed,
  events: SensorEvent[] = liveEvents(feed.events),
): HomeEnvironment {
  const meta = feed.meta!;
  const activityHistory = liveActivities(home.id, home.activityClasses, feed.episodes);
  const latest = feed.current;
  return {
    ...home,
    events,
    activityHistory,
    anomalies: liveAnomalies(feed.alerts, meta.dayLabel, meta.clock),
    currentActivityId: activityHistory.at(-1)?.id ?? null,
    dataSource: undefined,
    anomalySource: undefined,
    live: {
      status: meta.status,
      scenario: meta.scenario,
      title: meta.title,
      dayLabel: meta.dayLabel,
      speed: meta.speed,
      clock: meta.clock,
      recogniser: meta.recogniser,
      episodeRule: meta.episodeRule,
      routineLearnedFrom: meta.routineLearnedFrom,
      injected: meta.injected,
      latest: latest
        ? {
            activityId: latest.activity.toLowerCase(),
            label: activityLabel(home.activityClasses, latest.activity),
            confidence: latest.confidence,
            at: latest.at,
          }
        : null,
    },
  };
}
