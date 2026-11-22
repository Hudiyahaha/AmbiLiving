"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { SENSOR_COLORS } from "@/lib/sensorColors";
import type { HomeEnvironment, SensorDefinition } from "@/types/home";

export type MonitoringTab = "home" | "activities" | "alerts";

export function useMonitoringTab(): MonitoringTab {
  const t = useSearchParams().get("tab");
  return t === "activities" || t === "alerts" ? t : "home";
}

/** Clock, status and tabs shared by the live and recorded-day views. */
export function MonitoringShell({
  home,
  status,
  clock,
  subtitle,
  actions,
  children,
}: {
  home: HomeEnvironment;
  status?: ReactNode;
  clock: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const tab = useMonitoringTab();
  const urgent = home.anomalies.filter((a) => a.requiresAttention).length;
  const tabs: { id: MonitoringTab; label: string; badge?: ReactNode }[] = [
    { id: "home", label: "Home" },
    {
      id: "activities",
      label: home.live ? "Activities today" : "Activities",
      badge: <span className="text-muted">{home.activityHistory.length}</span>,
    },
    {
      id: "alerts",
      label: home.live ? "Alerts today" : "Alerts",
      badge: home.anomalies.length ? (
        <span
          className={`rounded-full px-1.5 text-xs ${urgent ? "bg-danger text-white" : "bg-surface-muted text-muted"}`}
        >
          {home.anomalies.length}
        </span>
      ) : null,
    },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          {status}
          <p className="font-display text-3xl font-semibold tabular-nums tracking-tight text-foreground">
            {clock}
          </p>
          {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
        </div>
        {actions}
      </div>

      <nav className="flex gap-1 border-b border-border" aria-label="Monitoring views">
        {tabs.map((t) => (
          <Link
            key={t.id}
            href={t.id === "home" ? "/monitoring" : `/monitoring?tab=${t.id}`}
            replace
            scroll={false}
            className={[
              "-mb-px flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition",
              tab === t.id
                ? "border-accent text-foreground"
                : "border-transparent text-muted hover:text-foreground",
            ].join(" ")}
          >
            {t.label}
            {t.badge}
          </Link>
        ))}
      </nav>

      {children}
    </div>
  );
}

/** Rooms where a sensor is currently active (sensor ids in the tooltip). */
export function RoomsCard({ active }: { active: SensorDefinition[] }) {
  const rooms = new Map<string, SensorDefinition[]>();
  for (const s of active) rooms.set(s.room, [...(rooms.get(s.room) ?? []), s]);
  return (
    <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
      <h2 className="text-xs font-medium uppercase tracking-wide text-muted">Movement in</h2>
      <p className="mt-2 flex flex-wrap gap-2">
        {rooms.size ? (
          [...rooms.entries()].map(([room, sensors]) => (
            <span
              key={room}
              className="rounded-md px-2 py-1 text-xs font-semibold text-white"
              style={{ backgroundColor: SENSOR_COLORS[sensors[0].type].fill }}
              title={sensors.map((s) => s.id).join(", ")}
            >
              {room}
            </span>
          ))
        ) : (
          <span className="text-sm text-muted">No movement right now</span>
        )}
      </p>
    </section>
  );
}

const VIEW_LABEL = "flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm";

/** Map options: sensor ids and reference vs SVG floor plan. */
export function MapOptions({
  home,
  showIds,
  onShowIds,
  planSource,
  onPlanSource,
}: {
  home: HomeEnvironment;
  showIds: boolean;
  onShowIds: (on: boolean) => void;
  planSource: "reference" | "svg";
  onPlanSource: (p: "reference" | "svg") => void;
}) {
  return (
    <div className="flex flex-wrap justify-end gap-2">
      <label className={`${VIEW_LABEL} cursor-pointer`}>
        <input
          type="checkbox"
          checked={showIds}
          onChange={(e) => onShowIds(e.target.checked)}
          className="accent-accent"
        />
        Sensor IDs
      </label>
      {home.floorPlan?.vectorSrc && (
        <label className={VIEW_LABEL}>
          Map
          <select
            value={planSource}
            onChange={(e) => onPlanSource(e.target.value as "reference" | "svg")}
            className="rounded border border-border bg-surface px-2 py-0.5 text-sm outline-none"
          >
            <option value="reference">Reference</option>
            <option value="svg">SVG</option>
          </select>
        </label>
      )}
    </div>
  );
}

export function withPlan(home: HomeEnvironment, planSource: "reference" | "svg"): HomeEnvironment {
  const fp = home.floorPlan;
  return planSource === "svg" && fp?.vectorSrc ? { ...home, floorPlan: { ...fp, src: fp.vectorSrc } } : home;
}
