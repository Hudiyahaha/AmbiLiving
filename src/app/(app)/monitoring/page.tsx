"use client";

import { useEffect, useMemo, useState } from "react";
import { InteractiveFloorPlan } from "@/components/floorplan/InteractiveFloorPlan";
import { EventTimeline } from "@/components/monitoring/EventTimeline";
import { useEnvironment } from "@/context/EnvironmentContext";
import { useSettings } from "@/context/SettingsContext";
import { useEventPlayback } from "@/hooks/useEventPlayback";
import { SENSOR_COLORS } from "@/lib/sensorColors";
import {
  formatClock,
  getSensorStatesAtTime,
  isSensorVisuallyActive,
} from "@/lib/sensorState";
import { getActivityAtTime } from "@/lib/timeline";

type PlanSource = "reference" | "svg";

export default function MonitoringPage() {
  const { currentHome } = useEnvironment();
  const { settings } = useSettings();
  const [showIds, setShowIds] = useState(settings.showSensorIdsByDefault);
  const [planSource, setPlanSource] = useState<PlanSource>("reference");

  useEffect(() => {
    setShowIds(settings.showSensorIdsByDefault);
  }, [settings.showSensorIdsByDefault]);

  const playback = useEventPlayback({
    events: currentHome.events,
    resetKey: currentHome.id,
    intervalMs: settings.playbackIntervalMs,
  });

  const previewHome = useMemo(() => {
    if (!currentHome.floorPlan) return currentHome;
    if (planSource === "svg" && currentHome.floorPlan.vectorSrc) {
      return {
        ...currentHome,
        floorPlan: {
          ...currentHome.floorPlan,
          src: currentHome.floorPlan.vectorSrc,
        },
      };
    }
    return currentHome;
  }, [currentHome, planSource]);

  const states = useMemo(
    () =>
      getSensorStatesAtTime(
        currentHome.sensors,
        currentHome.events,
        playback.timestamp,
      ),
    [currentHome.sensors, currentHome.events, playback.timestamp],
  );

  const activeSensors = useMemo(
    () =>
      currentHome.sensors.filter((sensor) =>
        isSensorVisuallyActive(sensor, states[sensor.id]),
      ),
    [currentHome.sensors, states],
  );

  const currentActivity = useMemo(
    () => getActivityAtTime(currentHome.activityHistory, playback.timestamp),
    [currentHome.activityHistory, playback.timestamp],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-display text-3xl font-semibold tabular-nums tracking-tight text-foreground">
            {formatClock(playback.timestamp)}
          </p>
          <p className="mt-1 text-sm text-muted">
            Time-controlled floor plan — play through the sensor stream for the
            selected home.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={showIds}
              onChange={(e) => setShowIds(e.target.checked)}
              className="accent-accent"
            />
            Show sensor IDs
          </label>
          {currentHome.floorPlan?.vectorSrc && (
            <label className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm">
              Plan
              <select
                value={planSource}
                onChange={(e) => setPlanSource(e.target.value as PlanSource)}
                className="rounded border border-border bg-surface px-2 py-1 text-sm outline-none"
              >
                <option value="reference">Reference (exact)</option>
                <option value="svg">SVG recreation</option>
              </select>
            </label>
          )}
        </div>
      </div>

      {currentHome.status === "placeholder" ? (
        <p className="rounded-lg bg-warning-soft px-3 py-2 text-sm text-warning">
          This environment is a placeholder. Switch to an active home to use
          monitoring.
        </p>
      ) : (
        <>
          <InteractiveFloorPlan
            home={previewHome}
            timestamp={playback.timestamp}
            showSensorIds={showIds}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
              <h2 className="text-xs font-medium uppercase tracking-wide text-muted">
                Current activity
              </h2>
              {currentActivity ? (
                <>
                  <p className="mt-1 font-display text-xl font-semibold text-foreground">
                    {currentActivity.label}
                  </p>
                  <p className="mt-1 text-sm text-muted">
                    Confidence: {Math.round(currentActivity.confidence * 100)}%
                  </p>
                </>
              ) : (
                <p className="mt-1 text-sm text-muted">
                  No recognized activity at this time.
                </p>
              )}
            </section>
            <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
              <h2 className="text-xs font-medium uppercase tracking-wide text-muted">
                Active sensors
              </h2>
              <p className="mt-2 flex flex-wrap gap-2">
                {activeSensors.length > 0 ? (
                  activeSensors.map((sensor) => (
                    <span
                      key={sensor.id}
                      className="rounded-md px-2 py-1 text-xs font-semibold text-white"
                      style={{
                        backgroundColor: SENSOR_COLORS[sensor.type].fill,
                      }}
                    >
                      {sensor.id}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-muted">None</span>
                )}
              </p>
            </section>
          </div>

          <EventTimeline
            events={currentHome.events}
            timestamp={playback.timestamp}
            eventIndex={playback.eventIndex}
            playing={playback.playing}
            onSeek={playback.setTimestamp}
            onGoToIndex={playback.goToIndex}
            onPrevious={playback.previous}
            onNext={playback.next}
            onTogglePlay={playback.togglePlay}
          />
        </>
      )}
    </div>
  );
}
