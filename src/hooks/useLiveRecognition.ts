"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type Recognised } from "@/lib/api";
import type { HomeEnvironment } from "@/types/home";

/** Events the live window model reads (ml/api/live.py). */
export const WINDOW_EVENTS = 100;
const DEBOUNCE_MS = 200;

export type LiveRecognitionState =
  | { status: "off" }
  | { status: "warming-up"; have: number }
  | { status: "loading"; last?: Recognised }
  | { status: "ok"; result: Recognised }
  | { status: "error"; message: string };

/**
 * The live model's answer at a point of the playback: the saved BiLSTM is sent the
 * last 100 motion/door events up to and including `eventIndex`. This is what a
 * deployed system would know at that moment, unlike the activity history, whose
 * boundaries come from the dataset annotations.
 */
export function useLiveRecognition(
  home: HomeEnvironment,
  eventIndex: number,
  enabled: boolean,
): LiveRecognitionState {
  const date = home.dataSource?.date;

  // Index of each binary (motion/door) event, so a window is a slice.
  const binary = useMemo(
    () =>
      home.events
        .map((e, i) => (typeof e.state === "string" ? i : -1))
        .filter((i) => i >= 0),
    [home.events],
  );

  const upTo = useMemo(() => {
    // Number of binary events at or before eventIndex (binary is sorted).
    let lo = 0;
    let hi = binary.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (binary[mid] <= eventIndex) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  }, [binary, eventIndex]);

  const [state, setState] = useState<LiveRecognitionState>({ status: "off" });
  const ready = enabled && !!date && upTo >= WINDOW_EVENTS;

  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setState((s) => ({
        status: "loading",
        last: s.status === "ok" ? s.result : s.status === "loading" ? s.last : undefined,
      }));
      const events = binary.slice(upTo - WINDOW_EVENTS, upTo).map((i) => {
        const e = home.events[i];
        return {
          timestamp: `${date}T${e.timestamp}`,
          sensor: e.sensorId,
          state: String(e.state),
        };
      });
      api
        .recognise(home.id, { events, top: 3 }, controller.signal)
        .then((r) => setState({ status: "ok", result: r.current }))
        .catch((err: unknown) => {
          if (controller.signal.aborted) return;
          setState({
            status: "error",
            message: err instanceof Error ? err.message : String(err),
          });
        });
    }, DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [ready, binary, upTo, home.events, home.id, date]);

  if (!enabled || !date) return { status: "off" };
  if (upTo < WINDOW_EVENTS) return { status: "warming-up", have: upTo };
  return state;
}
