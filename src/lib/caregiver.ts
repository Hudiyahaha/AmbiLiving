/**
 * Small helpers for caregiver-facing views: activity colours, rooms instead of
 * sensor ids, and plain-language durations.
 */
import type { ActivityClass, SensorDefinition } from "@/types/home";

export const ACTIVITY_PALETTE = [
  "#3f6b52", "#9a6b2f", "#4f6d8f", "#9b4d3c", "#6b5b8f", "#2f7f7a",
  "#8f6b4f", "#5f7f2f", "#8f4f6f", "#4f8f5f", "#7a6a2f", "#2f5f8f",
  "#8f2f4f", "#5f5f5f", "#3f8f8f",
];

/** A stable colour per activity, from its position in the home's activity list. */
export function activityColor(classes: ActivityClass[], activityId: string): string {
  const i = classes.findIndex((c) => c.id === activityId.toLowerCase());
  return i < 0 ? "#c9c9c4" : ACTIVITY_PALETTE[i % ACTIVITY_PALETTE.length];
}

/** Rooms of the given sensors, in first-seen order. */
export function roomsOf(sensorIds: string[], sensors: SensorDefinition[]): string[] {
  const room = new Map(sensors.map((s) => [s.id, s.room]));
  const out: string[] = [];
  for (const id of sensorIds) {
    const r = room.get(id);
    if (r && !out.includes(r)) out.push(r);
  }
  return out;
}

export function formatDuration(rawMinutes: number): string {
  const minutes = Math.round(rawMinutes);
  if (minutes <= 0) return "< 1 min";
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}
