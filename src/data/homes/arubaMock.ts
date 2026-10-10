import type {
  ActivityClass,
  AnomalyRecord,
  RecognizedActivity,
  SensorEvent,
} from "@/types/home";

/**
 * Aruba activity classes from CASAS / defense slides (11 classes).
 * Counts shown in slides: Relax 2919, Meal_Preparation 1606, etc.
 */
export const arubaActivityClasses: ActivityClass[] = [
  { id: "relax", label: "Relax" },
  { id: "meal_preparation", label: "Meal Preparation" },
  { id: "leave_home", label: "Leave Home" },
  { id: "enter_home", label: "Enter Home" },
  { id: "sleeping", label: "Sleeping" },
  { id: "eating", label: "Eating" },
  { id: "work", label: "Work" },
  { id: "bed_to_toilet", label: "Bed to Toilet" },
  { id: "wash_dishes", label: "Wash Dishes" },
  { id: "housekeeping", label: "Housekeeping" },
  { id: "respirate", label: "Respirate" },
];

/**
 * Monitoring stream built around slide examples:
 * - Sleeping (M003 / M002 / M007 pattern)
 * - Meal_Preparation (M015, M017, M018, M019) — slide 13
 * - Wash_Dishes (same sensors) — slide 13
 */
export const arubaEvents: SensorEvent[] = [
  // Sleeping end transition (adapted from slide 11)
  { timestamp: "05:40:27", sensorId: "M003", state: "active" },
  { timestamp: "05:40:29", sensorId: "M002", state: "active" },
  { timestamp: "05:40:32", sensorId: "M007", state: "active" },
  { timestamp: "05:40:34", sensorId: "M002", state: "inactive" },
  { timestamp: "05:40:40", sensorId: "M003", state: "inactive" },
  { timestamp: "05:40:45", sensorId: "M007", state: "inactive" },
  { timestamp: "05:41:00", sensorId: "T002", state: 21.5 },
  { timestamp: "05:41:10", sensorId: "T003", state: 21.0 },
  { timestamp: "05:41:12", sensorId: "T004", state: 21.0 },

  // Bed_to_Toilet
  { timestamp: "05:42:00", sensorId: "M004", state: "active" },
  { timestamp: "05:42:20", sensorId: "M004", state: "inactive" },
  { timestamp: "05:43:00", sensorId: "M007", state: "active" },
  { timestamp: "05:45:00", sensorId: "M007", state: "inactive" },

  // Meal_Preparation — slide 13 (09:54:58 – 09:56:27)
  { timestamp: "09:54:58", sensorId: "M018", state: "active" },
  { timestamp: "09:54:59", sensorId: "M019", state: "active" },
  { timestamp: "09:55:00", sensorId: "M015", state: "active" },
  { timestamp: "09:55:06", sensorId: "M015", state: "active" },
  { timestamp: "09:55:07", sensorId: "M019", state: "active" },
  { timestamp: "09:55:17", sensorId: "M015", state: "active" },
  { timestamp: "09:55:38", sensorId: "M018", state: "active" },
  { timestamp: "09:56:22", sensorId: "M018", state: "active" },
  { timestamp: "09:56:23", sensorId: "M017", state: "active" },
  { timestamp: "09:56:27", sensorId: "M018", state: "inactive" },
  { timestamp: "09:56:28", sensorId: "M017", state: "inactive" },
  { timestamp: "09:56:30", sensorId: "M019", state: "inactive" },
  { timestamp: "09:56:32", sensorId: "M015", state: "inactive" },

  // Eating
  { timestamp: "09:57:10", sensorId: "M014", state: "active" },
  { timestamp: "09:57:40", sensorId: "M013", state: "active" },
  { timestamp: "10:02:00", sensorId: "M014", state: "inactive" },
  { timestamp: "10:02:10", sensorId: "M013", state: "inactive" },

  // Wash_Dishes — slide 13 (10:03:21 – 10:04:25)
  { timestamp: "10:03:21", sensorId: "M018", state: "active" },
  { timestamp: "10:03:24", sensorId: "M017", state: "active" },
  { timestamp: "10:03:43", sensorId: "M017", state: "active" },
  { timestamp: "10:03:57", sensorId: "M017", state: "active" },
  { timestamp: "10:03:59", sensorId: "M018", state: "active" },
  { timestamp: "10:04:05", sensorId: "M019", state: "active" },
  { timestamp: "10:04:06", sensorId: "M015", state: "active" },
  { timestamp: "10:04:21", sensorId: "M018", state: "active" },
  { timestamp: "10:04:25", sensorId: "M018", state: "inactive" },
  { timestamp: "10:04:27", sensorId: "M017", state: "inactive" },
  { timestamp: "10:04:28", sensorId: "M019", state: "inactive" },
  { timestamp: "10:04:30", sensorId: "M015", state: "inactive" },

  // Relax in living room
  { timestamp: "10:10:00", sensorId: "M020", state: "active" },
  { timestamp: "10:10:15", sensorId: "M009", state: "active" },
  { timestamp: "10:10:30", sensorId: "M012", state: "active" },
  { timestamp: "10:25:00", sensorId: "M009", state: "inactive" },
  { timestamp: "10:25:10", sensorId: "M012", state: "inactive" },
  { timestamp: "10:25:20", sensorId: "M020", state: "inactive" },

  // Work in office
  { timestamp: "10:30:00", sensorId: "M027", state: "active" },
  { timestamp: "10:30:20", sensorId: "M025", state: "active" },
  { timestamp: "10:52:00", sensorId: "M025", state: "inactive" },
  { timestamp: "10:52:10", sensorId: "M027", state: "inactive" },

  // Leave_Home
  { timestamp: "11:00:00", sensorId: "M011", state: "active" },
  { timestamp: "11:00:05", sensorId: "D001", state: "open" },
  { timestamp: "11:00:12", sensorId: "D001", state: "closed" },
  { timestamp: "11:00:15", sensorId: "M011", state: "inactive" },
];

export const arubaActivityHistory: RecognizedActivity[] = [
  {
    id: "aruba-sleep-1",
    activityId: "sleeping",
    label: "Sleeping",
    start: "00:03:50",
    end: "05:40:40",
    durationMinutes: 337,
    confidence: 0.97,
    sensorIds: ["M002", "M003", "M007"],
    dayLabel: "Today",
  },
  {
    id: "aruba-btt-1",
    activityId: "bed_to_toilet",
    label: "Bed to Toilet",
    start: "05:42:00",
    end: "05:45:00",
    durationMinutes: 3,
    confidence: 0.93,
    sensorIds: ["M004", "M007"],
    dayLabel: "Today",
  },
  {
    id: "aruba-meal-1",
    activityId: "meal_preparation",
    label: "Meal Preparation",
    start: "09:54:58",
    end: "09:56:27",
    durationMinutes: 2,
    confidence: 0.91,
    sensorIds: ["M015", "M017", "M018", "M019"],
    dayLabel: "Today",
  },
  {
    id: "aruba-eat-1",
    activityId: "eating",
    label: "Eating",
    start: "09:57:10",
    end: "10:02:10",
    durationMinutes: 5,
    confidence: 0.88,
    sensorIds: ["M013", "M014"],
    dayLabel: "Today",
  },
  {
    id: "aruba-wash-1",
    activityId: "wash_dishes",
    label: "Wash Dishes",
    start: "10:03:21",
    end: "10:04:25",
    durationMinutes: 1,
    confidence: 0.79,
    sensorIds: ["M015", "M017", "M018", "M019"],
    dayLabel: "Today",
  },
  {
    id: "aruba-relax-1",
    activityId: "relax",
    label: "Relax",
    start: "10:10:00",
    end: "10:25:20",
    durationMinutes: 15,
    confidence: 0.94,
    sensorIds: ["M009", "M012", "M020"],
    dayLabel: "Today",
  },
  {
    id: "aruba-work-1",
    activityId: "work",
    label: "Work",
    start: "10:30:00",
    end: "10:52:10",
    durationMinutes: 22,
    confidence: 0.9,
    sensorIds: ["M025", "M027"],
    dayLabel: "Today",
  },
  {
    id: "aruba-leave-1",
    activityId: "leave_home",
    label: "Leave Home",
    start: "11:00:00",
    end: "11:00:15",
    durationMinutes: 0,
    confidence: 0.96,
    sensorIds: ["D001", "M011"],
    dayLabel: "Today",
  },
  {
    id: "aruba-meal-y",
    activityId: "meal_preparation",
    label: "Meal Preparation",
    start: "18:10:00",
    end: "19:44:00",
    durationMinutes: 94,
    confidence: 0.86,
    sensorIds: ["M015", "M016", "M017", "M018", "M019"],
    dayLabel: "Yesterday",
  },
  {
    id: "aruba-house-y",
    activityId: "housekeeping",
    label: "Housekeeping",
    start: "14:20:00",
    end: "14:55:00",
    durationMinutes: 35,
    confidence: 0.82,
    sensorIds: ["M009", "M013", "M020", "M021"],
    dayLabel: "Yesterday",
  },
  {
    id: "aruba-enter-y",
    activityId: "enter_home",
    label: "Enter Home",
    start: "16:05:00",
    end: "16:05:20",
    durationMinutes: 0,
    confidence: 0.95,
    sensorIds: ["D001", "M011"],
    dayLabel: "Yesterday",
  },
];

export const arubaAnomalies: AnomalyRecord[] = [
  {
    id: "aruba-anom-1",
    title: "Unusual Meal Preparation Duration",
    observed: "94 min",
    expected: "20–45 min",
    reason: "Unusual duration — longer than the resident’s typical meal preparation window",
    severity: "medium",
    relatedActivityId: "aruba-meal-y",
    timestamp: "Yesterday · 19:44",
    requiresAttention: true,
  },
  {
    id: "aruba-anom-2",
    title: "Overlapping kitchen activities",
    observed: "Meal Preparation and Wash Dishes used the same sensors (M015, M017, M018, M019)",
    expected: "Clearer separation between kitchen activity patterns",
    reason: "Irregular / ambiguous sensor sequence — activities share nearly identical evidence",
    severity: "low",
    relatedActivityId: "aruba-wash-1",
    timestamp: "Today · 10:04",
    requiresAttention: true,
  },
  {
    id: "aruba-anom-3",
    title: "Irregular sensor sequence",
    observed: "Kitchen → Bedroom → Kitchen within 2 min",
    expected: "Gradual room transitions",
    reason: "Irregular sensor sequence",
    severity: "low",
    timestamp: "Today · 09:18",
    requiresAttention: false,
  },
];
