"use client";

import { useCallback, useEffect, useState } from "react";

export const DAY_SECONDS = 24 * 3600;
const TICK_MS = 100;
const END = DAY_SECONDS - 1;

interface ClockState {
  key: string;
  seconds: number;
  playing: boolean;
}

/**
 * A simulated clock for replaying one day: `speed` home-seconds per real second.
 * Resets to `initial` (midnight by default) when `resetKey` changes.
 */
export function useReplayClock(speed: number, resetKey: string, initial = 0) {
  const start = Math.max(0, Math.min(initial, END));
  const [state, setState] = useState<ClockState>({ key: resetKey, seconds: start, playing: false });
  // Reset during render when the scenario changes (no effect, no extra commit).
  if (state.key !== resetKey) {
    setState({ key: resetKey, seconds: start, playing: false });
  }

  useEffect(() => {
    if (!state.playing) return;
    const id = window.setInterval(() => {
      setState((s) => {
        const seconds = Math.min(s.seconds + (speed * TICK_MS) / 1000, END);
        return { ...s, seconds, playing: s.playing && seconds < END };
      });
    }, TICK_MS);
    return () => window.clearInterval(id);
  }, [state.playing, speed]);

  const seek = useCallback((s: number) => {
    setState((st) => ({ ...st, seconds: Math.max(0, Math.min(Math.floor(s), END)) }));
  }, []);

  const togglePlay = useCallback(() => {
    setState((st) => ({
      ...st,
      seconds: !st.playing && st.seconds >= END ? 0 : st.seconds,
      playing: !st.playing,
    }));
  }, []);

  return { seconds: Math.floor(state.seconds), playing: state.playing, seek, togglePlay };
}
