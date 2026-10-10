import type { RecognizedActivity, SensorEvent } from "@/types/home";
import { timeToSeconds } from "@/lib/sensorState";

/** Activity covering the given timestamp (inclusive). Prefer latest start if overlap. */
export function getActivityAtTime(
  activities: RecognizedActivity[],
  timestamp: string,
): RecognizedActivity | null {
  const t = timeToSeconds(timestamp);
  let best: RecognizedActivity | null = null;
  for (const activity of activities) {
    const start = timeToSeconds(activity.start);
    const end = timeToSeconds(activity.end);
    const inWindow =
      end >= start ? t >= start && t <= end : t >= start || t <= end; // overnight
    if (inWindow) {
      if (!best || start >= timeToSeconds(best.start)) {
        best = activity;
      }
    }
  }
  return best;
}

export function getEventIndexAtOrBefore(
  events: SensorEvent[],
  timestamp: string,
): number {
  if (events.length === 0) return -1;
  const t = timeToSeconds(timestamp);
  let idx = -1;
  for (let i = 0; i < events.length; i++) {
    if (timeToSeconds(events[i].timestamp) <= t) idx = i;
    else break;
  }
  return idx;
}

export function timelineBounds(events: SensorEvent[]): {
  startSec: number;
  endSec: number;
  start: string;
  end: string;
} | null {
  if (events.length === 0) return null;
  const start = events[0].timestamp;
  const end = events[events.length - 1].timestamp;
  return {
    start,
    end,
    startSec: timeToSeconds(start),
    endSec: timeToSeconds(end),
  };
}
