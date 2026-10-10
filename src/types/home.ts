/**
 * Dataset/home-agnostic domain types for the AmbiLiving PoC.
 * UI components consume these shapes — never Aruba-specific fields.
 */

export type HomeStatus = "active" | "placeholder";

export type SensorType = "motion" | "door" | "temperature";

export type MotionSize = "large" | "small";

export type MotionState = "active" | "inactive";
export type DoorState = "open" | "closed";

/** Runtime state for a sensor at a given timestamp */
export type SensorStateValue = MotionState | DoorState | number; // number = °C for temperature

export interface SensorDefinition {
  id: string;
  type: SensorType;
  room: string;
  /** SVG coordinate system (same as floor plan viewBox) */
  x: number;
  y: number;
  /** Motion cone size when type === "motion" */
  size?: MotionSize;
  /** Door segment orientation when type === "door" */
  orientation?: "horizontal" | "vertical";
}

export interface FloorPlanDefinition {
  /** Public path to static floor plan (SVG or raster) */
  src: string;
  viewBox: {
    width: number;
    height: number;
  };
  /** Optional reference raster for calibration / comparison */
  referenceSrc?: string;
  /** Optional vector recreation path */
  vectorSrc?: string;
}

export interface ActivityClass {
  id: string;
  label: string;
}

export interface RecognizedActivity {
  id: string;
  activityId: string;
  label: string;
  start: string; // ISO-like or HH:mm:ss display time for PoC
  end: string;
  durationMinutes: number;
  confidence: number; // 0–1
  sensorIds: string[];
  /** Optional date label for history grouping, e.g. "Today" */
  dayLabel?: string;
}

export interface SensorEvent {
  timestamp: string; // e.g. "10:42:13"
  sensorId: string;
  /** Semantic state for the event */
  state: SensorStateValue;
}

export interface AnomalyRecord {
  id: string;
  title: string;
  observed: string;
  expected: string;
  reason: string;
  severity: "low" | "medium" | "high";
  relatedActivityId?: string;
  timestamp: string;
  /** Whether caregiver still needs to review */
  requiresAttention?: boolean;
}

export interface DatasetStats {
  activityInstances: number;
  activityClasses: number;
  dataPeriod: string;
}

export interface HomeEnvironment {
  id: string;
  name: string;
  status: HomeStatus;
  summary: string;
  residentLabel: string;
  activityCount: number | null;
  floorPlan: FloorPlanDefinition | null;
  sensors: SensorDefinition[];
  activityClasses: ActivityClass[];
  /** Mock chronological sensor stream for monitoring playback */
  events: SensorEvent[];
  /** Recognized activity history for this home */
  activityHistory: RecognizedActivity[];
  anomalies: AnomalyRecord[];
  /** Optional activity at “current” monitoring time */
  currentActivityId: string | null;
  datasetStats?: DatasetStats;
}
