"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  DEFAULT_HOME_ID,
  getHomeById,
  homes as bundledHomes,
  withApiData,
} from "@/data/homes";
import { useLiveFeed, type LiveFeed, type LiveFeedControls } from "@/hooks/useLiveFeed";
import { api, API_BASE } from "@/lib/api";
import { liveEvents, toLiveHome } from "@/lib/liveHome";
import type { HomeEnvironment } from "@/types/home";

const LIVE_PREF = "ambiliving.live";

function readLivePref(): boolean {
  if (typeof window === "undefined") return true;
  try {
    return window.localStorage.getItem(LIVE_PREF) !== "off";
  } catch {
    return true;
  }
}

export interface LiveContext {
  /** Whether pages follow a live feed (when the API is up) or show the exported day */
  enabled: boolean;
  setEnabled: (on: boolean) => void;
  /** The current home's live feed */
  feed: LiveFeed;
  controls: LiveFeedControls;
}

/**
 * Where the current data comes from: the backend API, or the files bundled
 * with the app (used while the API loads and whenever it cannot be reached).
 */
export type DataOrigin = "loading" | "api" | "bundled";

interface EnvironmentContextValue {
  homes: HomeEnvironment[];
  currentHome: HomeEnvironment;
  setHomeId: (id: string) => void;
  dataOrigin: DataOrigin;
  /** Why the API was not used, when dataOrigin is "bundled" */
  apiError: string | null;
  apiBase: string;
  /** Try the API again */
  reload: () => void;
  live: LiveContext;
}

const EnvironmentContext = createContext<EnvironmentContextValue | null>(null);

export function EnvironmentProvider({ children }: { children: ReactNode }) {
  const [homeId, setHomeIdState] = useState(DEFAULT_HOME_ID);
  const [homes, setHomes] = useState<HomeEnvironment[]>(bundledHomes);
  const [dataOrigin, setDataOrigin] = useState<DataOrigin>("loading");
  const [apiError, setApiError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    Promise.all(
      bundledHomes.map(async (home) => {
        if (home.status !== "active") return home;
        const [day, anomalies] = await Promise.all([
          api.day(home.id),
          api.anomalies(home.id),
        ]);
        return withApiData(home, day, anomalies);
      }),
    )
      .then((fromApi) => {
        if (!live) return;
        setHomes(fromApi);
        setDataOrigin("api");
        setApiError(null);
      })
      .catch((err: unknown) => {
        if (!live) return;
        setHomes(bundledHomes);
        setDataOrigin("bundled");
        setApiError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      live = false;
    };
  }, [attempt]);

  const setHomeId = useCallback((id: string) => {
    if (getHomeById(id)) {
      setHomeIdState(id);
    }
  }, []);

  const reload = useCallback(() => {
    setDataOrigin("loading");
    setAttempt((n) => n + 1);
  }, []);

  const baseHome = useMemo(() => {
    return (
      homes.find((h) => h.id === homeId) ??
      homes.find((h) => h.id === DEFAULT_HOME_ID)!
    );
  }, [homes, homeId]);

  // Live feed (decision D19): a simulated home streamed from the backend.
  const [liveEnabled, setLiveEnabledState] = useState(readLivePref);
  const setLiveEnabled = useCallback((on: boolean) => {
    setLiveEnabledState(on);
    try {
      window.localStorage.setItem(LIVE_PREF, on ? "on" : "off");
    } catch {
      // preference only lasts for this page then
    }
  }, []);
  const [feed, controls] = useLiveFeed(
    baseHome.id,
    liveEnabled && dataOrigin === "api" && baseHome.status === "active",
  );
  const liveSensorEvents = useMemo(() => liveEvents(feed.events), [feed.events]);
  const showLive = liveEnabled && dataOrigin === "api" && feed.ready && feed.meta !== null;

  const currentHome = useMemo(
    () => (showLive ? toLiveHome(baseHome, feed, liveSensorEvents) : baseHome),
    [showLive, baseHome, feed, liveSensorEvents],
  );

  const live = useMemo<LiveContext>(
    () => ({ enabled: liveEnabled, setEnabled: setLiveEnabled, feed, controls }),
    [liveEnabled, setLiveEnabled, feed, controls],
  );

  const value = useMemo(
    () => ({
      homes,
      currentHome,
      setHomeId,
      dataOrigin,
      apiError,
      apiBase: API_BASE,
      reload,
      live,
    }),
    [homes, currentHome, setHomeId, dataOrigin, apiError, reload, live],
  );

  return (
    <EnvironmentContext.Provider value={value}>
      {children}
    </EnvironmentContext.Provider>
  );
}

export function useEnvironment() {
  const ctx = useContext(EnvironmentContext);
  if (!ctx) {
    throw new Error("useEnvironment must be used within EnvironmentProvider");
  }
  return ctx;
}
