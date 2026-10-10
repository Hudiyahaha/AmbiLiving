"use client";

import { useEnvironment } from "@/context/EnvironmentContext";

export default function HomesPage() {
  const { homes, currentHome, setHomeId } = useEnvironment();

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <p className="text-sm text-muted">
        CASAS smart-home environments available in this PoC. Switching updates
        floor plan, sensors, activities, and anomalies across the app.
      </p>

      <ul className="grid gap-4 md:grid-cols-2">
        {homes.map((home) => {
          const selected = home.id === currentHome.id;
          const stats = home.datasetStats;

          return (
            <li key={home.id}>
              <button
                type="button"
                onClick={() => setHomeId(home.id)}
                className={[
                  "w-full overflow-hidden rounded-2xl border bg-surface text-left shadow-sm transition",
                  selected
                    ? "border-accent ring-2 ring-accent/20"
                    : "border-border hover:border-accent/40",
                ].join(" ")}
              >
                {home.floorPlan && (
                  <div className="border-b border-border bg-surface-muted/30 p-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={home.floorPlan.src}
                      alt=""
                      className="mx-auto h-36 w-auto object-contain"
                    />
                  </div>
                )}
                <div className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="font-display text-lg font-semibold text-foreground">
                      {home.name}
                    </h2>
                    <span className="rounded-md bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent">
                      Active
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-muted">{home.summary}</p>
                  <dl className="mt-4 grid grid-cols-2 gap-3 text-xs text-muted">
                    <div>
                      <dt className="font-medium text-foreground">Residents</dt>
                      <dd>{home.residentLabel}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-foreground">Sensors</dt>
                      <dd>{home.sensors.length}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-foreground">
                        Activity classes
                      </dt>
                      <dd>{home.activityClasses.length}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-foreground">
                        Annotated instances
                      </dt>
                      <dd>
                        {stats
                          ? stats.activityInstances.toLocaleString()
                          : "—"}
                      </dd>
                    </div>
                    {stats && (
                      <div className="col-span-2">
                        <dt className="font-medium text-foreground">Dataset</dt>
                        <dd>{stats.dataPeriod}</dd>
                      </div>
                    )}
                  </dl>
                  <div className="mt-4">
                    <p className="text-xs font-medium text-foreground">
                      Activity classes
                    </p>
                    <p className="mt-1.5 flex flex-wrap gap-1">
                      {home.activityClasses.map((c) => (
                        <span
                          key={c.id}
                          className="rounded-md bg-surface-muted px-1.5 py-0.5 text-[10px] text-muted"
                        >
                          {c.label}
                        </span>
                      ))}
                    </p>
                  </div>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
