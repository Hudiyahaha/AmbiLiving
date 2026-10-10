"use client";

import type { SensorDefinition, SensorStateValue } from "@/types/home";
import { SENSOR_COLORS } from "@/lib/sensorColors";
import { isSensorVisuallyActive } from "@/lib/sensorState";

interface SensorMarkerProps {
  sensor: SensorDefinition;
  state?: SensorStateValue;
  showId: boolean;
  selected: boolean;
  hovered: boolean;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
}

export function SensorMarker({
  sensor,
  state,
  showId,
  selected,
  hovered,
  onSelect,
  onHover,
}: SensorMarkerProps) {
  const color = SENSOR_COLORS[sensor.type].fill;
  const active = isSensorVisuallyActive(sensor, state);
  const emphasize = selected || hovered;
  const opacity = active ? 1 : 0.35;
  const stroke = emphasize ? "#1e2a24" : "#ffffff";
  const strokeWidth = emphasize ? 2 : 1.25;

  const hitPad = sensor.type === "motion" && sensor.size === "large" ? 16 : 12;

  return (
    <g
      transform={`translate(${sensor.x} ${sensor.y})`}
      opacity={opacity}
      style={{ cursor: "pointer" }}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(sensor.id);
      }}
      onMouseEnter={() => onHover(sensor.id)}
      onMouseLeave={() => onHover(null)}
      role="button"
      tabIndex={0}
      aria-label={`${sensor.id} ${sensor.type} sensor`}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(sensor.id);
        }
      }}
    >
      {/* Invisible hit target */}
      <circle r={hitPad} fill="transparent" />

      {active && (
        <circle
          r={sensor.type === "motion" && sensor.size === "large" ? 16 : 12}
          fill={color}
          fillOpacity={0.18}
        />
      )}

      {sensor.type === "motion" && (
        <circle
          r={sensor.size === "large" ? 9 : 5.5}
          fill={color}
          stroke={stroke}
          strokeWidth={strokeWidth}
        />
      )}

      {sensor.type === "temperature" && (
        <rect
          x={-10}
          y={-4}
          width={20}
          height={8}
          rx={1.5}
          fill={color}
          stroke={stroke}
          strokeWidth={strokeWidth}
        />
      )}

      {sensor.type === "door" &&
        (() => {
          const horizontal = sensor.orientation !== "vertical";
          return (
            <rect
              x={horizontal ? -16 : -3.5}
              y={horizontal ? -3.5 : -16}
              width={horizontal ? 32 : 7}
              height={horizontal ? 7 : 32}
              rx={1.5}
              fill={color}
              stroke={stroke}
              strokeWidth={strokeWidth}
            />
          );
        })()}

      {(showId || emphasize) && (
        <text
          y={
            sensor.type === "door" && sensor.orientation === "vertical"
              ? 0
              : sensor.type === "motion" && sensor.size === "large"
                ? -14
                : -11
          }
          x={
            sensor.type === "door" && sensor.orientation === "vertical" ? 14 : 0
          }
          textAnchor="middle"
          fill="#1e2a24"
          fontSize={10}
          fontWeight={700}
          style={{ pointerEvents: "none" }}
        >
          {sensor.id}
        </text>
      )}
    </g>
  );
}
