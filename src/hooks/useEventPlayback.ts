"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { SensorEvent } from "@/types/home";
import { getEventIndexAtOrBefore } from "@/lib/timeline";

interface UseEventPlaybackOptions {
  events: SensorEvent[];
  /** ms between advancing to the next event while playing */
  intervalMs?: number;
  /** Reset when this key changes (e.g. home id) */
  resetKey?: string;
}

export function useEventPlayback({
  events,
  intervalMs = 550,
  resetKey,
}: UseEventPlaybackOptions) {
  const [eventIndex, setEventIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const eventsRef = useRef(events);
  eventsRef.current = events;

  const timestamp =
    events.length === 0
      ? "00:00:00"
      : events[Math.min(eventIndex, events.length - 1)]?.timestamp ??
        events[0].timestamp;

  const setTimestamp = useCallback(
    (next: string) => {
      const idx = getEventIndexAtOrBefore(eventsRef.current, next);
      setEventIndex(Math.max(0, idx));
      setPlaying(false);
    },
    [],
  );

  const goToIndex = useCallback(
    (index: number) => {
      if (eventsRef.current.length === 0) return;
      setEventIndex(
        Math.max(0, Math.min(index, eventsRef.current.length - 1)),
      );
    },
    [],
  );

  const previous = useCallback(() => {
    setPlaying(false);
    setEventIndex((i) => Math.max(0, i - 1));
  }, []);

  const next = useCallback(() => {
    setPlaying(false);
    setEventIndex((i) =>
      Math.min(Math.max(eventsRef.current.length - 1, 0), i + 1),
    );
  }, []);

  const togglePlay = useCallback(() => {
    setPlaying((p) => {
      if (!p && eventsRef.current.length > 0) {
        // Restart from beginning if already at end
        setEventIndex((i) =>
          i >= eventsRef.current.length - 1 ? 0 : i,
        );
      }
      return !p;
    });
  }, []);

  const pause = useCallback(() => setPlaying(false), []);

  useEffect(() => {
    setEventIndex(0);
    setPlaying(false);
  }, [resetKey]);

  useEffect(() => {
    if (!playing || events.length === 0) return;

    const id = window.setInterval(() => {
      setEventIndex((i) => {
        if (i >= eventsRef.current.length - 1) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, intervalMs);

    return () => window.clearInterval(id);
  }, [playing, events.length, intervalMs]);

  return {
    timestamp,
    eventIndex,
    playing,
    setTimestamp,
    goToIndex,
    previous,
    next,
    togglePlay,
    pause,
    eventCount: events.length,
  };
}
