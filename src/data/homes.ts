import type { HomeEnvironment } from "@/types/home";
import {
  arubaActivityClasses,
  arubaActivityHistory,
  arubaAnomalies,
  arubaEvents,
} from "@/data/homes/arubaMock";
import { arubaSensors } from "@/data/homes/arubaSensors";
import {
  milanActivityClasses,
  milanActivityHistory,
  milanAnomalies,
  milanEvents,
} from "@/data/homes/milanMock";
import { milanSensors } from "@/data/homes/milanSensors";

/**
 * Centralized environment registry (Aruba + Milan from CASAS / defense slides).
 */
export const homes: HomeEnvironment[] = [
  {
    id: "aruba",
    name: "Aruba Home",
    status: "active",
    summary:
      "CASAS Aruba · ambient sensor events and annotated daily activities (2010–2011)",
    residentLabel: "1 resident",
    activityCount: arubaActivityClasses.length,
    floorPlan: {
      src: "/floorplans/aruba-crop-920.png",
      viewBox: { width: 910, height: 646 },
      referenceSrc: "/floorplans/aruba-crop-920.png",
      vectorSrc: "/floorplans/aruba.svg",
    },
    sensors: arubaSensors,
    activityClasses: arubaActivityClasses,
    events: arubaEvents,
    activityHistory: arubaActivityHistory,
    anomalies: arubaAnomalies,
    currentActivityId: "aruba-relax-1",
    datasetStats: {
      activityInstances: 6477,
      activityClasses: 11,
      dataPeriod: "Daily life activities, 2010–2011",
    },
  },
  {
    id: "milan",
    name: "Milan Home",
    status: "active",
    summary:
      "CASAS Milan · sensor readings during daily activities (2009) · 1 resident + pet",
    residentLabel: "1 resident + pet",
    activityCount: milanActivityClasses.length,
    floorPlan: {
      src: "/floorplans/milan-reference.png",
      viewBox: { width: 1024, height: 848 },
      referenceSrc: "/floorplans/milan-reference.png",
      vectorSrc: "/floorplans/milan.svg",
    },
    sensors: milanSensors,
    activityClasses: milanActivityClasses,
    events: milanEvents,
    activityHistory: milanActivityHistory,
    anomalies: milanAnomalies,
    currentActivityId: "milan-tv",
    datasetStats: {
      activityInstances: 2353,
      activityClasses: 15,
      dataPeriod: "Daily life, 2009",
    },
  },
];

export const DEFAULT_HOME_ID = "aruba";

export function getHomeById(id: string): HomeEnvironment | undefined {
  return homes.find((home) => home.id === id);
}
