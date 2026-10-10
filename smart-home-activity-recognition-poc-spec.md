# Build a high-fidelity functional PoC for a smart-home activity recognition and monitoring platform.

**IMPORTANT CONTEXT:**
The attached image is the Aruba CASAS smart-home floor plan and must be used as the visual reference for the Aruba environment. Do NOT redesign the floor plan arbitrarily. Recreate/trace it as an interactive SVG or use the image as a base layer with a precisely aligned SVG/HTML sensor overlay.

This is a PoC, NOT the actual ML implementation. The UI should be highly detailed and interactive, but backend/ML results can be mocked. Do not implement actual activity-recognition models.

---

## 1. Technology Decisions

**Frontend:**
- React
- TypeScript
- Tailwind CSS
- shadcn/ui where useful
- Recharts only for conventional charts
- react-zoom-pan-pinch for floor-plan zoom/pan

**Backend:**
- FastAPI/Python only if an API layer is useful.
- For this PoC, mock JSON data is sufficient.
- Keep the data structures compatible with a future FastAPI/ML backend.

**Do NOT use:**
- Leaflet
- Mapbox
- GIS/map libraries
- a heavy 3D engine

The floor plan is a 2D indoor diagram, not a geographic map.

---

## 2. Core Architectural Principle

The product must be DATASET/HOME AGNOSTIC.

Aruba is currently the primary research/evaluation dataset, but the final product is intended to support multiple smart-home environments such as Aruba, Milan, and potentially Kasteren.

Therefore NEVER hard-code Aruba-specific logic into React components.

Separate:

- A. Environment configuration
- B. Floor-plan visualization
- C. Sensor metadata
- D. Timestamped sensor events
- E. Recognized activities
- F. Anomalies
- G. UI

**Conceptual architecture:**

```
Home Environment
    |
    +-- floorPlan
    +-- sensors
    +-- activities
    +-- sensor events
    +-- monitoring data
    |
    v
Generic React visualization
```

**Example:**

```
/data
  /homes
    aruba.json
    milan.json
    kasteren.json

/floorplans
    aruba.svg
    milan.svg
    kasteren.svg
```

The React floor-plan component should receive:
- floorPlan
- sensors
- currentSensorStates
- timestamp

It must not know that it is displaying Aruba.

---

## 3. Floor Plan Architecture

Use SVG as the floor-plan representation.

The SVG should represent STATIC physical information:

- walls
- rooms
- doors
- furniture/major physical structures where useful
- fixed sensor positions if desired as reference points

Do NOT encode dynamic sensor state directly into the SVG.

Dynamic sensor state must be rendered by React as an overlay.

**Conceptually:**

```
    Static SVG floor plan
             +
    React sensor overlay
             +
    current timestamp
             =
    current monitoring view
```

Every sensor must have coordinates in the same coordinate system as the SVG.

**Example data:**

```json
{
  "id": "M015",
  "type": "motion",
  "size": "large",
  "room": "Kitchen",
  "x": 80,
  "y": 63
}
```

Do this for every Aruba sensor visible in the supplied floor-plan image.

The exact coordinates should be aligned visually with the attached reference image.

---

## 4. Sensor Types

The supplied Aruba floor plan contains different sensor types.

Represent them semantically:

- Motion sensors
- Door sensors
- Temperature sensors

Do NOT treat all sensors as simple ON/OFF devices.

- **Motion:** ACTIVE / INACTIVE
- **Door:** OPEN / CLOSED
- **Temperature:** display a temperature value

The UI should visually distinguish sensor types.

Use a clean modern visual language rather than reproducing the original diagram's tiny labels and legend exactly.

**Default monitoring view:**
- active sensors are visually prominent
- inactive sensors are muted
- sensor ID appears on hover/click
- avoid displaying every sensor ID permanently because it creates visual clutter

Provide a "Show sensor IDs" option if practical.

---

## 5. Timestamped Sensor Visualization

The central feature of the Monitoring page is a time-controlled floor plan.

Provide:

- current timestamp
- timeline
- play/pause
- previous/next event controls if practical
- draggable timeline
- sensor states update as the timestamp changes

**Mock sensor-event data should look conceptually like:**

```json
[
  {
    "timestamp": "10:42:13",
    "sensorId": "M015",
    "state": "active"
  },
  {
    "timestamp": "10:42:14",
    "sensorId": "M019",
    "state": "active"
  }
]
```

When the user changes the timestamp, calculate/render the sensor states appropriate to that timestamp.

When Play is pressed, advance through the mock event sequence and update the floor plan.

The goal is to make the floor plan look like a visualization of a real sensor stream rather than a static image.

---

## 6. Main Application Structure

Use a persistent sidebar and top navigation/header.

**Main sections:**

1. Dashboard
2. Monitoring
3. Activity History
4. Anomalies
5. Homes / Environments
6. Settings

Top bar should contain an environment selector:

```
Monitoring Environment
[ Aruba Home v ]
```

Changing the environment should conceptually change:

- floor plan
- sensor configuration
- available activity classes
- activity history
- monitoring data
- anomaly data

Do NOT create separate hard-coded dashboards for Aruba/Milan/etc.

---

## 7. Dashboard

The caregiver-facing dashboard should answer:

"What is happening in the home and does anything require attention?"

**Show:**

- current home/environment
- current recognized activity
- recent activities
- today's activity count
- anomalies requiring attention
- recent activity timeline
- latest anomaly

Do NOT make model comparison or ML metrics the focus of the caregiver dashboard.

The caregiver should see useful results, not:
"Model A = 92%, Model B = 94%."

---

## 8. Monitoring Page — Most Important Screen

Make this the centerpiece of the PoC.

**Layout:**

```
--------------------------------------------------
Monitoring                         Aruba Home v
--------------------------------------------------

              10:42:15 AM

    +--------------------------------+
    |                                |
    |        INTERACTIVE             |
    |        ARUBA FLOOR PLAN        |
    |                                |
    |   active/inactive sensors      |
    |                                |
    +--------------------------------+

    Current Activity
    Meal Preparation
    Confidence: 94%

    Active Sensors:
    M015  M019  M023

--------------------------------------------------
Sensor/Event Timeline
--------------------------------------------------
10:40 ---- 10:41 ---- 10:42 ---- 10:43
                         ^
                       cursor

[Play] [Pause] [Previous] [Next]
```

The floor plan should support:
- zoom
- pan
- hover sensor
- click sensor
- tooltip
- active/inactive visualization
- synchronized timeline

---

## 9. Sensor Interaction

Clicking a sensor should open a small detail panel/popover:

```
Sensor:
M019

Type:
Motion

Room:
Kitchen

Current state:
ACTIVE

Last event:
10:42:14 AM

Events today:
37
```

Do not make this overly complex.

---

## 10. Activity History

Show recognized activities as a chronological table/timeline.

**Example:**

```
Time       Activity              Duration
10:42      Meal Preparation      31 min
09:57      Eating                18 min
08:30      Work                  52 min
```

Clicking an activity opens details:

- activity name
- start/end time
- duration
- sensors involved
- confidence
- relevant sensor sequence

---

## 11. Anomalies

Anomalies are a separate product concept from activity recognition.

Show caregiver-readable anomalies such as:

```
"Unusual Meal Preparation Duration"

Observed:
94 min

Expected:
20–45 min

Reason:
Unusual duration
```

or:

```
"Irregular sensor sequence"
```

Do NOT expose raw mathematical anomaly scores as the primary user-facing explanation.

The research system may eventually calculate those scores, but the PoC should translate them into understandable results.

---

## 12. Homes / Environments

Create a Homes/Environments page.

**Example:**

```
Aruba Home
- 11 activities
- 1 resident
- Aruba floor plan
- Active

Milan Home
- 15 activities
- 1 resident + pet
- Milan floor plan
- Evaluation environment

Kasteren Home
- Evaluation environment / optional
- Do not imply it is operational if no real data is available
```

These are examples of configurations, not separate applications.

---

## 13. Research vs Product

Keep research evaluation separate from the caregiver product.

If an evaluation screen is included, make it an "Evaluation" / researcher/admin view.

**It can show:**

- model
- accuracy
- precision
- recall
- F1
- per-class performance
- confusion analysis

But this should NOT be presented as a caregiver feature.

**The product architecture is:**

```
Sensor Data
    |
Recognition
    |
Recognized Activity
    |
Anomaly Detection
    |
Caregiver Interface
```

**The research architecture is:**

```
Dataset
    |
Preprocessing
    |
Models / approaches
    |
Systematic evaluation
    |
Best-supported approach
    |
Integration into product
```

---

## 14. Mock Data Architecture

Do not scatter fake values throughout React components.

Centralize all mock data.

**For example:**

```
/src/data/
    homes.ts
    sensors.ts
    activities.ts
    sensorEvents.ts
    anomalies.ts
```

or JSON equivalents.

**Environment configuration should look conceptually like:**

```json
{
  "id": "aruba",
  "name": "Aruba Home",
  "floorPlan": "/floorplans/aruba.svg",
  "sensors": [...],
  "activities": [...],
  "events": [...]
}
```

This makes it straightforward to replace mock data with FastAPI/ML results later.

---

## 15. Visual Design

Aim for a polished professional healthcare/smart-home monitoring product.

**Prioritize:**
- clean spacing
- strong hierarchy
- readable typography
- restrained use of color
- clear active/inactive states
- accessible contrast
- professional dashboard appearance

**Avoid:**
- excessive gradients
- excessive animations
- futuristic "AI" aesthetics
- unnecessary 3D
- cluttered sensor labels
- fake metrics everywhere

The product should look like something a caregiver could realistically use.

---

## 16. Important Scope Limit

This is a HIGH-FIDELITY FUNCTIONAL PoC.

Implement interaction and navigation convincingly, but do NOT implement:

- actual deep-learning models
- actual anomaly detection algorithms
- real-time sensor hardware
- production authentication
- production database
- model training
- real deployment infrastructure

Mock those layers cleanly.

The objective is to demonstrate the intended product behavior and architecture.

---

## 17. Acceptance Criteria

The PoC is successful if:

1. I can switch between home environments.
2. The correct floor plan is loaded for the selected environment.
3. Sensors are positioned correctly on the floor plan.
4. Sensor state changes according to the selected timestamp.
5. I can play through a sequence of sensor events.
6. I can hover/click sensors and see their details.
7. The current recognized activity is displayed.
8. Activity history is accessible.
9. Anomalies are displayed separately.
10. The application does not hard-code Aruba-specific logic into generic components.
11. Adding another floor plan should require adding configuration/data rather than redesigning the UI.
12. The overall interface looks like a coherent finished product rather than a collection of disconnected demo screens.

---

Start by inspecting the attached Aruba floor-plan image carefully and use it as the authoritative reference for room layout and sensor placement. Build the reusable environment/floor-plan architecture first, then build the monitoring interaction around it.
