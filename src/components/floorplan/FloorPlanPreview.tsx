"use client";

import type { HomeEnvironment, SensorDefinition } from "@/types/home";
import { SENSOR_COLORS } from "@/lib/sensorColors";

interface FloorPlanPreviewProps {
  home: HomeEnvironment;
  showSensors?: boolean;
  showSensorIds?: boolean;
  className?: string;
}

function SensorMarker({
  sensor,
  showId,
}: {
  sensor: SensorDefinition;
  showId: boolean;
}) {
  const color = SENSOR_COLORS[sensor.type].fill;

  if (sensor.type === "motion") {
    const r = sensor.size === "large" ? 9 : 5;
    return (
      <g transform={`translate(${sensor.x} ${sensor.y})`}>
        <circle
          r={r}
          fill={color}
          fillOpacity={0.9}
          stroke="#ffffff"
          strokeWidth={1.25}
        />
        {showId && (
          <text
            y={-(r + 5)}
            textAnchor="middle"
            fill="#1e2a24"
            fontSize={10}
            fontWeight={600}
          >
            {sensor.id}
          </text>
        )}
      </g>
    );
  }

  if (sensor.type === "temperature") {
    return (
      <g transform={`translate(${sensor.x} ${sensor.y})`}>
        <rect
          x={-9}
          y={-3.5}
          width={18}
          height={7}
          rx={1}
          fill={color}
          fillOpacity={0.9}
        />
        {showId && (
          <text
            y={-10}
            textAnchor="middle"
            fill="#1e2a24"
            fontSize={10}
            fontWeight={600}
          >
            {sensor.id}
          </text>
        )}
      </g>
    );
  }

  const horizontal = sensor.orientation !== "vertical";
  return (
    <g transform={`translate(${sensor.x} ${sensor.y})`}>
      <rect
        x={horizontal ? -16 : -3.5}
        y={horizontal ? -3.5 : -16}
        width={horizontal ? 32 : 7}
        height={horizontal ? 7 : 32}
        rx={1}
        fill={color}
      />
      {showId && (
        <text
          y={horizontal ? -12 : 0}
          x={horizontal ? 0 : 14}
          textAnchor="middle"
          fill="#1e2a24"
          fontSize={10}
          fontWeight={600}
        >
          {sensor.id}
        </text>
      )}
    </g>
  );
}

/**
 * Static floor-plan preview (no zoom/interaction).
 * Prefer InteractiveFloorPlan on Monitoring.
 */
export function FloorPlanPreview({
  home,
  showSensors = true,
  showSensorIds = false,
  className = "",
}: FloorPlanPreviewProps) {
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
    <div
      className={`relative overflow-hidden rounded-2xl border border-border bg-surface shadow-sm ${className}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        className="block h-auto w-full"
        draggable={false}
      />
      {showSensors && (
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="pointer-events-none absolute inset-0 h-full w-full"
          aria-hidden
        >
          {home.sensors.map((sensor) => (
            <SensorMarker
              key={sensor.id}
              sensor={sensor}
              showId={showSensorIds}
            />
          ))}
        </svg>
      )}
      <span className="sr-only">{home.name} floor plan</span>
    </div>
  );
}
