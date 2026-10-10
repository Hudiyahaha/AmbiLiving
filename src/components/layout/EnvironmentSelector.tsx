"use client";

import { ChevronDown } from "lucide-react";
import { useEnvironment } from "@/context/EnvironmentContext";

export function EnvironmentSelector() {
  const { homes, currentHome, setHomeId } = useEnvironment();

  return (
    <label className="flex items-center gap-3">
      <span className="hidden text-sm text-muted sm:inline">
        Monitoring Environment
      </span>
      <div className="relative">
        <select
          value={currentHome.id}
          onChange={(e) => setHomeId(e.target.value)}
          className="appearance-none rounded-lg border border-border bg-surface py-2 pl-3 pr-9 text-sm font-medium text-foreground shadow-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-ring/25"
          aria-label="Monitoring environment"
        >
          {homes.map((home) => (
            <option key={home.id} value={home.id}>
              {home.name}
              {home.status === "placeholder" ? " (placeholder)" : ""}
            </option>
          ))}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
          aria-hidden
        />
      </div>
    </label>
  );
}
