"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export interface CaregiverSettings {
  caregiverName: string;
  notifyAnomalies: boolean;
  notifyLeaveHome: boolean;
  showSensorIdsByDefault: boolean;
  playbackIntervalMs: number;
  quietHoursEnabled: boolean;
  quietHoursStart: string;
  quietHoursEnd: string;
}

const DEFAULT_SETTINGS: CaregiverSettings = {
  caregiverName: "Aleeza",
  notifyAnomalies: true,
  notifyLeaveHome: true,
  showSensorIdsByDefault: false,
  playbackIntervalMs: 550,
  quietHoursEnabled: true,
  quietHoursStart: "22:00",
  quietHoursEnd: "06:30",
};

interface SettingsContextValue {
  settings: CaregiverSettings;
  updateSettings: (patch: Partial<CaregiverSettings>) => void;
  resetSettings: () => void;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<CaregiverSettings>(DEFAULT_SETTINGS);

  const updateSettings = useCallback((patch: Partial<CaregiverSettings>) => {
    setSettings((prev) => ({ ...prev, ...patch }));
  }, []);

  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
  }, []);

  const value = useMemo(
    () => ({ settings, updateSettings, resetSettings }),
    [settings, updateSettings, resetSettings],
  );

  return (
    <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error("useSettings must be used within SettingsProvider");
  }
  return ctx;
}
