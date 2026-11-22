"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type LiveAlert,
  type LiveCurrent,
  type LiveEpisode,
  type LiveEvent,
  type LivePrediction,
  type SimulationMeta,
  type SimulationSnapshot,
  type SimulationTick,
} from "@/lib/api";

/**
 * Follows a simulated live home (decision D19): the backend plays a recorded day
 * into a live session and streams what the live pipeline produces. One simulation
 * per home; its id is kept in sessionStorage so a page reload re-attaches to it.
 */

export interface LiveFeed {
  meta: SimulationMeta | null;
  /** True once the day so far has been received */
  ready: boolean;
  events: LiveEvent[];
  predictions: LivePrediction[];
  episodes: LiveEpisode[];
  alerts: LiveAlert[];
  current: LiveCurrent | null;
  /** Alert ids raised while this page was open, newest last */
  newAlertIds: string[];
  /** Why the feed could not start or continue */
  error: string | null;
}

export interface LiveFeedControls {
  start: (options?: { scenario?: string; speed?: number; startAt?: number }) => void;
  pause: () => void;
  resume: () => void;
  setSpeed: (speed: number) => void;
}

export const DEFAULT_SPEED = 60;
export const DEFAULT_START = 6 * 3600;

export const EMPTY_FEED: LiveFeed = {
  meta: null,
  ready: false,
  events: [],
  predictions: [],
  episodes: [],
  alerts: [],
  current: null,
  newAlertIds: [],
  error: null,
};

/** Feed state belongs to one home and one simulation. */
interface State {
  home: string;
  simId: string | null;
  /** Bumped on every (re)attach, so the stream reconnects even to the same simulation */
  epoch: number;
  feed: LiveFeed;
}

const storageKey = (home: string) => `ambiliving.simulation.${home}`;

function readStored(home: string): string | null {
  try {
    return window.sessionStorage.getItem(storageKey(home));
  } catch {
    return null;
  }
}

function writeStored(home: string, id: string | null) {
  try {
    if (id) window.sessionStorage.setItem(storageKey(home), id);
    else window.sessionStorage.removeItem(storageKey(home));
  } catch {
    // storage unavailable (private mode, preview): a reload starts a new feed
  }
}

function applyTick(feed: LiveFeed, t: SimulationTick): LiveFeed {
  if (!feed.meta) return feed;
  return {
    ...feed,
    meta: {
      ...feed.meta,
      status: t.status,
      error: t.error,
      clock: t.clock,
      speed: t.speed ?? feed.meta.speed,
    },
    events:
      t.events && t.eventsFrom !== undefined
        ? feed.events.slice(0, t.eventsFrom).concat(t.events)
        : feed.events,
    predictions:
      t.predictions && t.predictionsFrom !== undefined
        ? feed.predictions.slice(0, t.predictionsFrom).concat(t.predictions)
        : feed.predictions,
    episodes: t.episodes ?? feed.episodes,
    alerts: t.alerts ?? feed.alerts,
    current: t.current !== undefined ? t.current : feed.current,
    newAlertIds: t.newAlerts?.length
      ? [...feed.newAlertIds, ...t.newAlerts].slice(-20)
      : feed.newAlertIds,
    error: t.status === "error" ? t.error : feed.error,
  };
}

export function useLiveFeed(home: string, enabled: boolean): [LiveFeed, LiveFeedControls] {
  const [state, setState] = useState<State>({ home, simId: null, epoch: 0, feed: EMPTY_FEED });
  const current = state.home === home ? state : { home, simId: null, epoch: 0, feed: EMPTY_FEED };
  const simRef = useRef<string | null>(null);
  useEffect(() => {
    simRef.current = current.simId;
  });

  const update = useCallback(
    (forHome: string, fn: (s: State) => State) =>
      setState((s) => (s.home === forHome ? fn(s) : s)),
    [],
  );

  const start = useCallback<LiveFeedControls["start"]>(
    (options) => {
      const previous = simRef.current;
      setState((s) => ({ home, simId: null, epoch: s.epoch + 1, feed: EMPTY_FEED }));
      api
        .createSimulation(home, {
          scenario: options?.scenario ?? "normal",
          speed: options?.speed ?? DEFAULT_SPEED,
          startAt: options?.startAt ?? DEFAULT_START,
        })
        .then((meta) => {
          if (previous) void api.deleteSimulation(previous);
          writeStored(home, meta.simulation);
          update(home, (s) => ({
            home,
            simId: meta.simulation,
            epoch: s.epoch + 1,
            feed: { ...EMPTY_FEED, meta },
          }));
        })
        .catch((err: unknown) =>
          update(home, (s) => ({
            ...s,
            feed: { ...EMPTY_FEED, error: err instanceof Error ? err.message : String(err) },
          })),
        );
    },
    [home, update],
  );

  // Attach to this home's simulation from earlier in the session, or start one.
  useEffect(() => {
    if (!enabled) return;
    let live = true;
    const stored = readStored(home);
    const attach = stored ? api.simulation(stored).catch(() => null) : Promise.resolve(null);
    attach.then((meta) => {
      if (!live) return;
      if (meta && meta.status !== "error") {
        setState((s) => ({
          home,
          simId: meta.simulation,
          epoch: s.epoch + 1,
          feed: { ...EMPTY_FEED, meta },
        }));
      } else {
        writeStored(home, null);
        start();
      }
    });
    return () => {
      live = false;
    };
  }, [home, enabled, start]);

  // Stream the simulation.
  const simId = current.simId;
  const epoch = current.epoch;
  useEffect(() => {
    if (!simId) return;
    const source = new EventSource(api.simulationStreamUrl(simId));
    const set = (fn: (f: LiveFeed) => LiveFeed) =>
      update(home, (s) =>
        s.simId === simId && s.epoch === epoch ? { ...s, feed: fn(s.feed) } : s,
      );
    source.addEventListener("snapshot", (e) => {
      const snap = JSON.parse((e as MessageEvent).data) as SimulationSnapshot;
      const { events, predictions, episodes, alerts, current: cur, ...meta } = snap;
      set((f) => ({
        ...f,
        meta: meta as SimulationMeta,
        ready: true,
        events,
        predictions,
        episodes,
        alerts,
        current: cur,
        error: snap.status === "error" ? snap.error : null,
      }));
    });
    source.addEventListener("status", (e) => {
      const meta = JSON.parse((e as MessageEvent).data) as SimulationMeta;
      set((f) => ({ ...f, meta }));
    });
    source.addEventListener("tick", (e) => {
      const t = JSON.parse((e as MessageEvent).data) as SimulationTick;
      set((f) => applyTick(f, t));
      if (t.status === "finished" || t.status === "error") source.close();
    });
    source.onerror = () => {
      // EventSource reconnects by itself (and gets a fresh snapshot); if the
      // simulation is gone on the server, stop and say so.
      api.simulation(simId).catch(() => {
        source.close();
        writeStored(home, null);
        set((f) => ({ ...f, error: "The live feed ended on the server. Restart it." }));
      });
    };
    return () => source.close();
  }, [simId, epoch, home, update]);

  const controls = useMemo<LiveFeedControls>(() => {
    const control = (action: "pause" | "resume" | "speed", speed?: number) => {
      const id = simRef.current;
      if (!id) return;
      api
        .controlSimulation(id, action, speed)
        .then((meta) =>
          update(home, (s) =>
            s.simId === id && s.feed.meta
              ? { ...s, feed: { ...s.feed, meta: { ...s.feed.meta, ...meta } } }
              : s,
          ),
        )
        .catch(() => undefined);
    };
    return {
      start,
      pause: () => control("pause"),
      resume: () => control("resume"),
      setSpeed: (speed: number) => control("speed", speed),
    };
  }, [start, home, update]);

  return [current.feed, controls];
}
