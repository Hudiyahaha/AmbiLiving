"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { DEFAULT_HOME_ID, getHomeById, homes } from "@/data/homes";
import type { HomeEnvironment } from "@/types/home";

interface EnvironmentContextValue {
  homes: HomeEnvironment[];
  currentHome: HomeEnvironment;
  setHomeId: (id: string) => void;
}

const EnvironmentContext = createContext<EnvironmentContextValue | null>(null);

export function EnvironmentProvider({ children }: { children: ReactNode }) {
  const [homeId, setHomeIdState] = useState(DEFAULT_HOME_ID);

  const setHomeId = useCallback((id: string) => {
    if (getHomeById(id)) {
      setHomeIdState(id);
    }
  }, []);

  const currentHome = useMemo(() => {
    return getHomeById(homeId) ?? getHomeById(DEFAULT_HOME_ID)!;
  }, [homeId]);

  const value = useMemo(
    () => ({
      homes,
      currentHome,
      setHomeId,
    }),
    [currentHome, setHomeId],
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
