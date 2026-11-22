"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Bell, CheckCircle2, Circle, Clock, Inbox, LayoutList, Pause, Play } from "lucide-react";
import { DayTimeline } from "@/components/DayTimeline";
import { useEnvironment } from "@/context/EnvironmentContext";
import { DAY_SECONDS, useReplayClock } from "@/hooks/useReplayClock";
import { api } from "@/lib/api";
import { activityColor } from "@/lib/caregiver";
import { secondsToTime } from "@/lib/sensorState";
import type { ReplayAlert, ReplayIndex, ReplayScenario } from "@/types/replay";

const NONE = "No_recognised_activity";
const END = DAY_SECONDS - 1;
const TONE = { notify: "high", summary: "medium", insight: "low" } as const;
const SPEEDS = [
  { value: 300, label: "5 min / s" },
  { value: 1200, label: "20 min / s" },
  { value: 3600, label: "1 h / s" },
];

function hhmm(s: number): string {
  return secondsToTime(s).slice(0, 5);
}

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

type Headline = { tone: "high" | "medium" | "ok"; text: string; detail: string };

function headline(sc: ReplayScenario): Headline {
  const notes = sc.alerts.filter((a) => a.tier === "notify" && a.delivered);
  if (notes.length) {
    return {
      tone: "high",
      text: notes.length === 1 ? "1 notification" : `${notes.length} notifications`,
      detail: notes[0].title,
    };
  }
  const summary = sc.alerts.filter((a) => a.tier === "summary" && a.delivered);
  if (summary.length) {
    return { tone: "medium", text: "In the evening summary", detail: summary[0].title };
  }
  return {
    tone: "ok",
    text: "All as usual",
    detail: sc.alerts.length ? "Small changes, noted on the dashboard" : "Nothing unusual",
  };
}

const DOT = { high: "bg-danger", medium: "bg-warning", ok: "bg-accent" } as const;

/** Past days: a report per day of what happened and what the caregiver was told.
 *  While the home is live, the days the live system has closed come first (D20),
 *  then the recorded days from before them. */
export default function PastDaysPage() {
  const { currentHome, live } = useEnvironment();
  const meta = currentHome.live ? live.feed.meta : null;
  const simId = meta?.simulation ?? null;
  const closedKey = (meta?.closedDays ?? []).map((c) => c.day).join(",");
  const [liveDays, setLiveDays] = useState<Record<string, ReplayScenario>>({});
  const requested = useRef(new Set<string>());
  const [index, setIndex] = useState<ReplayIndex | null>(null);
  const [days, setDays] = useState<Record<string, ReplayScenario>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [speed, setSpeed] = useState(1200);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .replayIndex()
      .catch(() => fetch("/replay/index.json").then((r) => (r.ok ? r.json() : Promise.reject())))
      .then(setIndex)
      .catch(() => setError("Past days are not available."));
  }, []);

  const refs = useMemo(() => index?.[currentHome.id]?.scenarios ?? [], [index, currentHome.id]);

  useEffect(() => {
    let live = true;
    Promise.all(
      refs.map((r) =>
        api
          .scenario(currentHome.id, r.id)
          .catch(() => fetch(`/replay/${r.file}`).then((x) => x.json()))
          .then((sc: ReplayScenario) => [r.id, sc] as const),
      ),
    )
      .then((pairs) => live && setDays(Object.fromEntries(pairs)))
      .catch(() => live && setError("Past days are not available."));
    return () => {
      live = false;
    };
  }, [refs, currentHome.id]);

  // Days the live session has closed, fetched once each.
  useEffect(() => {
    if (!simId || !closedKey) return;
    const todo = closedKey
      .split(",")
      .map((day) => `${simId}/${day}`)
      .filter((k) => !requested.current.has(k));
    if (!todo.length) return;
    todo.forEach((k) => requested.current.add(k));
    Promise.all(
      todo.map((k) =>
        api
          .simulationDay(simId, k.split("/")[1])
          .then((sc) => [k, sc] as const)
          .catch(() => {
            requested.current.delete(k);
            return null;
          }),
      ),
    ).then((pairs) => {
      const got = pairs.filter((x): x is readonly [string, ReplayScenario] => x !== null);
      if (got.length) setLiveDays((d) => ({ ...d, ...Object.fromEntries(got) }));
    });
  }, [simId, closedKey]);

  // One report per date, newest first. Where several recorded days share a date,
  // keep the untouched day, else the one with a notification, else the first.
  const ordered = useMemo(() => {
    const rank = (sc: ReplayScenario) =>
      sc.kind === "clean" ? 0 : sc.alerts.some((a) => a.tier === "notify" && a.delivered) ? 1 : 2;
    const byDate = new Map<string, (typeof refs)[number]>();
    for (const r of refs) {
      const sc = days[r.id];
      if (!sc) continue;
      const kept = byDate.get(sc.day);
      if (!kept || rank(sc) < rank(days[kept.id])) byDate.set(sc.day, r);
    }
    return [...byDate.values()].sort(
      (a, b) => Date.parse(days[b.id].day) - Date.parse(days[a.id].day),
    );
  }, [refs, days]);
  // While live: the closed live days, then recorded days from before the live week.
  const entries = useMemo(() => {
    const recorded = ordered.map((r) => ({ key: r.id, sc: days[r.id] }));
    if (!meta) return recorded;
    const closed = meta.closedDays ?? [];
    const firstDay = Date.parse(closed[0]?.dayLabel ?? meta.dayLabel);
    const fromLive = closed
      .map((c) => ({ key: `live/${c.day}`, sc: liveDays[`${meta.simulation}/${c.day}`] }))
      .filter((e) => e.sc)
      .reverse();
    return [...fromLive, ...recorded.filter((e) => Date.parse(e.sc.day) < firstDay)];
  }, [ordered, days, meta, liveDays]);
  const pick = entries.find((e) => e.key === selected) ?? entries[0] ?? null;
  const current = pick?.key ?? null;
  const sc = pick?.sc ?? null;

  if (!entries.length) {
    return (
      <p className="mx-auto max-w-6xl text-sm text-muted">
        {meta
          ? `Days appear here once they are over. ${meta.dayLabel} ends at midnight.`
          : (error ?? "Loading…")}
      </p>
    );
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-4 lg:grid-cols-[260px_1fr]">
      <ul className="space-y-2">
        {entries.map((e) => {
          const h = headline(e.sc);
          const on = e.key === current;
          return (
            <li key={e.key}>
              <button
                type="button"
                onClick={() => setSelected(e.key)}
                className={[
                  "w-full rounded-xl border p-3 text-left transition",
                  on ? "border-accent bg-accent-soft/60" : "border-border bg-surface hover:bg-surface-muted/50",
                ].join(" ")}
              >
                <p className="text-sm font-medium text-foreground">{e.sc.day}</p>
                <p className="mt-1 flex items-center gap-1.5 text-xs text-foreground">
                  <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[h.tone]}`} aria-hidden />
                  {h.text}
                </p>
                <p className="mt-0.5 truncate text-xs text-muted">{h.detail}</p>
              </button>
            </li>
          );
        })}
      </ul>
      {sc && current && (
        <DayReport key={`${currentHome.id}/${current}`} sc={sc} speed={speed} onSpeed={setSpeed} />
      )}
    </div>
  );
}

function DayReport({
  sc,
  speed,
  onSpeed,
}: {
  sc: ReplayScenario;
  speed: number;
  onSpeed: (s: number) => void;
}) {
  const { currentHome } = useEnvironment();
  const { seconds: t, playing, seek, togglePlay } = useReplayClock(speed, sc.day + sc.id, END);
  const labelOf = (raw: string) =>
    currentHome.activityClasses.find((c) => c.id === raw.toLowerCase())?.label ??
    raw.replace(/_/g, " ");
  const h = headline(sc);
  const whole = t >= END;
  const raised = sc.alerts.filter((a) => a.raisedAt <= t);

  const segments = sc.episodes
    .filter(([s, , i]) => s <= t && sc.labels[i] !== NONE)
    .map(([s, e, i]) => ({
      start: s,
      end: Math.min(e, t),
      label: labelOf(sc.labels[i]),
      color: activityColor(currentHome.activityClasses, sc.labels[i]),
    }));
  const markers = raised.map((a) => ({ t: a.raisedAt, tone: TONE[a.tier], title: a.title }));

  const ep = lastAtOrBefore(sc.episodes, t);
  const lastEvent = lastAtOrBefore(sc.events, t);
  const usual = (sc.usual[Math.floor(Math.min(t, END) / 1800)] ?? []).filter((u) => u !== NONE);
  const quiet = lastEvent && !whole ? t - lastEvent[0] : 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl font-semibold text-foreground">{sc.day}</h2>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-foreground">
            <span className={`h-2 w-2 rounded-full ${DOT[h.tone]}`} aria-hidden />
            {h.text}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              if (whole) seek(0);
              togglePlay();
            }}
            className="flex items-center gap-2 rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-accent-foreground transition hover:bg-accent-hover"
          >
            {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            {playing ? "Pause" : whole ? "Replay the day" : "Continue"}
          </button>
          {!whole && (
            <button
              type="button"
              onClick={() => {
                if (playing) togglePlay();
                seek(END);
              }}
              className="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm transition hover:bg-surface-muted"
            >
              Whole day
            </button>
          )}
          <select
            value={speed}
            onChange={(e) => onSpeed(Number(e.target.value))}
            className="rounded-lg border border-border bg-surface px-2 py-1.5 text-sm outline-none"
            aria-label="Replay speed"
          >
            {SPEEDS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
        <DayTimeline segments={segments} markers={markers} now={whole ? undefined : t} onSeek={seek} />
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted">
            {whole ? "End of the day" : `At ${hhmm(t)}`}
          </h3>
          {ep && sc.labels[ep[2]] !== NONE ? (
            <p className="mt-1 font-display text-xl font-semibold text-foreground">
              {labelOf(sc.labels[ep[2]])}
            </p>
          ) : (
            <p className="mt-1 text-sm text-muted">Not known</p>
          )}
          {!whole && usual.length > 0 && (
            <p className="mt-1 text-sm text-muted">Usually {usual.map(labelOf).join(" or ")} at this time</p>
          )}
          {quiet >= 30 * 60 && (
            <p className="mt-2 flex items-center gap-1.5 text-sm text-warning">
              <Clock className="h-4 w-4" /> No movement for {Math.round(quiet / 60)} min
            </p>
          )}
        </section>
        <DailyRoutine sc={sc} t={t} raised={raised} labelOf={labelOf} />
      </div>

      <WhatYouWereTold sc={sc} t={t} raised={raised} />
    </div>
  );
}

function DailyRoutine({
  sc,
  t,
  raised,
  labelOf,
}: {
  sc: ReplayScenario;
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
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted">Daily routine</h3>
      <ul className="mt-2 space-y-1.5 text-sm">
        {sc.daily.map((d) => {
          const li = sc.labels.indexOf(d.activity);
          const first = sc.episodes.find(([s, , i]) => i === li && s <= t);
          const missed = raised.some((a) => a.kind === "missed" && a.activity === d.activity);
          const late = !first && t > toSec(d.usualFirst);
          return (
            <li key={d.activity} className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-2">
                {first ? (
                  <CheckCircle2 className="h-4 w-4 text-accent" />
                ) : (
                  <Circle className={`h-4 w-4 ${missed ? "text-warning" : "text-muted"}`} />
                )}
                <span className={first ? "text-foreground" : "text-muted"}>{labelOf(d.activity)}</span>
              </span>
              <span className={`text-xs ${missed ? "font-medium text-warning" : "text-muted"}`}>
                {first
                  ? hhmm(first[0])
                  : missed
                    ? "missed"
                    : late
                      ? `usually by ${d.usualFirst}`
                      : `usually ~${d.usualFirst}`}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function WhatYouWereTold({
  sc,
  t,
  raised,
}: {
  sc: ReplayScenario;
  t: number;
  raised: ReplayAlert[];
}) {
  const sent = t >= sc.summaryAt;
  // How each alert reached the caregiver (decision D15); repeats held back are left out.
  const how = (a: ReplayAlert) => {
    if (a.tier === "notify") {
      return a.delivered
        ? { icon: <Bell className="h-3.5 w-3.5" />, label: "Notification", cls: "bg-danger-soft text-danger" }
        : null;
    }
    if (a.tier === "summary" && (a.delivered || !sent)) {
      return {
        icon: <Inbox className="h-3.5 w-3.5" />,
        label: sent ? `Evening summary ${hhmm(sc.summaryAt)}` : "For the evening summary",
        cls: "bg-warning-soft text-warning",
      };
    }
    return { icon: <LayoutList className="h-3.5 w-3.5" />, label: "Noted", cls: "bg-surface-muted text-muted" };
  };
  const items = raised.map((a) => ({ a, h: how(a) })).filter((x) => x.h !== null);

  return (
    <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-foreground">What you were told</h3>
      {items.length ? (
        <ul className="mt-3 divide-y divide-border">
          {items.map(({ a, h }, k) => (
            <li key={k} className="flex flex-wrap items-start gap-x-4 gap-y-1 py-3 text-sm first:pt-0 last:pb-0">
              <span className="w-12 shrink-0 tabular-nums text-muted">{hhmm(a.raisedAt)}</span>
              <div className="min-w-0 flex-1">
                <p className="font-medium text-foreground">{a.title}</p>
                <p className="mt-0.5 text-foreground">{a.observed}</p>
                <p className="mt-0.5 text-muted">{a.expected}</p>
              </div>
              <span className={`flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${h!.cls}`}>
                {h!.icon}
                {h!.label}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-muted">Nothing — the day went as usual.</p>
      )}
    </section>
  );
}
