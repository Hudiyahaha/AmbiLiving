import type { HomeEnvironment } from "@/types/home";
import { arubaActivityClasses } from "@/data/homes/arubaMock";
import { arubaSensors } from "@/data/homes/arubaSensors";
import { milanActivityClasses } from "@/data/homes/milanMock";
import { milanSensors } from "@/data/homes/milanSensors";
import {
  arubaRealDay,
  milanRealDay,
  toRealDay,
  type ExportedDay,
} from "@/data/homes/realData";
import {
  arubaRealAnomalies,
  milanRealAnomalies,
  toRealAnomalies,
  type ExportedAnomalies,
} from "@/data/homes/realAnomalies";

// Sensor events and recognised activities are one real dataset day with model
// predictions (see realData.ts). Anomalies are the routine model's alerts on the
// real monitoring days of each home (see realAnomalies.ts).
const aruba = arubaRealDay(arubaActivityClasses);
const milan = milanRealDay(milanActivityClasses);

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
    events: aruba.events,
    activityHistory: aruba.activityHistory,
    anomalies: arubaRealAnomalies.anomalies,
    anomalySource: arubaRealAnomalies.source,
    currentActivityId: aruba.currentActivityId,
    dataSource: aruba.dataSource,
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
    events: milan.events,
    activityHistory: milan.activityHistory,
    anomalies: milanRealAnomalies.anomalies,
    anomalySource: milanRealAnomalies.source,
    currentActivityId: milan.currentActivityId,
    dataSource: milan.dataSource,
    datasetStats: {
      activityInstances: 2353,
      activityClasses: 15,
      dataPeriod: "Daily life, 2009",
    },
  },
];

export const DEFAULT_HOME_ID = "aruba";

/**
 * The same home with its day and anomalies taken from the API (`/homes/{id}/day`,
 * `/homes/{id}/anomalies`) instead of the bundled files. Both go through the
 * transforms used for the bundled files, so pages see the same shapes.
 */
export function withApiData(
  home: HomeEnvironment,
  day: ExportedDay,
  anomalies: ExportedAnomalies,
): HomeEnvironment {
  const dataset = home.dataSource?.dataset ?? home.name;
  const real = toRealDay(day, dataset, home.activityClasses);
  const found = toRealAnomalies(anomalies);
  return {
    ...home,
    events: real.events,
    activityHistory: real.activityHistory,
    currentActivityId: real.currentActivityId,
    dataSource: real.dataSource,
    anomalies: found.anomalies,
    anomalySource: found.source,
  };
}

export function getHomeById(id: string): HomeEnvironment | undefined {
  return homes.find((home) => home.id === id);
}
