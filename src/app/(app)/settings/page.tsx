"use client";

import { useSettings } from "@/context/SettingsContext";

export default function SettingsPage() {
  const { settings, updateSettings, resetSettings } = useSettings();

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <p className="text-sm text-muted">
        Caregiver preferences for this PoC. Changes apply immediately in the
        current session.
      </p>

      <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
        <h2 className="font-display text-lg font-semibold text-foreground">
          Profile
        </h2>
        <label className="mt-4 block text-sm">
          <span className="text-muted">Caregiver name</span>
          <input
            type="text"
            value={settings.caregiverName}
            onChange={(e) => updateSettings({ caregiverName: e.target.value })}
            className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-foreground outline-none focus:border-accent focus:ring-2 focus:ring-ring/25"
          />
        </label>
      </section>

      <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
        <h2 className="font-display text-lg font-semibold text-foreground">
          Alerts
        </h2>
        <ul className="mt-4 space-y-3">
          <li>
            <label className="flex cursor-pointer items-center justify-between gap-3 text-sm">
              <span>Notify on anomalies requiring attention</span>
              <input
                type="checkbox"
                checked={settings.notifyAnomalies}
                onChange={(e) =>
                  updateSettings({ notifyAnomalies: e.target.checked })
                }
                className="accent-accent"
              />
            </label>
          </li>
          <li>
            <label className="flex cursor-pointer items-center justify-between gap-3 text-sm">
              <span>Notify on Leave Home / Enter Home</span>
              <input
                type="checkbox"
                checked={settings.notifyLeaveHome}
                onChange={(e) =>
                  updateSettings({ notifyLeaveHome: e.target.checked })
                }
                className="accent-accent"
              />
            </label>
          </li>
          <li>
            <label className="flex cursor-pointer items-center justify-between gap-3 text-sm">
              <span>Quiet hours (reduce non-urgent alerts)</span>
              <input
                type="checkbox"
                checked={settings.quietHoursEnabled}
                onChange={(e) =>
                  updateSettings({ quietHoursEnabled: e.target.checked })
                }
                className="accent-accent"
              />
            </label>
          </li>
        </ul>
        {settings.quietHoursEnabled && (
          <div className="mt-4 grid grid-cols-2 gap-3">
            <label className="text-sm">
              <span className="text-muted">Quiet start</span>
              <input
                type="time"
                value={settings.quietHoursStart}
                onChange={(e) =>
                  updateSettings({ quietHoursStart: e.target.value })
                }
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
              />
            </label>
            <label className="text-sm">
              <span className="text-muted">Quiet end</span>
              <input
                type="time"
                value={settings.quietHoursEnd}
                onChange={(e) =>
                  updateSettings({ quietHoursEnd: e.target.value })
                }
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
              />
            </label>
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
        <h2 className="font-display text-lg font-semibold text-foreground">
          Monitoring
        </h2>
        <ul className="mt-4 space-y-4">
          <li>
            <label className="flex cursor-pointer items-center justify-between gap-3 text-sm">
              <span>Show sensor IDs by default</span>
              <input
                type="checkbox"
                checked={settings.showSensorIdsByDefault}
                onChange={(e) =>
                  updateSettings({ showSensorIdsByDefault: e.target.checked })
                }
                className="accent-accent"
              />
            </label>
          </li>
          <li>
            <label className="block text-sm">
              <span className="text-muted">
                Playback speed ({settings.playbackIntervalMs} ms per event)
              </span>
              <input
                type="range"
                min={200}
                max={1200}
                step={50}
                value={settings.playbackIntervalMs}
                onChange={(e) =>
                  updateSettings({
                    playbackIntervalMs: Number(e.target.value),
                  })
                }
                className="mt-2 w-full accent-accent"
              />
            </label>
          </li>
        </ul>
      </section>

      <button
        type="button"
        onClick={resetSettings}
        className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-surface-muted"
      >
        Reset to defaults
      </button>
    </div>
  );
}
