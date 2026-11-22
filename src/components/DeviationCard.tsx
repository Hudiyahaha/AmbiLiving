import { AlertTriangle } from "lucide-react";
import type { AnomalyRecord } from "@/types/home";

const severityStyles = {
  high: "bg-danger-soft text-danger",
  medium: "bg-warning-soft text-warning",
  low: "bg-surface-muted text-muted",
} as const;

const iconStyles = { high: "text-danger", medium: "text-warning", low: "text-muted" } as const;

/** One routine deviation as the caregiver sees it: what happened vs what is usual. */
export function DeviationCard({ anom, compact = false }: { anom: AnomalyRecord; compact?: boolean }) {
  return (
    <li className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <AlertTriangle className={`mt-0.5 h-5 w-5 shrink-0 ${iconStyles[anom.severity]}`} />
          <div>
            <h3 className="font-medium text-foreground">{anom.title}</h3>
            <p className="mt-0.5 text-xs text-muted">{anom.timestamp}</p>
          </div>
        </div>
        {anom.delivery && (
          <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${severityStyles[anom.severity]}`}>
            {anom.delivery}
          </span>
        )}
      </div>
      <dl className={`mt-3 grid gap-2 text-sm ${compact ? "" : "sm:grid-cols-2"}`}>
        <div className="rounded-xl bg-surface-muted/50 p-3">
          <dt className="text-xs text-muted">What happened</dt>
          <dd className="mt-0.5 text-foreground">{anom.observed}</dd>
        </div>
        <div className="rounded-xl bg-surface-muted/50 p-3">
          <dt className="text-xs text-muted">Usually</dt>
          <dd className="mt-0.5 text-foreground">{anom.expected}</dd>
        </div>
      </dl>
      {!compact && <p className="mt-2 text-xs text-muted">{anom.reason}</p>}
    </li>
  );
}
