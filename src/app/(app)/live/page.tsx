"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bell,
  CheckCircle2,
  Circle,
  Clock,
  FastForward,
  Inbox,
  LayoutList,
  Pause,
  Play,
  RotateCcw,
} from "lucide-react";
import { InteractiveFloorPlan } from "@/components/floorplan/InteractiveFloorPlan";
import { useEnvironment } from "@/context/EnvironmentContext";
import { DAY_SECONDS, useReplayClock } from "@/hooks/useReplayClock";
import { api } from "@/lib/api";
import { secondsToTime } from "@/lib/sensorState";
import type { SensorEvent, SensorStateValue } from "@/types/home";
import type {
  ReplayAlert,
  ReplayHome,
  ReplayIndex,
  ReplayScenario,
} from "@/types/replay";

const NONE = "No_recognised_activity";
const SPEEDS = [
  { value: 60, label: "1 min / s" },
  { value: 300, label: "5 min / s" },
  { value: 1200, label: "20 min / s" },
];
const PALETTE = [
  "#3f6b52", "#9a6b2f", "#4f6d8f", "#9b4d3c", "#6b5b8f", "#2f7f7a",
  "#8f6b4f", "#5f7f2f", "#8f4f6f", "#4f8f5f", "#7a6a2f", "#2f5f8f",
  "#8f2f4f", "#5f5f5f", "#3f8f8f",
];

function clock(s: number): string {
  return secondsToTime(s).slice(0, 5);
}

/** Last item whose first field is <= t (items sorted by it). */
function lastAtOrBefore<T extends number[]>(items: T[], t: number): T | null {
  let lo = 0;
  let hi = items.length - 1;
  let best = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (items[mid][0] <= t) {
      best = mid;
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return best >= 0 ? items[best] : null;
}

export default function LiveDemoPage() {
  const { currentHome } = useEnvironment();
  const [index, setIndex] = useState<ReplayIndex | null>(null);
  const [scenarioId, setScenarioId] = useState("normal");
  const [loaded, setLoaded] = useState<{ file: string; data: ReplayScenario } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [speed, setSpeed] = useState(300);

  const home: ReplayHome | undefined = index?.[currentHome.id];
  const ref = home?.scenarios.find((s) => s.id === scenarioId) ?? home?.scenarios[0];

  // From the backend API when it runs, else the files bundled in public/replay/.
  useEffect(() => {
    api
      .replayIndex()
      .catch(() =>
        fetch("/replay/index.json").then((r) =>
          r.ok ? r.json() : Promise.reject(new Error(r.statusText)),
        ),
      )
      .then(setIndex)
      .catch(() => setError("Replay data not found. Run `python -m har.replay` in ml/."));
  }, []);

  const file = ref?.file;
  const refId = ref?.id;
  const homeId = currentHome.id;
  const scenario = loaded && loaded.file === file ? loaded.data : null;

  useEffect(() => {
    if (!file || !refId) return;
    let live = true;
    api
      .scenario(homeId, refId)
      .catch(() =>
        fetch(`/replay/${file}`).then((r) =>
          r.ok ? r.json() : Promise.reject(new Error(r.statusText)),
        ),
      )
      .then((data: ReplayScenario) => live && setLoaded({ file, data }))
      .catch(() => live && setError(`Could not load ${file}.`));
    return () => {
      live = false;
    };
  }, [file, homeId, refId]);

  const { seconds: t, playing, seek, togglePlay } = useReplayClock(
    speed,
    `${currentHome.id}/${ref?.id ?? ""}`,
  );

  const labelOf = useMemo(() => {
    const classes = currentHome.activityClasses;
    return (raw: string) =>
      raw === NONE
        ? "No recognised activity"
        : classes.find((c) => c.id === raw.toLowerCase())?.label ??
          raw.replace(/_/g, " ");
  }, [currentHome.activityClasses]);

  const events: SensorEvent[] = useMemo(
    () =>
      scenario?.events.map(([s, si, st]) => ({
        timestamp: secondsToTime(s),
        sensorId: scenario.sensors[si],
        state: scenario.states[st] as SensorStateValue,
      })) ?? [],
    [scenario],
  );
  const planHome = useMemo(() => ({ ...currentHome, events }), [currentHome, events]);

  if (currentHome.status === "placeholder") {
    return (
      <p className="mx-auto max-w-6xl rounded-lg bg-warning-soft px-3 py-2 text-sm text-warning">
        This environment is a placeholder. Switch to Aruba or Milan for the live demo.
      </p>
    );
  }
  if (error) {
    return (
      <p className="mx-auto max-w-6xl rounded-lg bg-warning-soft px-3 py-2 text-sm text-warning">
        {error}
      </p>
    );
  }
  if (!home || !ref) {
    return <p className="mx-auto max-w-6xl text-sm text-muted">Loading replays…</p>;
  }

  const raised = scenario?.alerts.filter((a) => a.raisedAt <= t) ?? [];
  const pred = scenario ? lastAtOrBefore(scenario.predictions, t) : null;
  const lastEvent = scenario ? lastAtOrBefore(scenario.events, t) : null;
  const annotated = scenario?.annotations.find(([s, e]) => s <= t && t < e) ?? null;
  const usual = scenario?.usual[Math.floor(t / 1800)] ?? [];
  const latestNotify = [...raised]
    .reverse()
    .find((a) => a.tier === "notify" && a.delivered && t - a.raisedAt < 30 * 60);
  const jumpTo = scenario?.injected
    ? scenario.injected.start - 15 * 60
    : (scenario?.alerts[0]?.raisedAt ?? 8 * 3600) - 30 * 60;

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {/* Clock and controls */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-display text-3xl font-semibold tabular-nums tracking-tight text-foreground">
            {secondsToTime(t)}
          </p>
          <p className="mt-1 text-sm text-muted">{scenario?.day ?? ref.day}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={togglePlay}
            disabled={!scenario}
            className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition hover:bg-accent-hover disabled:opacity-50"
          >
            {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            {playing ? "Pause" : "Play"}
          </button>
          <button
            type="button"
            onClick={() => seek(Math.max(jumpTo, 0))}
            disabled={!scenario}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm transition hover:bg-surface-muted disabled:opacity-50"
          >
            <FastForward className="h-4 w-4" />
            {scenario?.injected ? "Jump to the deviation" : "Jump to first alert"}
          </button>
          <button
            type="button"
            onClick={() => seek(0)}
            className="rounded-lg border border-border bg-surface p-2 transition hover:bg-surface-muted"
            aria-label="Back to midnight"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
          <label className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm">
            Speed
            <select
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              className="rounded border border-border bg-surface px-2 py-1 text-sm outline-none"
            >
              {SPEEDS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {/* Scenario picker */}
      <div className="flex flex-wrap gap-2">
        {home.scenarios.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setScenarioId(s.id)}
            className={[
              "rounded-full border px-3 py-1.5 text-sm transition",
              s.id === ref.id
                ? "border-accent bg-accent-soft font-medium text-accent"
                : "border-border bg-surface text-muted hover:text-foreground",
            ].join(" ")}
          >
            {s.title}
          </button>
        ))}
      </div>

      {scenario && <ScenarioNote scenario={scenario} labelOf={labelOf} />}

      {latestNotify && (
        <div
          role="status"
          className="flex items-start gap-3 rounded-2xl border border-danger/30 bg-danger-soft px-4 py-3"
        >
          <Bell className="mt-0.5 h-5 w-5 shrink-0 text-danger" />
          <div>
            <p className="text-sm font-semibold text-danger">
              Notification sent to the caregiver at {clock(latestNotify.raisedAt)}
            </p>
            <p className="mt-0.5 text-sm text-foreground">
              {latestNotify.title}. {latestNotify.observed}.
            </p>
          </div>
        </div>
      )}

      {scenario && (
        <DayStrip scenario={scenario} t={t} raised={raised} onSeek={seek} labelOf={labelOf} />
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <InteractiveFloorPlan home={planHome} timestamp={secondsToTime(t)} />

        <div className="space-y-4">
          <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
            <h2 className="text-xs font-medium uppercase tracking-wide text-muted">
              Live recogniser says
            </h2>
            {pred && scenario ? (
              <>
                <p className="mt-1 font-display text-xl font-semibold text-foreground">
                  {labelOf(scenario.labels[pred[1]])}
                </p>
                <p className="mt-0.5 text-sm text-muted">
                  Confidence {Math.round(pred[2] * 100)}% · predicted at {clock(pred[0])}
                </p>
              </>
            ) : (
              <p className="mt-1 text-sm text-muted">No prediction yet today.</p>
            )}
            {lastEvent && t - lastEvent[0] >= 10 * 60 && (
              <p className="mt-2 flex items-center gap-1.5 text-sm text-warning">
                <Clock className="h-4 w-4" />
                No sensor event for {Math.round((t - lastEvent[0]) / 60)} min
              </p>
            )}
            <dl className="mt-3 space-y-1.5 border-t border-border pt-3 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Usually at this time</dt>
                <dd className="text-right text-foreground">
                  {usual.map(labelOf).join(" or ") || "–"}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Dataset annotation</dt>
                <dd className="text-right text-foreground">
                  {annotated && scenario ? labelOf(scenario.labels[annotated[2]]) : "None"}
                </dd>
              </div>
            </dl>
          </section>

          {scenario && <DailyChecklist scenario={scenario} t={t} raised={raised} labelOf={labelOf} />}
        </div>
      </div>

      {scenario && <CaregiverView scenario={scenario} t={t} raised={raised} />}

    </div>
  );
}

function ScenarioNote({
  scenario,
  labelOf,
}: {
  scenario: ReplayScenario;
  labelOf: (raw: string) => string;
}) {
  const inj = scenario.injected;
  if (!inj) return null;
  return (
    <p className="text-xs">
      <span
        className="rounded-full bg-warning-soft px-2.5 py-1 font-medium text-warning"
        title={inj.note.replace(/_/g, " ")}
      >
        Test day · {inj.target ? `${labelOf(inj.target)}: ` : ""}
        {inj.note.replace(/_/g, " ")}
      </span>
    </p>
  );
}

function DayStrip({
  scenario,
  t,
  raised,
  onSeek,
  labelOf,
}: {
  scenario: ReplayScenario;
  t: number;
  raised: ReplayAlert[];
  onSeek: (s: number) => void;
  labelOf: (raw: string) => string;
}) {
  const W = 1440;
  const x = (s: number) => (s / DAY_SECONDS) * W;
  const colour = (i: number) =>
    scenario.labels[i] === NONE ? "#c9c9c4" : PALETTE[i % PALETTE.length];
  const row = (items: [number, number, number][], y: number) =>
    items
      .filter(([s]) => s <= t)
      .map(([s, e, i]) => (
        <rect key={`${y}-${s}`} x={x(s)} y={y} width={Math.max(x(Math.min(e, t)) - x(s), 1)} height={16} fill={colour(i)}>
          <title>
            {labelOf(scenario.labels[i])} {clock(s)}–{clock(Math.min(e, t))}
          </title>
        </rect>
      ));
  const tierColour = { notify: "var(--danger)", summary: "var(--warning)", insight: "#8a8a85" };
  const seen = new Set<number>();
  for (const [, , i] of scenario.episodes) if (scenario.labels[i] !== NONE) seen.add(i);

  return (
    <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
      <svg
        viewBox={`0 0 ${W} 96`}
        className="w-full cursor-pointer"
        role="img"
        aria-label="Day timeline"
        onClick={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          onSeek(((e.clientX - r.left) / r.width) * DAY_SECONDS);
        }}
      >
        {scenario.injected && (
          <rect
            x={x(scenario.injected.start)}
            y={0}
            width={Math.max(x(scenario.injected.end) - x(scenario.injected.start), 3)}
            height={64}
            fill="var(--danger)"
            opacity={0.12}
          />
        )}
        {row(scenario.episodes, 8)}
        {row(scenario.annotations, 40)}
        {raised.map((a, k) => (
          <g key={k}>
            <line x1={x(a.raisedAt)} x2={x(a.raisedAt)} y1={2} y2={62} stroke={tierColour[a.tier]} strokeWidth={2} />
            <circle cx={x(a.raisedAt)} cy={4} r={5} fill={tierColour[a.tier]} />
          </g>
        ))}
        {[0, 3, 6, 9, 12, 15, 18, 21].map((h) => (
          <text key={h} x={x(h * 3600) + 2} y={88} fontSize={13} fill="#8a8a85">
            {String(h).padStart(2, "0")}:00
          </text>
        ))}
        <line x1={x(t)} x2={x(t)} y1={0} y2={72} stroke="var(--foreground, #222)" strokeWidth={2} />
      </svg>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span>Top row: live recogniser · bottom row: dataset annotation</span>
        {scenario.injected && (
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-danger/20" /> injected deviation
          </span>
        )}
        <span className="flex items-center gap-1">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-danger" /> notification
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-warning" /> evening summary
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#8a8a85]" /> dashboard only
        </span>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
        {[...seen].map((i) => (
          <span key={i} className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: colour(i) }} />
            {labelOf(scenario.labels[i])}
          </span>
        ))}
      </div>
    </section>
  );
}

function DailyChecklist({
  scenario,
  t,
  raised,
  labelOf,
}: {
  scenario: ReplayScenario;
  t: number;
  raised: ReplayAlert[];
  labelOf: (raw: string) => string;
}) {
  const toSec = (hm: string) => {
    const [h, m] = hm.split(":").map(Number);
    return h * 3600 + m * 60;
  };
  return (
    <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
      <h2 className="text-xs font-medium uppercase tracking-wide text-muted">
        Daily routine so far
      </h2>
      <ul className="mt-2 space-y-1.5 text-sm">
        {scenario.daily.map((d) => {
          const li = scenario.labels.indexOf(d.activity);
          const first = scenario.episodes.find(([s, , i]) => i === li && s <= t);
          const flagged = raised.some((a) => a.kind === "missed" && a.activity === d.activity);
          const late = !first && t > toSec(d.usualFirst);
          return (
            <li key={d.activity} className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-2">
                {first ? (
                  <CheckCircle2 className="h-4 w-4 text-accent" />
                ) : (
                  <Circle className={`h-4 w-4 ${flagged ? "text-warning" : "text-muted"}`} />
                )}
                <span className={first ? "text-foreground" : "text-muted"}>{labelOf(d.activity)}</span>
              </span>
              <span className={`text-xs ${flagged ? "font-medium text-warning" : "text-muted"}`}>
                {first
                  ? `at ${clock(first[0])}`
                  : flagged
                    ? "flagged as missed"
                    : late
                      ? `not yet · usually by ${d.usualFirst}`
                      : `usually ~${d.usualFirst}`}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function AlertCard({ a }: { a: ReplayAlert }) {
  return (
    <li className="rounded-xl bg-surface-muted/50 p-3 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-medium text-foreground">{a.title}</p>
        <span className="text-xs text-muted">{clock(a.raisedAt)}</span>
      </div>
      <p className="mt-1 text-foreground">{a.observed}</p>
      <p className="mt-0.5 text-muted">{a.expected}</p>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {a.explainsInjection && (
          <span className="rounded-md bg-accent-soft px-1.5 py-0.5 text-xs text-accent">
            matches the injected deviation
          </span>
        )}
        {a.tier === "notify" && !a.delivered && (
          <span className="rounded-md border border-border px-1.5 py-0.5 text-xs text-muted">
            repeat within 2 h, not re-sent
          </span>
        )}
      </div>
    </li>
  );
}

function CaregiverView({
  scenario,
  t,
  raised,
}: {
  scenario: ReplayScenario;
  t: number;
  raised: ReplayAlert[];
}) {
  const notes = raised.filter((a) => a.tier === "notify");
  const summary = raised.filter((a) => a.tier === "summary");
  const insights = raised.filter((a) => a.tier === "insight");
  const sent = t >= scenario.summaryAt;
  const inSummary = summary.filter((a) => a.inSummary);
  const later = summary.filter((a) => a.raisedAt > scenario.summaryAt);

  const column = (
    icon: React.ReactNode,
    title: string,
    sub: string,
    items: ReplayAlert[],
    empty: string,
  ) => (
    <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">
        {icon}
        {title}
      </h2>
      <p className="mt-0.5 text-xs text-muted">{sub}</p>
      {items.length ? (
        <ul className="mt-3 space-y-2">
          {items.map((a, k) => (
            <AlertCard key={k} a={a} />
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-muted">{empty}</p>
      )}
    </section>
  );

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {column(
        <Bell className="h-4 w-4 text-danger" />,
        "Notifications",
        "Pushed at once: possible emergencies",
        notes,
        "None so far today.",
      )}
      {column(
        <Inbox className="h-4 w-4 text-warning" />,
        sent ? `Evening summary, sent ${clock(scenario.summaryAt)}` : "Evening summary",
        sent
          ? `${inSummary.length} of ${summary.length - later.length} items (at most 3)`
          : `Sent at ${clock(scenario.summaryAt)}; ${summary.length} item${summary.length === 1 ? "" : "s"} waiting`,
        sent ? [...inSummary, ...later] : summary,
        "Nothing for the summary yet.",
      )}
      {column(
        <LayoutList className="h-4 w-4 text-muted" />,
        "Dashboard only",
        "Differences worth seeing, not worth a message",
        insights,
        "None so far today.",
      )}
    </div>
  );
}
