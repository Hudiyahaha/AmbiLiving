"use client";

import { useEnvironment } from "@/context/EnvironmentContext";
import { useSettings } from "@/context/SettingsContext";

function DataSourceSection() {
  const { dataOrigin, live, homes, currentHome, reload } = useEnvironment();
  const base = homes.find((h) => h.id === currentHome.id) ?? currentHome;
  const src = base.dataSource;
  const option = (on: boolean, title: string, text: string) => (
    <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border p-3 text-sm has-[:checked]:border-accent">
      <input
        type="radio"
        name="data-source"
        checked={live.enabled === on}
        onChange={() => live.setEnabled(on)}
        className="mt-0.5 accent-accent"
      />
      <span>
        <span className="font-medium text-foreground">{title}</span>
        <span className="mt-0.5 block text-muted">{text}</span>
      </span>
    </label>
  );

  return (
    <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
      <h2 className="font-display text-lg font-semibold text-foreground">Data source</h2>
      {dataOrigin === "bundled" && (
        <p className="mt-2 text-sm text-warning">
          The backend is offline, so the app shows the data bundled with it.{" "}
          <button type="button" onClick={reload} className="font-medium underline">
            Retry
          </button>
        </p>
      )}
      <div className="mt-4 space-y-2">
        {option(true, "Live feed", "A recorded day played event by event through the live system.")}
        {option(false, "Recorded day", "One exported day per home, with the dataset's annotations.")}
      </div>

      <details className="group mt-4 text-sm">
        <summary className="cursor-pointer font-medium text-foreground">How it works</summary>
        <dl className="mt-3 space-y-3 text-muted">
          <div>
            <dt className="font-medium text-foreground">Live feed</dt>
            <dd>
              There are no real sensors, so a recorded CASAS day is sent to the backend event
              by event, as a sensor hub would send it, at the chosen speed. Activity
              recognition, routine checks and alerts run on it as it arrives. On test days one
              deviation was inserted into the raw sensor events; the system is not told.
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Activity recognition</dt>
            <dd>
              A BiLSTM reads the last 100 sensor events, every 10th event. Very short
              predicted activities are merged into the one before, so a stray guess does not
              start a new activity.
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Routine deviations</dt>
            <dd>
              Each resident&apos;s routine is learned from their own observation days: which
              activities happen daily and by when, how long, how often, at what time, in what
              order, and how long the home is usually quiet. Every 2 minutes the day so far is
              compared with it.
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Alerts</dt>
            <dd>
              Possible emergencies (a long silence, a very long bathroom visit, going out or
              cooking at night, missed medicine) are sent as notifications, at most once per 2
              hours. Others go into the 21:00 evening summary (at most 3) or stay on the
              Routine deviations page.
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Recorded day</dt>
            <dd>
              {src
                ? `${src.dataset}, ${src.date}: ${src.model}, trained on ${src.trainedOn}; ${src.correct} of ${src.total} activities recognised correctly. `
                : ""}
              Activity start and end times come from the dataset annotations, so this view
              shows the model at its best; the live feed shows it without that help.
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Scenario replay</dt>
            <dd>
              The same test days, computed in advance so you can scrub through them, with
              the dataset annotations shown next to the live system&apos;s view.
            </dd>
          </div>
        </dl>
      </details>
    </section>
  );
}

export default function SettingsPage() {
  const { settings, updateSettings, resetSettings } = useSettings();

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <DataSourceSection />

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
              <span>Notify on routine deviations needing attention</span>
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
