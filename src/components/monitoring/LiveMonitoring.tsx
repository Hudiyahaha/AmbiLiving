"use client";

import { useEffect, useMemo, useState } from "react";
import { Bell, Pause, Play, RotateCcw } from "lucide-react";
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
import type { HomeEnvironment } from "@/types/home";

const BTN =
  "flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-foreground shadow-sm transition hover:bg-surface-muted disabled:opacity-50";
const LABEL = "flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm";
const SELECT = "rounded border border-border bg-surface px-2 py-1 text-sm outline-none";

const SPEEDS = [1, 10, 60, 300, 900];
const STARTS = [0, 6, 12, 18];

const STATUS_TEXT = {
  starting: "Starting",
  running: "Live",
  paused: "Paused",
  finished: "Day over",
  error: "Stopped",
} as const;

type PlanSource = "reference" | "svg";

function hhmm(sec: number) {
  return secondsToTime(sec).slice(0, 5);
}

/** Monitoring while a live feed runs (decision D19). Explanations live in Settings. */
export function LiveMonitoring({
  showIds,
  onShowIds,
}: {
  showIds: boolean;
  onShowIds: (on: boolean) => void;
}) {
  const { currentHome, live } = useEnvironment();
  const info = currentHome.live!;
  const { feed, controls } = live;
  const [scenarios, setScenarios] = useState<FeedScenario[]>([]);
  const [scenario, setScenario] = useState(info.scenario);
  const [startAt, setStartAt] = useState(DEFAULT_START);
  const [planSource, setPlanSource] = useState<PlanSource>("reference");

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

  const planHome = useMemo<HomeEnvironment>(() => {
    const fp = currentHome.floorPlan;
    if (planSource === "svg" && fp?.vectorSrc) {
      return { ...currentHome, floorPlan: { ...fp, src: fp.vectorSrc } };
    }
    return currentHome;
  }, [currentHome, planSource]);

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
  const dayOptions = scenarios.length
    ? scenarios
    : [{ id: info.scenario, title: info.title, day: info.dayLabel, kind: "" }];

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-accent">
            <span
              className={`h-1.5 w-1.5 rounded-full bg-accent ${running ? "animate-pulse" : "opacity-50"}`}
              aria-hidden
            />
            {STATUS_TEXT[info.status]}
          </p>
          <p className="font-display text-3xl font-semibold tabular-nums tracking-tight text-foreground">
            {formatClock(timestamp)}
          </p>
          <p className="mt-1 text-sm text-muted">{info.dayLabel}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className={`${LABEL} cursor-pointer`}>
            <input
              type="checkbox"
              checked={showIds}
              onChange={(e) => onShowIds(e.target.checked)}
              className="accent-accent"
            />
            Show sensor IDs
          </label>
          {currentHome.floorPlan?.vectorSrc && (
            <label className={LABEL}>
              Plan
              <select
                value={planSource}
                onChange={(e) => setPlanSource(e.target.value as PlanSource)}
                className={SELECT}
              >
                <option value="reference">Reference (exact)</option>
                <option value="svg">SVG recreation</option>
              </select>
            </label>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {info.status === "paused" ? (
          <button type="button" onClick={controls.resume} className={BTN}>
            <Play className="h-4 w-4" aria-hidden /> Resume
          </button>
        ) : (
          <button type="button" onClick={controls.pause} disabled={!running} className={BTN}>
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
            {(SPEEDS.includes(info.speed) ? SPEEDS : [...SPEEDS, info.speed]).map((s) => (
              <option key={s} value={s}>
                {s === 1 ? "Real time" : `${s}×`}
              </option>
            ))}
          </select>
        </label>
        <span className="mx-1 hidden h-6 w-px bg-border sm:block" aria-hidden />
        <label className={LABEL}>
          Day
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className={`${SELECT} max-w-[14rem]`}
          >
            {dayOptions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </label>
        <label className={LABEL}>
          From
          <select
            value={startAt}
            onChange={(e) => setStartAt(Number(e.target.value))}
            className={SELECT}
          >
            {STARTS.map((h) => (
              <option key={h} value={h * 3600}>
                {String(h).padStart(2, "0")}:00
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => controls.start({ scenario, startAt, speed: info.speed || DEFAULT_SPEED })}
          className={BTN}
        >
          <RotateCcw className="h-4 w-4" aria-hidden /> Play
        </button>
        {info.injected && (
          <span
            className="rounded-full bg-warning-soft px-2.5 py-1 text-xs font-medium text-warning"
            title={info.injected.note}
          >
            Test day · deviation inserted {hhmm(info.injected.start)}–{hhmm(info.injected.end)}
          </span>
        )}
      </div>

      {feed.error && (
        <p className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{feed.error}</p>
      )}

      <InteractiveFloorPlan home={planHome} timestamp={timestamp} showSensorIds={showIds} />

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
              <p className="mt-1 text-sm text-muted">Since {formatClock(episode.start)}</p>
            </>
          ) : (
            <p className="mt-1 text-sm text-muted">Not known yet.</p>
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
              <p className="mt-1 text-xs text-muted">{latestAlert.timestamp}</p>
            </>
          ) : (
            <p className="mt-1 text-sm text-muted">None today.</p>
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
      </section>
    </div>
  );
}
