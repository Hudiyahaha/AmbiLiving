"use client";

import { RefreshCw } from "lucide-react";
import { useEnvironment } from "@/context/EnvironmentContext";

/** Shows whether the pages show data from the backend API or the bundled files. */
export function DataOriginBadge() {
  const { dataOrigin, apiError, apiBase, reload } = useEnvironment();

  if (dataOrigin === "loading") {
    return (
      <span className="whitespace-nowrap rounded-full border border-border px-2.5 py-1 text-xs text-muted">
        Connecting to API…
      </span>
    );
  }

  if (dataOrigin === "api") {
    return (
      <span
        className="flex items-center gap-1.5 whitespace-nowrap rounded-full bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent"
        title={`Data from ${apiBase}`}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
        Live API
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
