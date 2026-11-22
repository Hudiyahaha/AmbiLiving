"use client";

import Link from "next/link";
import { useEnvironment } from "@/context/EnvironmentContext";
import { secondsToTime } from "@/lib/sensorState";

const CHIP = "flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium transition hover:opacity-80";

/** Where the data comes from (live feed, recorded day or offline); details in Settings. */
export function DataOriginBadge() {
  const { dataOrigin, currentHome, live } = useEnvironment();

  if (dataOrigin === "api" && currentHome.live) {
    const l = currentHome.live;
    return (
      <Link
        href="/monitoring"
        className={`${CHIP} bg-accent-soft tabular-nums text-accent`}
        title={`${l.title}, ${l.dayLabel}`}
      >
        <span
          className={`h-1.5 w-1.5 rounded-full bg-accent ${l.status === "running" ? "animate-pulse" : "opacity-50"}`}
          aria-hidden
        />
        Live {secondsToTime(Math.min(l.clock, 86399)).slice(0, 5)}
        {l.status === "paused" ? " · paused" : l.status === "finished" ? " · day over" : ""}
      </Link>
    );
  }

  const connecting =
    dataOrigin === "loading" ||
    (dataOrigin === "api" && live.enabled && currentHome.status === "active" && !live.feed.error);
  if (connecting) {
    return <span className={`${CHIP} border border-border text-muted`}>Connecting…</span>;
  }

  return (
    <Link
      href="/settings"
      className={`${CHIP} ${dataOrigin === "api" ? "border border-border text-muted" : "bg-warning-soft text-warning"}`}
      title="Data source settings"
    >
      {dataOrigin === "api" ? "Recorded day" : "Offline"}
    </Link>
  );
}
