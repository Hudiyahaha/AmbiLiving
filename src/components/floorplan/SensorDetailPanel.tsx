"use client";

import { X } from "lucide-react";
import type { SensorDefinition, SensorEvent, SensorStateValue } from "@/types/home";
import { SENSOR_COLORS } from "@/lib/sensorColors";
import {
  countEventsForSensor,
  formatSensorState,
  lastEventTimeForSensor,
} from "@/lib/sensorState";

interface SensorDetailPanelProps {
  sensor: SensorDefinition;
  state: SensorStateValue | undefined;
  events: SensorEvent[];
  timestamp: string;
  onClose: () => void;
}

function formatClock(time: string): string {
  const [h, m, s] = time.split(":").map(Number);
  const period = h >= 12 ? "PM" : "AM";
  const hour12 = h % 12 || 12;
  return `${hour12}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")} ${period}`;
}

export function SensorDetailPanel({
  sensor,
  state,
  events,
  timestamp,
  onClose,
}: SensorDetailPanelProps) {
  const palette = SENSOR_COLORS[sensor.type];
  const lastEvent = lastEventTimeForSensor(events, sensor.id, timestamp);
  const eventsToday = countEventsForSensor(events, sensor.id);

  return (
    <aside className="w-full max-w-xs rounded-2xl border border-border bg-surface p-4 shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            Sensor
          </p>
          <h2 className="font-display text-xl font-semibold text-foreground">
            {sensor.id}
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1.5 text-muted transition hover:bg-surface-muted hover:text-foreground"
          aria-label="Close sensor details"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <dl className="mt-4 space-y-3 text-sm">
        <div>
          <dt className="text-xs text-muted">Type</dt>
          <dd className="mt-0.5 flex items-center gap-2 font-medium text-foreground">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: palette.fill }}
              aria-hidden
            />
            {palette.label}
            {sensor.type === "motion" && sensor.size
              ? ` · ${sensor.size} cone`
              : ""}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Room</dt>
          <dd className="mt-0.5 font-medium text-foreground">{sensor.room}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Current state</dt>
          <dd className="mt-0.5 font-medium text-foreground">
            {formatSensorState(sensor, state)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Last event</dt>
          <dd className="mt-0.5 font-medium text-foreground">
            {lastEvent ? formatClock(lastEvent) : "None yet"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Events in stream</dt>
          <dd className="mt-0.5 font-medium text-foreground">{eventsToday}</dd>
        </div>
      </dl>
    </aside>
  );
}
