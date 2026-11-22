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
import { api, API_BASE } from "@/lib/api";
import type { HomeEnvironment } from "@/types/home";

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

  const currentHome = useMemo(() => {
    return (
      homes.find((h) => h.id === homeId) ??
      homes.find((h) => h.id === DEFAULT_HOME_ID)!
    );
  }, [homes, homeId]);

  const value = useMemo(
    () => ({
      homes,
      currentHome,
      setHomeId,
      dataOrigin,
      apiError,
      apiBase: API_BASE,
      reload,
    }),
    [homes, currentHome, setHomeId, dataOrigin, apiError, reload],
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
