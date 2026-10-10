"use client";

import { AlertTriangle } from "lucide-react";
import { useEnvironment } from "@/context/EnvironmentContext";

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
        Caregiver-readable routine deviations for {currentHome.name}. Anomalies
        are separate from activity recognition — shown as understandable
        results, not raw scores.
      </p>

      {sorted.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted">
          No anomalies recorded for this environment.
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
