"use client";

import { useMemo, useState } from "react";
import {
  TransformComponent,
  TransformWrapper,
  useControls,
} from "react-zoom-pan-pinch";
import { Minus, Plus, RotateCcw } from "lucide-react";
import type { HomeEnvironment, SensorStateValue } from "@/types/home";
import { SensorDetailPanel } from "@/components/floorplan/SensorDetailPanel";
import { SensorMarker } from "@/components/floorplan/SensorMarker";
import { SENSOR_COLORS } from "@/lib/sensorColors";
import { getSensorStatesAtTime } from "@/lib/sensorState";

interface InteractiveFloorPlanProps {
  home: HomeEnvironment;
  /** Current playback timestamp — drives sensor states */
  timestamp: string;
  showSensorIds?: boolean;
  className?: string;
}

function ZoomControls() {
  const { zoomIn, zoomOut, resetTransform } = useControls();

  return (
    <div className="absolute bottom-3 left-3 z-10 flex gap-1 rounded-lg border border-border bg-surface/95 p-1 shadow-sm backdrop-blur">
      <button
        type="button"
        onClick={() => zoomIn()}
        className="rounded-md p-2 text-foreground transition hover:bg-surface-muted"
        aria-label="Zoom in"
      >
        <Plus className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => zoomOut()}
        className="rounded-md p-2 text-foreground transition hover:bg-surface-muted"
        aria-label="Zoom out"
      >
        <Minus className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => resetTransform()}
        className="rounded-md p-2 text-foreground transition hover:bg-surface-muted"
        aria-label="Reset zoom"
      >
        <RotateCcw className="h-4 w-4" />
      </button>
    </div>
  );
}

function SensorLegend() {
  return (
    <ul className="flex flex-wrap gap-3 text-xs text-muted">
      {(Object.keys(SENSOR_COLORS) as Array<keyof typeof SENSOR_COLORS>).map(
        (type) => (
          <li key={type} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: SENSOR_COLORS[type].fill }}
              aria-hidden
            />
            {SENSOR_COLORS[type].label}
          </li>
        ),
      )}
      <li className="text-muted/80">Bright = active · muted = inactive</li>
    </ul>
  );
}

/**
 * Home-agnostic interactive floor plan:
 * static plan image + sensor overlay + zoom/pan + hover/click details.
 */
export function InteractiveFloorPlan({
  home,
  timestamp,
  showSensorIds = false,
  className = "",
}: InteractiveFloorPlanProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const states = useMemo(
    () => getSensorStatesAtTime(home.sensors, home.events, timestamp),
    [home.sensors, home.events, timestamp],
  );

  const selectedSensor = useMemo(
    () => home.sensors.find((s) => s.id === selectedId) ?? null,
    [home.sensors, selectedId],
  );

  if (!home.floorPlan) {
    return (
      <div
        className={`flex items-center justify-center rounded-2xl border border-dashed border-border bg-surface-muted/40 p-10 text-sm text-muted ${className}`}
      >
        No floor plan configured for this environment yet.
      </div>
    );
  }

  const { src, viewBox } = home.floorPlan;
  const { width, height } = viewBox;

  return (
    <div className={`space-y-3 ${className}`}>
      <SensorLegend />

      <div className="grid gap-4 lg:grid-cols-[1fr_minmax(220px,280px)]">
        <div className="relative overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
          <TransformWrapper
            initialScale={1}
            minScale={0.6}
            maxScale={4}
            centerOnInit
            wheel={{ step: 0.12 }}
            doubleClick={{ mode: "zoomIn" }}
          >
            <ZoomControls />
            <TransformComponent
              wrapperClass="!w-full !h-full"
              contentClass="!w-full"
              wrapperStyle={{ width: "100%", height: "100%" }}
            >
              <div
                className="relative w-full select-none"
                onClick={() => setSelectedId(null)}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={src}
                  alt=""
                  className="block h-auto w-full"
                  draggable={false}
                />
                <svg
                  viewBox={`0 0 ${width} ${height}`}
                  className="absolute inset-0 h-full w-full"
                  role="img"
                  aria-label={`${home.name} sensor overlay`}
                >
                  {home.sensors.map((sensor) => (
                    <SensorMarker
                      key={sensor.id}
                      sensor={sensor}
                      state={states[sensor.id]}
                      showId={showSensorIds}
                      selected={selectedId === sensor.id}
                      hovered={hoveredId === sensor.id}
                      onSelect={setSelectedId}
                      onHover={setHoveredId}
                    />
                  ))}
                </svg>
              </div>
            </TransformComponent>
          </TransformWrapper>
          <span className="sr-only">{home.name} floor plan</span>
        </div>

        <div className="min-h-[200px]">
          {selectedSensor ? (
            <SensorDetailPanel
              sensor={selectedSensor}
              state={states[selectedSensor.id] as SensorStateValue | undefined}
              events={home.events}
              timestamp={timestamp}
              onClose={() => setSelectedId(null)}
            />
          ) : (
            <div className="rounded-2xl border border-dashed border-border bg-surface/60 p-4 text-sm text-muted">
              Click a sensor to see its details. Hover to highlight. Scroll or
              use controls to zoom; drag to pan.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
