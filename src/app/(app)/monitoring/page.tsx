"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { InteractiveFloorPlan } from "@/components/floorplan/InteractiveFloorPlan";
import { EventTimeline } from "@/components/monitoring/EventTimeline";
import { LiveMonitoring } from "@/components/monitoring/LiveMonitoring";
import { ActivitiesPanel, AlertsPanel } from "@/components/monitoring/MonitoringPanels";
import {
  MapOptions,
  MonitoringShell,
  RoomsCard,
  useMonitoringTab,
  withPlan,
} from "@/components/monitoring/MonitoringShell";
import { useEnvironment } from "@/context/EnvironmentContext";
import { useSettings } from "@/context/SettingsContext";
import { useEventPlayback } from "@/hooks/useEventPlayback";
import {
  formatClock,
  getSensorStatesAtTime,
  isSensorVisuallyActive,
} from "@/lib/sensorState";
import { getActivityAtTime } from "@/lib/timeline";

export default function MonitoringPage() {
  return (
    <Suspense fallback={null}>
      <Monitoring />
    </Suspense>
  );
}

function Monitoring() {
  const { currentHome } = useEnvironment();
  const { settings } = useSettings();
  const [showIds, setShowIds] = useState(settings.showSensorIdsByDefault);

  useEffect(() => {
    setShowIds(settings.showSensorIdsByDefault);
  }, [settings.showSensorIdsByDefault]);

  if (currentHome.status === "placeholder") {
    return (
      <p className="mx-auto max-w-6xl rounded-lg bg-warning-soft px-3 py-2 text-sm text-warning">
        This home is not set up yet.
      </p>
    );
  }
  if (currentHome.live) return <LiveMonitoring showIds={showIds} onShowIds={setShowIds} />;
  return <RecordedMonitoring showIds={showIds} onShowIds={setShowIds} />;
}

/** The exported day, played back event by event. */
function RecordedMonitoring({
  showIds,
  onShowIds,
}: {
  showIds: boolean;
  onShowIds: (on: boolean) => void;
}) {
  const { currentHome } = useEnvironment();
  const { settings } = useSettings();
  const tab = useMonitoringTab();
  const [planSource, setPlanSource] = useState<"reference" | "svg">("svg");

  const playback = useEventPlayback({
    events: currentHome.events,
    resetKey: currentHome.id,
    intervalMs: settings.playbackIntervalMs,
  });
  const states = useMemo(
    () => getSensorStatesAtTime(currentHome.sensors, currentHome.events, playback.timestamp),
    [currentHome.sensors, currentHome.events, playback.timestamp],
  );
  const active = currentHome.sensors.filter((s) => isSensorVisuallyActive(s, states[s.id]));
  const now = useMemo(
    () => getActivityAtTime(currentHome.activityHistory, playback.timestamp),
    [currentHome.activityHistory, playback.timestamp],
  );

  return (
    <MonitoringShell
      home={currentHome}
      clock={formatClock(playback.timestamp)}
      subtitle={currentHome.dataSource ? `Recorded day · ${currentHome.dataSource.date}` : undefined}
    >
      {tab === "home" && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <section className="rounded-2xl border border-border bg-surface p-4 shadow-sm">
              <h2 className="text-xs font-medium uppercase tracking-wide text-muted">Now</h2>
              {now ? (
                <>
                  <p className="mt-1 font-display text-xl font-semibold text-foreground">
                    {now.label}
                  </p>
                  <p className="mt-0.5 text-sm text-muted">
                    since {formatClock(now.start).replace(/:\d\d /, " ")}
                  </p>
                </>
              ) : (
                <p className="mt-1 text-sm text-muted">Not known</p>
              )}
            </section>
            <RoomsCard active={active} />
          </div>
          <MapOptions
            home={currentHome}
            showIds={showIds}
            onShowIds={onShowIds}
            planSource={planSource}
            onPlanSource={setPlanSource}
          />
          <InteractiveFloorPlan
            home={withPlan(currentHome, planSource)}
            timestamp={playback.timestamp}
            showSensorIds={showIds}
          />
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
        </div>
      )}
      {tab === "activities" && <ActivitiesPanel home={currentHome} />}
      {tab === "alerts" && <AlertsPanel home={currentHome} />}
    </MonitoringShell>
  );
}
