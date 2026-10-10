import type { SensorType } from "@/types/home";

/** Distinct colors per sensor category — used across markers, legend, and details. */
export const SENSOR_COLORS: Record<
  SensorType,
  { fill: string; soft: string; label: string }
> = {
  motion: {
    fill: "#2f6f5e",
    soft: "#d7ebe4",
    label: "Motion",
  },
  door: {
    fill: "#3a6d9b",
    soft: "#d9e6f2",
    label: "Door",
  },
  temperature: {
    fill: "#c17a2f",
    soft: "#f5e6d4",
    label: "Temperature",
  },
};

export function sensorColor(type: SensorType): string {
  return SENSOR_COLORS[type].fill;
}
