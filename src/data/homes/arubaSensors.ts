import type { SensorDefinition } from "@/types/home";

/**
 * Aruba CASAS sensors — coordinates in the floor-plan viewBox (910 × 646),
 * aligned to public/floorplans/aruba-crop-920.png (reference, legend removed).
 *
 * Large motion cones: M007, M019, M020, M024, M027
 * Positions refined against marker detection on the reference crop.
 */
export const arubaSensors: SensorDefinition[] = [
  // Kitchen
  { id: "D002", type: "door", room: "Kitchen", x: 229, y: 26, orientation: "horizontal" },
  { id: "M016", type: "motion", size: "small", room: "Kitchen", x: 232, y: 48 },
  { id: "M017", type: "motion", size: "small", room: "Kitchen", x: 249, y: 80 },
  { id: "M019", type: "motion", size: "large", room: "Kitchen", x: 200, y: 135 },
  { id: "M015", type: "motion", size: "small", room: "Kitchen", x: 108, y: 150 },
  { id: "M018", type: "motion", size: "small", room: "Kitchen", x: 275, y: 181 },
  { id: "T003", type: "temperature", room: "Kitchen", x: 74, y: 176 },

  // Dining
  { id: "M014", type: "motion", size: "small", room: "Dining", x: 156, y: 269 },

  // Living
  { id: "M013", type: "motion", size: "small", room: "Living", x: 137, y: 411 },
  { id: "M009", type: "motion", size: "small", room: "Living", x: 294, y: 447 },
  { id: "M020", type: "motion", size: "large", room: "Living", x: 168, y: 497 },
  { id: "M010", type: "motion", size: "small", room: "Living", x: 295, y: 532 },
  { id: "M012", type: "motion", size: "small", room: "Living", x: 177, y: 542 },
  { id: "T002", type: "temperature", room: "Living", x: 87, y: 528 },
  { id: "M011", type: "motion", size: "small", room: "Living", x: 300, y: 600 },
  { id: "D001", type: "door", room: "Living", x: 362, y: 622, orientation: "horizontal" },

  // Top bathroom + adjacent hall
  { id: "D004", type: "door", room: "Bathroom", x: 539, y: 31, orientation: "horizontal" },
  { id: "M030", type: "motion", size: "small", room: "Bathroom", x: 521, y: 48 },
  { id: "M029", type: "motion", size: "small", room: "Bathroom", x: 520, y: 93 },
  { id: "D003", type: "door", room: "Bathroom", x: 455, y: 205, orientation: "horizontal" },
  { id: "M031", type: "motion", size: "small", room: "Hallway", x: 384, y: 220 },
  { id: "T004", type: "temperature", room: "Hallway", x: 389, y: 252 },

  // Office
  { id: "M026", type: "motion", size: "small", room: "Office", x: 805, y: 76 },
  { id: "M027", type: "motion", size: "large", room: "Office", x: 761, y: 137 },
  { id: "T005", type: "temperature", room: "Office", x: 820, y: 153 },
  { id: "M025", type: "motion", size: "small", room: "Office", x: 829, y: 187 },

  // Central hallway / transitions
  { id: "M028", type: "motion", size: "small", room: "Hallway", x: 580, y: 177 },
  { id: "M021", type: "motion", size: "small", room: "Hallway", x: 372, y: 276 },
  { id: "M022", type: "motion", size: "small", room: "Hallway", x: 535, y: 275 },
  { id: "M023", type: "motion", size: "small", room: "Hallway", x: 669, y: 278 },

  // Middle bedroom (right of hall)
  { id: "M024", type: "motion", size: "large", room: "Bedroom", x: 676, y: 277 },

  // Bottom bedroom
  { id: "M008", type: "motion", size: "small", room: "Bedroom", x: 409, y: 437 },
  { id: "M006", type: "motion", size: "small", room: "Bedroom", x: 450, y: 448 },
  { id: "M005", type: "motion", size: "small", room: "Bedroom", x: 542, y: 432 },
  { id: "T001", type: "temperature", room: "Bedroom", x: 466, y: 492 },
  { id: "M003", type: "motion", size: "small", room: "Bedroom", x: 438, y: 515 },
  { id: "M007", type: "motion", size: "large", room: "Bedroom", x: 599, y: 517 },
  { id: "M002", type: "motion", size: "small", room: "Bedroom", x: 437, y: 573 },
  { id: "M001", type: "motion", size: "small", room: "Bedroom", x: 606, y: 581 },

  // Bottom bathroom entrance
  { id: "M004", type: "motion", size: "small", room: "Bathroom", x: 703, y: 406 },
];
