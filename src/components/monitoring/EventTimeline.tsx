"use client";

import { useMemo } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
} from "lucide-react";
import type { SensorEvent } from "@/types/home";
import { formatClock, secondsToTime, timeToSeconds } from "@/lib/sensorState";
import { timelineBounds } from "@/lib/timeline";

interface EventTimelineProps {
  events: SensorEvent[];
  timestamp: string;
  eventIndex: number;
  playing: boolean;
  onSeek: (timestamp: string) => void;
  onGoToIndex: (index: number) => void;
  onPrevious: () => void;
  onNext: () => void;
  onTogglePlay: () => void;
}

function tickLabels(startSec: number, endSec: number): string[] {
  const span = Math.max(endSec - startSec, 1);
  const steps = 4;
  const labels: string[] = [];
  for (let i = 0; i <= steps; i++) {
    const sec = startSec + (span * i) / steps;
    labels.push(formatClock(secondsToTime(sec)));
  }
  return labels;
}

export function EventTimeline({
  events,
  timestamp,
  eventIndex,
  playing,
  onSeek,
  onGoToIndex,
  onPrevious,
  onNext,
  onTogglePlay,
}: EventTimelineProps) {
  const bounds = useMemo(() => timelineBounds(events), [events]);

  if (!bounds || events.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-surface/60 p-4 text-sm text-muted">
        No sensor events available for this environment.
      </div>
    );
  }

  const { startSec, endSec } = bounds;
  const span = Math.max(endSec - startSec, 1);
  const progress = Math.min(
    1,
    Math.max(0, (timeToSeconds(timestamp) - startSec) / span),
  );
  const labels = tickLabels(startSec, endSec);
  const currentEvent = events[eventIndex];

  return (
    <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">
          Sensor / event timeline
        </h2>
        <p className="text-xs text-muted">
          Event {eventIndex + 1} of {events.length}
          {currentEvent
            ? ` · ${currentEvent.sensorId} → ${String(currentEvent.state)}`
            : ""}
        </p>
      </div>

      {/* Scrubber */}
      <div className="relative mt-5 px-1">
        <div className="relative h-2 rounded-full bg-surface-muted">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-accent"
            style={{ width: `${progress * 100}%` }}
          />
          {/* Event markers */}
          {events.map((event, i) => {
            const left =
              ((timeToSeconds(event.timestamp) - startSec) / span) * 100;
            return (
              <button
                key={`${event.timestamp}-${event.sensorId}-${i}`}
                type="button"
                title={`${formatClock(event.timestamp)} · ${event.sensorId}`}
                onClick={() => onGoToIndex(i)}
                className={[
                  "absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white transition",
                  i === eventIndex
                    ? "z-10 scale-125 bg-accent"
                    : "bg-muted/50 hover:bg-accent/70",
                ].join(" ")}
                style={{ left: `${left}%` }}
                aria-label={`Jump to event ${i + 1}`}
              />
            );
          })}
        </div>

        <input
          type="range"
          min={startSec}
          max={endSec}
          step={1}
          value={timeToSeconds(timestamp)}
          onChange={(e) => onSeek(secondsToTime(Number(e.target.value)))}
          className="absolute inset-x-0 top-1/2 h-8 -translate-y-1/2 cursor-pointer opacity-0"
          aria-label="Scrub timeline"
        />

        <div className="mt-3 flex justify-between gap-2 text-[10px] tabular-nums text-muted sm:text-xs">
          {labels.map((label, i) => (
            <span key={`${label}-${i}`}>{label}</span>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onPrevious}
          disabled={eventIndex <= 0}
          className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-foreground transition hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft className="h-4 w-4" />
          Previous
        </button>
        <button
          type="button"
          onClick={onTogglePlay}
          className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition hover:bg-accent-hover"
        >
          {playing ? (
            <>
              <Pause className="h-4 w-4" />
              Pause
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Play
            </>
          )}
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={eventIndex >= events.length - 1}
          className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-foreground transition hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </section>
  );
}
