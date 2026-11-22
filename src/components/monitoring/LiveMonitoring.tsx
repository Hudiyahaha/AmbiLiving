"use client";

import { useEffect, useMemo, useState } from "react";
import { Bell, ChevronDown, Pause, Play, RotateCcw } from "lucide-react";
import { InteractiveFloorPlan } from "@/components/floorplan/InteractiveFloorPlan";
import {
  MapOptions,
  MonitoringShell,
  RoomsCard,
  useMonitoringTab,
  withPlan,
} from "@/components/monitoring/MonitoringShell";
import { ActivitiesPanel, AlertsPanel } from "@/components/monitoring/MonitoringPanels";
import { useEnvironment } from "@/context/EnvironmentContext";
import { DEFAULT_SPEED, DEFAULT_START } from "@/hooks/useLiveFeed";
import { api, type FeedScenario } from "@/lib/api";
import {
  formatClock,
  getSensorStatesAtTime,
  isSensorVisuallyActive,
  secondsToTime,
} from "@/lib/sensorState";

const BTN =
  "flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm font-medium text-foreground transition hover:bg-surface-muted disabled:opacity-50";
const SELECT = "w-full rounded border border-border bg-surface px-2 py-1 text-sm outline-none";
const SPEEDS = [1, 10, 60, 300, 900, 3600];
const STATUS_TEXT = {
  starting: "Connecting",
  running: "Live",
  paused: "Paused",
  finished: "Day over",
  error: "Stopped",
} as const;
const TONE = { notify: "high", summary: "medium", insight: "low" } as const;

/** Monitoring while a live feed runs (decision D19). */
export function LiveMonitoring({
  showIds,
  onShowIds,
}: {
  showIds: boolean;
  onShowIds: (on: boolean) => void;
}) {
  const { currentHome, live } = useEnvironment();
  const info = currentHome.live!;
  const tab = useMonitoringTab();
  const [planSource, setPlanSource] = useState<"reference" | "svg">("svg");

  // 24:00 would read as noon on a 12-hour clock; a finished day ends at 23:59:59.
  const clock = Math.min(info.clock, 86399);
  const timestamp = secondsToTime(clock);
  const states = useMemo(
    () => getSensorStatesAtTime(currentHome.sensors, currentHome.events, timestamp),
    [currentHome.sensors, currentHome.events, timestamp],
  );
  const active = currentHome.sensors.filter((s) => isSensorVisuallyActive(s, states[s.id]));
  const episode = currentHome.activityHistory.at(-1) ?? null;
  const urgent = currentHome.anomalies.find((a) => a.requiresAttention) ?? null;
  const markers = live.feed.alerts.map((a) => ({ t: a.raisedAt, tone: TONE[a.tier], title: a.title }));
  const running = info.status === "running";

  return (
    <MonitoringShell
      home={currentHome}
      clock={formatClock(timestamp)}
      subtitle={info.dayLabel}
      status={
        <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-accent">
          <span
            className={`h-1.5 w-1.5 rounded-full bg-accent ${running ? "animate-pulse" : "opacity-50"}`}
            aria-hidden
          />
          {info.status === "finished" && info.days > 1 ? "Week over" : STATUS_TEXT[info.status]}
        </p>
      }
      actions={<PlaybackMenu />}
    >
      {live.feed.error && (
        <p className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{live.feed.error}</p>
      )}

      {tab === "home" && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
              <h2 className="text-xs font-medium uppercase tracking-wide text-muted">Now</h2>
              {episode ? (
                <>
                  <p className="mt-1 font-display text-xl font-semibold text-foreground">
                    {episode.label}
                  </p>
                  <p className="mt-0.5 text-sm text-muted">
                    since {formatClock(episode.start).replace(/:\d\d /, " ")}
                  </p>
                </>
              ) : (
                <p className="mt-1 text-sm text-muted">Not known yet</p>
              )}
            </section>
            <RoomsCard active={active} />
            <section
              className={`rounded-2xl border p-4 shadow-sm ${urgent ? "border-danger/30 bg-danger-soft" : "border-border bg-surface"}`}
            >
              <h2 className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted">
                <Bell className="h-3.5 w-3.5" aria-hidden /> Attention
              </h2>
              {urgent ? (
                <>
                  <p className="mt-1 font-medium text-danger">{urgent.title}</p>
                  <p className="mt-0.5 text-xs text-muted">{urgent.timestamp}</p>
                </>
              ) : (
                <p className="mt-1 font-medium text-foreground">All as usual</p>
              )}
            </section>
          </div>
          <MapOptions
            home={currentHome}
            showIds={showIds}
            onShowIds={onShowIds}
            planSource={planSource}
            onPlanSource={setPlanSource}
          />
          <InteractiveFloorPlan
            home={withPlan(currentHome, planSource)}
            timestamp={timestamp}
            showSensorIds={showIds}
          />
        </div>
      )}
      {tab === "activities" && <ActivitiesPanel home={currentHome} now={clock} markers={markers} />}
      {tab === "alerts" && <AlertsPanel home={currentHome} />}
    </MonitoringShell>
  );
}

/** Demo controls (which recorded day, speed, pause), out of the caregiver's way. */
function PlaybackMenu() {
  const { currentHome, live } = useEnvironment();
  const info = currentHome.live!;
  const { controls } = live;
  const [open, setOpen] = useState(false);
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

  const days = scenarios.length
    ? scenarios
    : [{ id: info.scenario, title: info.title, day: info.dayLabel, kind: "", days: info.days }];

  return (
    <div className="relative flex items-center gap-2">
      {info.status === "paused" ? (
        <button type="button" onClick={controls.resume} className={BTN} aria-label="Resume">
          <Play className="h-4 w-4" aria-hidden />
        </button>
      ) : (
        <button
          type="button"
          onClick={controls.pause}
          disabled={info.status !== "running"}
          className={BTN}
          aria-label="Pause"
        >
          <Pause className="h-4 w-4" aria-hidden />
        </button>
      )}
      <button type="button" onClick={() => setOpen((o) => !o)} className={BTN} aria-expanded={open}>
        Playback {info.speed === 1 ? "" : `· ${info.speed}×`}
        <ChevronDown className="h-4 w-4" aria-hidden />
      </button>
      {open && (
        <div className="absolute right-0 top-full z-20 mt-2 w-72 space-y-3 rounded-xl border border-border bg-surface p-4 text-sm shadow-lg">
          <label className="block">
            <span className="text-xs text-muted">Speed</span>
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
          <div className="border-t border-border pt-3">
            <p className="text-xs font-medium text-foreground">Start again</p>
            <label className="mt-2 block">
              <span className="text-xs text-muted">Recording</span>
              <select value={scenario} onChange={(e) => setScenario(e.target.value)} className={SELECT}>
                {days.map((s) => (
                  <option key={s.id} value={s.id}>
                    {(s.days ?? 1) > 1 ? `${s.title} · ${s.day}` : `${s.day} · ${s.title}`}
                  </option>
                ))}
              </select>
            </label>
            <label className="mt-2 block">
              <span className="text-xs text-muted">{(scenarios.find((s) => s.id === scenario)?.days ?? 1) > 1 ? "First day from" : "From"}</span>
              <select
                value={startAt}
                onChange={(e) => setStartAt(Number(e.target.value))}
                className={SELECT}
              >
                {[0, 6, 12, 18].map((h) => (
                  <option key={h} value={h * 3600}>
                    {String(h).padStart(2, "0")}:00
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() => {
                controls.start({ scenario, startAt, speed: info.speed || DEFAULT_SPEED });
                setOpen(false);
              }}
              className={`${BTN} mt-3 w-full justify-center`}
            >
              <RotateCcw className="h-4 w-4" aria-hidden /> Play
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
