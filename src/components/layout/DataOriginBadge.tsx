"use client";

import Link from "next/link";
import { RefreshCw } from "lucide-react";
import { useEnvironment } from "@/context/EnvironmentContext";
import { secondsToTime } from "@/lib/sensorState";

/**
 * Where the pages' data comes from: a live feed, the backend API (exported day),
 * or the files bundled with the app when the API is offline.
 */
export function DataOriginBadge() {
  const { dataOrigin, apiError, apiBase, reload, currentHome, live } = useEnvironment();

  const waitingForLive =
    dataOrigin === "api" && live.enabled && !currentHome.live && currentHome.status === "active";
  if (dataOrigin === "loading" || (waitingForLive && !live.feed.error)) {
    return (
      <span className="whitespace-nowrap rounded-full border border-border px-2.5 py-1 text-xs text-muted">
        {dataOrigin === "loading" ? "Connecting to API…" : "Connecting to live feed…"}
      </span>
    );
  }

  if (dataOrigin === "api" && currentHome.live) {
    const l = currentHome.live;
    const running = l.status === "running";
    return (
      <Link
        href="/monitoring"
        className="flex items-center gap-1.5 whitespace-nowrap rounded-full bg-accent-soft px-2.5 py-1 text-xs font-medium tabular-nums text-accent transition hover:opacity-80"
        title={`Live feed: ${l.title}, ${l.dayLabel} (${l.status})`}
      >
        <span
          className={`h-1.5 w-1.5 rounded-full bg-accent ${running ? "animate-pulse" : "opacity-50"}`}
          aria-hidden
        />
        Live {secondsToTime(l.clock).slice(0, 5)}
        {l.status === "paused" ? " · paused" : l.status === "finished" ? " · day over" : ""}
      </Link>
    );
  }

  if (dataOrigin === "api") {
    return (
      <span
        className="flex items-center gap-1.5 whitespace-nowrap rounded-full bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent"
        title={`Data from ${apiBase}`}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
        API · exported day
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={reload}
      className="flex items-center gap-1.5 whitespace-nowrap rounded-full bg-warning-soft px-2.5 py-1 text-xs font-medium text-warning transition hover:opacity-80"
      title={`${apiError ?? "API not reachable"}. Showing the bundled data. Start it from ml/ with \`py -m api\`, then click to retry.`}
    >
      <RefreshCw className="h-3 w-3" aria-hidden />
      Bundled data · API offline
    </button>
  );
}
