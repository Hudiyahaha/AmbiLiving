"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, Clock } from "lucide-react";
import { useEnvironment } from "@/context/EnvironmentContext";
import { formatClock, timeToSeconds } from "@/lib/sensorState";

function formatDuration(minutes: number): string {
  if (minutes <= 0) return "< 1 min";
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}

export default function DashboardPage() {
  const { currentHome } = useEnvironment();

  const attention = currentHome.anomalies.filter(
    (a) => a.requiresAttention !== false && a.severity !== "low",
  );
  const attentionOrAll =
    attention.length > 0
      ? attention
      : currentHome.anomalies.filter((a) => a.requiresAttention);

  const todayActivities = currentHome.activityHistory.filter(
    (a) => a.dayLabel === "Today" || a.dayLabel === "Overnight",
  );

  const recentActivities = [...currentHome.activityHistory]
    .filter((a) => a.dayLabel === "Today" || a.dayLabel === "Overnight")
    .sort((a, b) => timeToSeconds(b.start) - timeToSeconds(a.start))
    .slice(0, 5);

  const currentActivity =
    currentHome.activityHistory.find(
      (a) => a.id === currentHome.currentActivityId,
    ) ?? recentActivities[0] ?? null;

  const latestAnomaly = currentHome.anomalies[0] ?? null;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <p className="text-sm text-muted">
          What is happening in the home, is it normal, and does anything require
          attention?
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            Environment
          </p>
          <p className="mt-1 font-display text-xl font-semibold text-foreground">
            {currentHome.name}
          </p>
          <p className="mt-1 text-sm text-muted">{currentHome.residentLabel}</p>
        </section>

        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            Current activity
          </p>
          {currentActivity ? (
            <>
              <p className="mt-1 font-display text-xl font-semibold text-foreground">
                {currentActivity.label}
              </p>
              <p className="mt-1 text-sm text-muted">
                Confidence {Math.round(currentActivity.confidence * 100)}%
              </p>
            </>
          ) : (
            <p className="mt-1 text-sm text-muted">No activity recognized</p>
          )}
        </section>

        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            Today&apos;s activities
          </p>
          <p className="mt-1 font-display text-3xl font-semibold text-foreground">
            {todayActivities.length}
          </p>
          <p className="mt-1 text-sm text-muted">
            {currentHome.activityClasses.length} activity classes configured
          </p>
        </section>

        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            Needs attention
          </p>
          <p className="mt-1 font-display text-3xl font-semibold text-foreground">
            {attentionOrAll.length}
          </p>
          <p className="mt-1 text-sm text-muted">Open anomaly alerts</p>
        </section>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-foreground">
              Recent activities
            </h2>
            <Link
              href="/activities"
              className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
            >
              View all <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <ul className="divide-y divide-border">
            {recentActivities.map((activity) => (
              <li
                key={activity.id}
                className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0"
              >
                <div>
                  <p className="font-medium text-foreground">{activity.label}</p>
                  <p className="mt-0.5 flex items-center gap-1 text-xs text-muted">
                    <Clock className="h-3 w-3" />
                    {formatClock(activity.start)} ·{" "}
                    {formatDuration(activity.durationMinutes)}
                  </p>
                </div>
                <span className="shrink-0 text-xs font-medium text-muted">
                  {Math.round(activity.confidence * 100)}%
                </span>
              </li>
            ))}
            {recentActivities.length === 0 && (
              <li className="py-2 text-sm text-muted">No recent activities.</li>
            )}
          </ul>
        </section>

        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-foreground">
              Anomalies requiring attention
            </h2>
            <Link
              href="/anomalies"
              className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
            >
              View all <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {latestAnomaly ? (
            <div className="rounded-xl bg-danger-soft/40 p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-danger" />
                <div>
                  <p className="font-semibold text-foreground">
                    {latestAnomaly.title}
                  </p>
                  <p className="mt-1 text-sm text-muted">
                    Observed: {latestAnomaly.observed}
                  </p>
                  <p className="text-sm text-muted">
                    Expected: {latestAnomaly.expected}
                  </p>
                  <p className="mt-2 text-xs text-muted">
                    {latestAnomaly.timestamp} · {latestAnomaly.reason}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted">No anomalies flagged.</p>
          )}

          {attentionOrAll.length > 1 && (
            <ul className="mt-3 space-y-2">
              {attentionOrAll.slice(1).map((anom) => (
                <li
                  key={anom.id}
                  className="rounded-lg border border-border px-3 py-2 text-sm"
                >
                  <span className="font-medium text-foreground">{anom.title}</span>
                  <span className="mt-0.5 block text-xs text-muted">
                    {anom.timestamp}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
        <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
          Recent activity timeline
        </h2>
        <ol className="relative space-y-0 border-l border-border ml-2">
          {recentActivities.map((activity) => (
            <li key={activity.id} className="relative pb-5 pl-5 last:pb-0">
              <span className="absolute -left-1.5 top-1.5 h-3 w-3 rounded-full border-2 border-surface bg-accent" />
              <p className="text-xs tabular-nums text-muted">
                {formatClock(activity.start)} – {formatClock(activity.end)}
              </p>
              <p className="font-medium text-foreground">{activity.label}</p>
              <p className="text-xs text-muted">
                Sensors: {activity.sensorIds.join(", ")}
              </p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
