import type { SensorDefinition } from "@/types/home";

/**
 * Milan CASAS sensors — coordinates in viewBox (1024 × 848),
 * aligned to public/floorplans/milan-reference.png.
 */
export const milanSensors: SensorDefinition[] = [
  // Northwest bedroom
  { id: "M021", type: "motion", size: "small", room: "Bedroom", x: 76, y: 111 },
  { id: "M028", type: "motion", size: "small", room: "Bedroom", x: 155, y: 175 },
  { id: "M020", type: "motion", size: "small", room: "Bedroom", x: 129, y: 240 },

  // Top bathroom
  { id: "M007", type: "motion", size: "small", room: "Bathroom", x: 384, y: 113 },

  // Living / open plan (right + top)
  { id: "M005", type: "motion", size: "small", room: "Living", x: 864, y: 24 },
  { id: "M026", type: "motion", size: "small", room: "Living", x: 628, y: 72 },
  { id: "M008", type: "motion", size: "small", room: "Living", x: 559, y: 227 },
  { id: "M004", type: "motion", size: "small", room: "Living", x: 675, y: 228 },
  { id: "M027", type: "motion", size: "small", room: "Living", x: 806, y: 506 },
  { id: "M003", type: "motion", size: "small", room: "Living", x: 759, y: 725 },
  { id: "M009", type: "motion", size: "small", room: "Living", x: 494, y: 398 },

  // Hall / transitions
  { id: "M019", type: "motion", size: "small", room: "Hallway", x: 437, y: 310 },
  { id: "M013", type: "motion", size: "small", room: "Hallway", x: 346, y: 377 },
  { id: "M011", type: "motion", size: "small", room: "Hallway", x: 492, y: 612 },
  { id: "M010", type: "motion", size: "small", room: "Hallway", x: 591, y: 610 },

  // Middle-left rooms
  { id: "M025", type: "motion", size: "small", room: "Bathroom", x: 190, y: 444 },
  { id: "M018", type: "motion", size: "small", room: "Bathroom", x: 321, y: 537 },
  { id: "M017", type: "motion", size: "small", room: "Bathroom", x: 433, y: 539 },

  // Southwest room
  { id: "M024", type: "motion", size: "small", room: "Office", x: 140, y: 717 },

  // South bedroom
  { id: "M016", type: "motion", size: "small", room: "Bedroom", x: 393, y: 662 },
  { id: "M015", type: "motion", size: "small", room: "Bedroom", x: 372, y: 717 },
  { id: "M014", type: "motion", size: "small", room: "Bedroom", x: 371, y: 791 },
  { id: "M023", type: "motion", size: "small", room: "Bedroom", x: 470, y: 720 },
  { id: "M022", type: "motion", size: "small", room: "Bedroom", x: 519, y: 771 },
  { id: "M012", type: "motion", size: "small", room: "Bedroom", x: 591, y: 741 },
  { id: "T002", type: "temperature", room: "Hallway", x: 462, y: 583 },
  { id: "T001", type: "temperature", room: "Bedroom", x: 583, y: 766 },
  { id: "D003", type: "door", room: "Bedroom", x: 367, y: 825, orientation: "horizontal" },

  // Entrance (southeast)
  { id: "M002", type: "motion", size: "small", room: "Entrance", x: 959, y: 672 },
  { id: "M001", type: "motion", size: "small", room: "Entrance", x: 956, y: 796 },
  { id: "D002", type: "door", room: "Entrance", x: 900, y: 740, orientation: "vertical" },
  { id: "D001", type: "door", room: "Entrance", x: 960, y: 835, orientation: "horizontal" },
];
