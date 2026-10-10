"use client";

import { useMemo, useState } from "react";
import { X } from "lucide-react";
import { useEnvironment } from "@/context/EnvironmentContext";
import { formatClock, timeToSeconds } from "@/lib/sensorState";
import type { RecognizedActivity } from "@/types/home";

function formatDuration(minutes: number): string {
  if (minutes <= 0) return "< 1 min";
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}

function ActivityDetail({
  activity,
  events,
  onClose,
}: {
  activity: RecognizedActivity;
  events: { timestamp: string; sensorId: string; state: string | number }[];
  onClose: () => void;
}) {
  const start = timeToSeconds(activity.start);
  const end = timeToSeconds(activity.end);
  const sequence = events.filter((e) => {
    const t = timeToSeconds(e.timestamp);
    // Handle overnight sleep where end < start
    if (end < start) return t >= start || t <= end;
    return t >= start && t <= end;
  });

  return (
    <aside className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            Activity details
          </p>
          <h2 className="font-display text-xl font-semibold text-foreground">
            {activity.label}
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1.5 text-muted hover:bg-surface-muted"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-muted">Start</dt>
          <dd className="font-medium">{formatClock(activity.start)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">End</dt>
          <dd className="font-medium">{formatClock(activity.end)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Duration</dt>
          <dd className="font-medium">
            {formatDuration(activity.durationMinutes)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Confidence</dt>
          <dd className="font-medium">
            {Math.round(activity.confidence * 100)}%
          </dd>
        </div>
      </dl>

      <div className="mt-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">
          Sensors involved
        </p>
        <p className="mt-2 flex flex-wrap gap-1.5">
          {activity.sensorIds.map((id) => (
            <span
              key={id}
              className="rounded-md bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent"
            >
              {id}
            </span>
          ))}
        </p>
      </div>

      <div className="mt-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">
          Relevant sensor sequence
        </p>
        <ul className="mt-2 max-h-56 overflow-auto rounded-lg border border-border text-xs">
          {sequence.length > 0 ? (
            sequence.map((e, i) => (
              <li
                key={`${e.timestamp}-${e.sensorId}-${i}`}
                className="flex justify-between gap-2 border-b border-border px-3 py-1.5 last:border-0"
              >
                <span className="tabular-nums text-muted">
                  {formatClock(e.timestamp)}
                </span>
                <span className="font-medium text-foreground">
                  {e.sensorId}{" "}
                  <span className="text-muted">
                    {typeof e.state === "number"
                      ? `${e.state}°C`
                      : String(e.state).toUpperCase()}
                  </span>
                </span>
              </li>
            ))
          ) : (
            <li className="px-3 py-2 text-muted">
              No streamed events in this window (activity may be outside the
              current playback clip).
            </li>
          )}
        </ul>
      </div>
    </aside>
  );
}

export default function ActivitiesPage() {
  const { currentHome } = useEnvironment();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const rows = useMemo(() => {
    return [...currentHome.activityHistory].sort((a, b) => {
      const dayRank = (d?: string) =>
        d === "Today" ? 0 : d === "Overnight" ? 1 : 2;
      const dr = dayRank(a.dayLabel) - dayRank(b.dayLabel);
      if (dr !== 0) return dr;
      return timeToSeconds(b.start) - timeToSeconds(a.start);
    });
  }, [currentHome.activityHistory]);

  const selected = rows.find((r) => r.id === selectedId) ?? null;

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <p className="text-sm text-muted">
        Recognized activities for {currentHome.name} — chronological history
        from ambient sensor streams.
      </p>

      <div className="grid gap-4 lg:grid-cols-[1fr_minmax(260px,320px)]">
        <div className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="border-b border-border bg-surface-muted/50 text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Time</th>
                  <th className="px-4 py-3 font-medium">Activity</th>
                  <th className="px-4 py-3 font-medium">Duration</th>
                  <th className="px-4 py-3 font-medium">Confidence</th>
                  <th className="px-4 py-3 font-medium">Day</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const active = row.id === selectedId;
                  return (
                    <tr
                      key={row.id}
                      onClick={() => setSelectedId(row.id)}
                      className={[
                        "cursor-pointer border-b border-border last:border-0 transition",
                        active ? "bg-accent-soft/60" : "hover:bg-surface-muted/40",
                      ].join(" ")}
                    >
                      <td className="px-4 py-3 tabular-nums text-foreground">
                        {formatClock(row.start)}
                      </td>
                      <td className="px-4 py-3 font-medium text-foreground">
                        {row.label}
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {formatDuration(row.durationMinutes)}
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {Math.round(row.confidence * 100)}%
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {row.dayLabel ?? "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {selected ? (
          <ActivityDetail
            activity={selected}
            events={currentHome.events}
            onClose={() => setSelectedId(null)}
          />
        ) : (
          <div className="rounded-2xl border border-dashed border-border bg-surface/60 p-5 text-sm text-muted">
            Click an activity to see start/end time, duration, confidence,
            sensors involved, and the relevant sensor sequence.
          </div>
        )}
      </div>
    </div>
  );
}
