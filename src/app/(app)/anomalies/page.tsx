"use client";

import { AlertTriangle } from "lucide-react";
import { useEnvironment } from "@/context/EnvironmentContext";
import { secondsToTime } from "@/lib/sensorState";

const severityStyles = {
  high: "bg-danger-soft text-danger",
  medium: "bg-warning-soft text-warning",
  low: "bg-surface-muted text-muted",
} as const;

export default function AnomaliesPage() {
  const { currentHome } = useEnvironment();

  const sorted = [...currentHome.anomalies].sort((a, b) => {
    const rank = { high: 0, medium: 1, low: 2 };
    return rank[a.severity] - rank[b.severity];
  });

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <p className="text-sm text-muted">
        How today departs from {currentHome.name}&apos;s own learned routine —
        what was observed against what is usual for this resident. A deviation
        is a change, not necessarily a problem; severity shows how much
        attention it needs.
      </p>

      {currentHome.anomalySource && (
        <p className="rounded-xl border border-border bg-surface-muted/50 px-4 py-3 text-xs text-muted">
          Found on {currentHome.anomalySource.days} real days (
          {currentHome.anomalySource.period}) by the{" "}
          {currentHome.anomalySource.detector.toLowerCase()} on activities
          recognised by {currentHome.anomalySource.recogniser}. The routine was
          learned from {currentHome.anomalySource.routineLearnedFrom}. In
          testing with injected routine deviations it caught{" "}
          {Math.round(currentHome.anomalySource.detectionRate * 100)}% of them
          with {currentHome.anomalySource.falseAlertsPerDay} alerts per normal
          day. Only possible emergencies are sent as notifications; the rest go
          into an evening summary or stay on this page.
        </p>
      )}

      {currentHome.live && (
        <p className="rounded-xl border border-border bg-surface-muted/50 px-4 py-3 text-xs text-muted">
          Live: {currentHome.live.title}, {currentHome.live.dayLabel}, up to{" "}
          {secondsToTime(currentHome.live.clock).slice(0, 5)}. Deviations appear the moment
          the routine model (learned from {currentHome.live.routineLearnedFrom}) raises them,
          checking every 2 minutes on the live activities. Possible emergencies are sent as
          notifications; others wait for the 21:00 evening summary (at most 3) or stay on
          this page.
        </p>
      )}

      {sorted.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted">
          {currentHome.live
            ? "No routine deviations so far today."
            : "No routine deviations recorded for this environment."}
        </p>
      ) : (
        <ul className="space-y-4">
          {sorted.map((anom) => (
            <li
              key={anom.id}
              className="rounded-2xl border border-border bg-surface p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <AlertTriangle
                    className={[
                      "mt-0.5 h-5 w-5 shrink-0",
                      anom.severity === "high"
                        ? "text-danger"
                        : anom.severity === "medium"
                          ? "text-warning"
                          : "text-muted",
                    ].join(" ")}
                  />
                  <div>
                    <h2 className="font-display text-lg font-semibold text-foreground">
                      {anom.title}
                    </h2>
                    <p className="mt-0.5 text-xs text-muted">{anom.timestamp}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {anom.delivery && (
                    <span className="rounded-md border border-border px-2 py-0.5 text-xs font-medium text-muted">
                      {anom.delivery}
                    </span>
                  )}
                  {anom.requiresAttention && (
                    <span className="rounded-md bg-danger-soft px-2 py-0.5 text-xs font-medium text-danger">
                      Needs attention
                    </span>
                  )}
                  <span
                    className={`rounded-md px-2 py-0.5 text-xs font-medium capitalize ${severityStyles[anom.severity]}`}
                  >
                    {anom.severity}
                  </span>
                </div>
              </div>

              <dl className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl bg-surface-muted/50 p-3">
                  <dt className="text-xs font-medium text-muted">Observed</dt>
                  <dd className="mt-1 text-sm font-medium text-foreground">
                    {anom.observed}
                  </dd>
                </div>
                <div className="rounded-xl bg-surface-muted/50 p-3">
                  <dt className="text-xs font-medium text-muted">Expected</dt>
                  <dd className="mt-1 text-sm font-medium text-foreground">
                    {anom.expected}
                  </dd>
                </div>
                <div className="rounded-xl bg-surface-muted/50 p-3">
                  <dt className="text-xs font-medium text-muted">Reason</dt>
                  <dd className="mt-1 text-sm font-medium text-foreground">
                    {anom.reason}
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
