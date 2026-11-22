"use client";

import { DayTimeline, type TimelineMarker } from "@/components/DayTimeline";
import { DeviationCard } from "@/components/DeviationCard";
import { activityColor, formatDuration, roomsOf } from "@/lib/caregiver";
import { formatClock, timeToSeconds } from "@/lib/sensorState";
import type { HomeEnvironment } from "@/types/home";

const DAY = 24 * 3600;

/** Today's recognised activities: a timeline of the day and the list, newest first. */
export function ActivitiesPanel({
  home,
  now,
  markers,
}: {
  home: HomeEnvironment;
  now?: number;
  markers?: TimelineMarker[];
}) {
  const acts = home.activityHistory;
  const segments = acts.map((a) => {
    const start = timeToSeconds(a.start);
    let end = timeToSeconds(a.end);
    if (end < start) end = DAY; // overnight: show until midnight
    return { start, end, label: a.label, color: activityColor(home.activityClasses, a.activityId) };
  });
  const rows = [...acts].sort((a, b) => timeToSeconds(b.start) - timeToSeconds(a.start));

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
        <DayTimeline segments={segments} markers={markers} now={now} />
      </section>
      <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
        {rows.length === 0 ? (
          <p className="p-6 text-center text-sm text-muted">No activities yet today.</p>
        ) : (
          <ul className="divide-y divide-border">
            {rows.map((a, i) => {
              const rooms = roomsOf(a.sensorIds, home.sensors);
              return (
                <li key={a.id} className="flex items-center gap-4 px-4 py-3">
                  <span
                    className="h-8 w-1.5 shrink-0 rounded-full"
                    style={{ backgroundColor: activityColor(home.activityClasses, a.activityId) }}
                    aria-hidden
                  />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-foreground">
                      {a.label}
                      {i === 0 && home.live && (
                        <span className="ml-2 rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent">
                          Now
                        </span>
                      )}
                    </p>
                    {rooms.length > 0 && (
                      <p className="truncate text-xs text-muted">{rooms.join(" · ")}</p>
                    )}
                  </div>
                  <div className="shrink-0 text-right text-sm">
                    <p className="tabular-nums text-foreground">{formatClock(a.start).replace(/:\d\d /, " ")}</p>
                    <p className="text-xs text-muted">{formatDuration(a.durationMinutes)}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

/** Routine deviations: those that needed attention first. */
export function AlertsPanel({ home }: { home: HomeEnvironment }) {
  const urgent = home.anomalies.filter((a) => a.requiresAttention);
  const other = home.anomalies.filter((a) => !a.requiresAttention);
  if (!home.anomalies.length) {
    return (
      <p className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted">
        Nothing unusual {home.live ? "today" : "recorded"}.
      </p>
    );
  }
  return (
    <div className="space-y-5">
      {urgent.length > 0 && (
        <section>
          <h2 className="mb-2 text-sm font-semibold text-foreground">Needs attention</h2>
          <ul className="space-y-3">
            {urgent.map((a) => (
              <DeviationCard key={a.id} anom={a} />
            ))}
          </ul>
        </section>
      )}
      {other.length > 0 && (
        <section>
          <h2 className="mb-2 text-sm font-semibold text-foreground">Other changes in routine</h2>
          <ul className="space-y-3">
            {other.map((a) => (
              <DeviationCard key={a.id} anom={a} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
