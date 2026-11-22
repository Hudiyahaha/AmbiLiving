"use client";

import { useEffect, useMemo, useState } from "react";
import { Bell, Pause, Play, Radio, RotateCcw } from "lucide-react";
import { InteractiveFloorPlan } from "@/components/floorplan/InteractiveFloorPlan";
import { useEnvironment } from "@/context/EnvironmentContext";
import { DEFAULT_SPEED, DEFAULT_START } from "@/hooks/useLiveFeed";
import { api, type FeedScenario } from "@/lib/api";
import { SENSOR_COLORS } from "@/lib/sensorColors";
import {
  formatClock,
  getSensorStatesAtTime,
  isSensorVisuallyActive,
  secondsToTime,
} from "@/lib/sensorState";

const BTN =
  "flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-foreground shadow-sm transition hover:bg-surface-muted";
const LABEL = "flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm";
const SELECT = "rounded border border-border bg-surface px-2 py-1 text-sm outline-none";

const SPEEDS = [
  { value: 1, label: "Real time" },
  { value: 10, label: "10×" },
  { value: 60, label: "60× (1 min / s)" },
  { value: 300, label: "300× (5 min / s)" },
  { value: 900, label: "900× (15 min / s)" },
];

const STARTS = [0, 6, 12, 18].map((h) => ({ value: h * 3600, label: `${String(h).padStart(2, "0")}:00` }));

const STATUS_TEXT = {
  starting: "Starting…",
  running: "Live",
  paused: "Paused",
  finished: "Day finished",
  error: "Stopped by an error",
} as const;

function hhmm(sec: number) {
  return secondsToTime(sec).slice(0, 5);
}

/**
 * Monitoring while a live feed runs: the floor plan, current activity and alerts
 * follow the simulated clock (decision D19).
 */
export function LiveMonitoring({ showIds }: { showIds: boolean }) {
  const { currentHome, live } = useEnvironment();
  const info = currentHome.live!;
  const { feed, controls } = live;
  const [scenarios, setScenarios] = useState<FeedScenario[]>([]);
  const [scenario, setScenario] = useState(info.scenario);
  const [startAt, setStartAt] = useState(DEFAULT_START);

  useEffect(() => {
    let ok = true;
    api
      .feeds(currentHome.id)
      .then((s) => ok && setScenarios(s))
      .catch(() => undefined);
    return () => {
      ok = false;
    };
  }, [currentHome.id]);

  // 24:00 would read as noon on a 12-hour clock; a finished day ends at 23:59:59.
  const timestamp = secondsToTime(Math.min(info.clock, 86399));
  const states = useMemo(
    () => getSensorStatesAtTime(currentHome.sensors, currentHome.events, timestamp),
    [currentHome.sensors, currentHome.events, timestamp],
  );
  const activeSensors = currentHome.sensors.filter((s) =>
    isSensorVisuallyActive(s, states[s.id]),
  );
  const episode = currentHome.activityHistory.at(-1) ?? null;
  const latestAlert = currentHome.anomalies[0] ?? null;
  const recent = currentHome.events.slice(-8).reverse();
  const running = info.status === "running";

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-accent">
            <Radio className={`h-3.5 w-3.5 ${running ? "animate-pulse" : ""}`} aria-hidden />
            {STATUS_TEXT[info.status]} · {info.speed === 1 ? "real time" : `${info.speed}×`}
          </p>
          <p className="font-display text-3xl font-semibold tabular-nums tracking-tight text-foreground">
            {formatClock(timestamp)}
          </p>
          <p className="mt-1 text-sm text-muted">
            {info.title} — {info.dayLabel}, played as a live sensor feed.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {info.status === "paused" ? (
            <button type="button" onClick={controls.resume} className={BTN}>
              <Play className="h-4 w-4" aria-hidden /> Resume
            </button>
          ) : (
            <button
              type="button"
              onClick={controls.pause}
              disabled={!running}
              className={`${BTN} disabled:opacity-50`}
            >
              <Pause className="h-4 w-4" aria-hidden /> Pause
            </button>
          )}
          <label className={LABEL}>
            Speed
            <select
              value={info.speed}
              onChange={(e) => controls.setSpeed(Number(e.target.value))}
              className={SELECT}
            >
              {SPEEDS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
              {!SPEEDS.some((s) => s.value === info.speed) && (
                <option value={info.speed}>{info.speed}×</option>
              )}
            </select>
          </label>
        </div>
      </div>

      <section className="flex flex-wrap items-end gap-2 rounded-2xl border border-border bg-surface p-3 shadow-sm">
        <label className={LABEL}>
          Day
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className={`${SELECT} max-w-[16rem]`}
          >
            {(scenarios.length ? scenarios : [{ id: info.scenario, title: info.title, day: info.dayLabel, kind: "" }]).map(
              (s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ),
            )}
          </select>
        </label>
        <label className={LABEL}>
          From
          <select
            value={startAt}
            onChange={(e) => setStartAt(Number(e.target.value))}
            className={SELECT}
          >
            {STARTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => controls.start({ scenario, startAt, speed: info.speed || DEFAULT_SPEED })}
          className={BTN}
        >
          <RotateCcw className="h-4 w-4" aria-hidden /> Play this day
        </button>
        <button
          type="button"
          onClick={() => live.setEnabled(false)}
          className="ml-auto text-xs text-muted underline-offset-2 hover:underline"
        >
          Show the exported day instead
        </button>
      </section>

      {info.injected && (
        <p className="rounded-lg bg-warning-soft px-3 py-2 text-sm text-warning">
          Test day: a deviation was inserted into the raw sensor events — {info.injected.note} (
          {hhmm(info.injected.start)}–{hhmm(info.injected.end)}). The pipeline is not told.
        </p>
      )}
      {feed.error && (
        <p className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{feed.error}</p>
      )}

      <InteractiveFloorPlan home={currentHome} timestamp={timestamp} showSensorIds={showIds} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
          <h2 className="text-xs font-medium uppercase tracking-wide text-muted">
            Current activity
          </h2>
          {episode ? (
            <>
              <p className="mt-1 font-display text-xl font-semibold text-foreground">
                {episode.label}
              </p>
              <p className="mt-1 text-sm text-muted">
                Since {formatClock(episode.start)} · mean confidence{" "}
                {Math.round(episode.confidence * 100)}%
              </p>
              {info.latest && info.latest.activityId !== episode.activityId && (
                <p className="mt-1 text-xs text-muted">
                  Latest window says {info.latest.label} (
                  {Math.round(info.latest.confidence * 100)}%), not yet a new activity.
                </p>
              )}
            </>
          ) : (
            <p className="mt-1 text-sm text-muted">
              Waiting for the first 100 sensor events of the day.
            </p>
          )}
        </section>

        <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
          <h2 className="text-xs font-medium uppercase tracking-wide text-muted">
            Active sensors
          </h2>
          <p className="mt-2 flex flex-wrap gap-2">
            {activeSensors.length > 0 ? (
              activeSensors.map((sensor) => (
                <span
                  key={sensor.id}
                  className="rounded-md px-2 py-1 text-xs font-semibold text-white"
                  style={{ backgroundColor: SENSOR_COLORS[sensor.type].fill }}
                >
                  {sensor.id}
                </span>
              ))
            ) : (
              <span className="text-sm text-muted">None</span>
            )}
          </p>
        </section>

        <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
          <h2 className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted">
            <Bell className="h-3.5 w-3.5" aria-hidden /> Latest deviation
          </h2>
          {latestAlert ? (
            <>
              <p className="mt-1 font-medium text-foreground">{latestAlert.title}</p>
              <p className="mt-1 text-sm text-muted">{latestAlert.observed}</p>
              <p className="mt-1 text-xs text-muted">
                {latestAlert.timestamp} · {latestAlert.delivery}
              </p>
            </>
          ) : (
            <p className="mt-1 text-sm text-muted">None so far today.</p>
          )}
        </section>
      </div>

      <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
        <h2 className="text-xs font-medium uppercase tracking-wide text-muted">
          Latest sensor events
        </h2>
        {recent.length ? (
          <ul className="mt-2 grid gap-1 font-mono text-xs text-foreground sm:grid-cols-2">
            {recent.map((e, i) => (
              <li key={`${e.timestamp}-${e.sensorId}-${i}`} className="flex gap-3">
                <span className="tabular-nums text-muted">{e.timestamp}</span>
                <span className="font-semibold">{e.sensorId}</span>
                <span>{String(e.state)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-muted">No events yet.</p>
        )}
        <p className="mt-3 text-xs text-muted">
          {info.recogniser}; {info.episodeRule}. Routine learned from {info.routineLearnedFrom};
          checked every 2 minutes of the day.
        </p>
      </section>
    </div>
  );
}
