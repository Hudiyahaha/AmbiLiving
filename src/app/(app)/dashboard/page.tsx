"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, CheckCircle2, Circle, ShieldCheck } from "lucide-react";
import { DayTimeline } from "@/components/DayTimeline";
import { DeviationCard } from "@/components/DeviationCard";
import { useEnvironment } from "@/context/EnvironmentContext";
import { api, type RoutineInfo } from "@/lib/api";
import { activityColor, formatDuration, roomsOf } from "@/lib/caregiver";
import { formatClock, timeToSeconds } from "@/lib/sensorState";

const DAY = 24 * 3600;
const TONE = { notify: "high", summary: "medium", insight: "low" } as const;

function shortClock(t: string) {
  return formatClock(t).replace(/:\d\d /, " ");
}

/** Today at a glance: is everything all right, what is happening, has the routine happened. */
export default function TodayPage() {
  const { currentHome, dataOrigin, live } = useEnvironment();
  const [routine, setRoutine] = useState<{ home: string; info: RoutineInfo } | null>(null);

  useEffect(() => {
    if (dataOrigin !== "api") return;
    let ok = true;
    api
      .routine(currentHome.id)
      .then((info) => ok && setRoutine({ home: currentHome.id, info }))
      .catch(() => undefined);
    return () => {
      ok = false;
    };
  }, [currentHome.id, dataOrigin]);

  const acts = currentHome.activityHistory;
  const now = acts.at(-1) ?? null;
  const urgent = currentHome.anomalies.filter((a) => a.requiresAttention);
  const clock = currentHome.live ? Math.min(currentHome.live.clock, DAY - 1) : undefined;
  const segments = acts.map((a) => {
    const start = timeToSeconds(a.start);
    const end = timeToSeconds(a.end);
    return {
      start,
      end: end < start ? DAY : end,
      label: a.label,
      color: activityColor(currentHome.activityClasses, a.activityId),
    };
  });
  const usualDay = routine?.home === currentHome.id ? routine.info.usual_day : [];
  const labelOf = (raw: string) =>
    currentHome.activityClasses.find((c) => c.id === raw.toLowerCase())?.label ?? raw.replace(/_/g, " ");
  const recent = [...acts].reverse().slice(0, 5);

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {urgent.length ? (
        <Link
          href="/monitoring?tab=alerts"
          className="flex items-center gap-3 rounded-2xl border border-danger/30 bg-danger-soft p-4 transition hover:opacity-90"
        >
          <AlertTriangle className="h-6 w-6 shrink-0 text-danger" />
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-danger">
              {urgent.length === 1 ? "1 thing needs your attention" : `${urgent.length} things need your attention`}
            </p>
            <p className="truncate text-sm text-foreground">
              {urgent[0].title} · {urgent[0].timestamp}
            </p>
          </div>
          <ArrowRight className="h-5 w-5 shrink-0 text-danger" />
        </Link>
      ) : (
        <div className="flex items-center gap-3 rounded-2xl border border-border bg-accent-soft/60 p-4">
          <ShieldCheck className="h-6 w-6 shrink-0 text-accent" />
          <div>
            <p className="font-semibold text-foreground">All as usual</p>
            <p className="text-sm text-muted">Nothing needs your attention right now.</p>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">Now</p>
          {now ? (
            <>
              <p className="mt-1 font-display text-2xl font-semibold text-foreground">{now.label}</p>
              <p className="mt-1 text-sm text-muted">
                since {shortClock(now.start)}
                {roomsOf(now.sensorIds, currentHome.sensors)[0] &&
                  ` · ${roomsOf(now.sensorIds, currentHome.sensors)[0]}`}
              </p>
            </>
          ) : (
            <p className="mt-1 text-sm text-muted">Not known yet</p>
          )}
        </section>

        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm md:col-span-2">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">Daily routine</p>
          {usualDay.length ? (
            <ul className="mt-2 grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2">
              {usualDay.map((d) => {
                const done = acts.find((a) => a.activityId === d.activity.toLowerCase());
                return (
                  <li key={d.activity} className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                      {done ? (
                        <CheckCircle2 className="h-4 w-4 text-accent" />
                      ) : (
                        <Circle className="h-4 w-4 text-muted" />
                      )}
                      <span className={done ? "text-foreground" : "text-muted"}>{labelOf(d.activity)}</span>
                    </span>
                    <span className="text-xs text-muted">
                      {done ? shortClock(done.start) : `usually ~${d.usualFirst}`}
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-muted">Available when the system is online.</p>
          )}
        </section>
      </div>

      <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-foreground">Today</h2>
          <Link
            href="/monitoring?tab=activities"
            className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
          >
            All activities <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        <DayTimeline
          segments={segments}
          now={clock}
          markers={
            currentHome.live
              ? live.feed.alerts.map((a) => ({ t: a.raisedAt, tone: TONE[a.tier], title: a.title }))
              : undefined
          }
        />
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <h2 className="mb-3 font-display text-lg font-semibold text-foreground">Recently</h2>
          <ul className="divide-y divide-border">
            {recent.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-3 py-2.5">
                <span className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: activityColor(currentHome.activityClasses, a.activityId) }}
                    aria-hidden
                  />
                  <span className="font-medium text-foreground">{a.label}</span>
                </span>
                <span className="text-xs text-muted">
                  {shortClock(a.start)} · {formatDuration(a.durationMinutes)}
                </span>
              </li>
            ))}
            {!recent.length && <li className="py-2 text-sm text-muted">Nothing yet today.</li>}
          </ul>
        </section>

        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-foreground">Changes in routine</h2>
            <Link
              href="/monitoring?tab=alerts"
              className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
            >
              All <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          {currentHome.anomalies.length ? (
            <ul className="space-y-3">
              {currentHome.anomalies.slice(0, 2).map((a) => (
                <DeviationCard key={a.id} anom={a} compact />
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">Nothing unusual.</p>
          )}
        </section>
      </div>
    </div>
  );
}
