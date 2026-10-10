# AmbiLiving — FYP Progress & Roadmap

**Project** F26-108-AmbiLiving — *Ambient-sensor human activity recognition and caregiver monitoring*
**Team** Aleeza Azhar · Hudiya e Zehra · Ibrahim Babar
**Supervisor** Dr. Labiba Fahad
**Status date** 10 October 2026

---

## 1. What the project is

Elderly residents who want to stay in their own homes cannot be watched continuously by family
or caregivers. Cameras are intrusive; wearables depend on the resident remembering to wear them.
AmbiLiving uses **passive ambient sensors** (motion, door, temperature) already embedded in the
home, recognises the resident's **daily activities** from the raw sensor stream, flags **deviations
from their normal routine**, and presents the result to a caregiver as actionable insight.

The gap we are closing: existing products (Zemplee Sense, OdeCare) report *which sensor fired and
when*. They do not report *what the resident was doing*. Our pipeline:

```
Ambient sensors → HAR model → recognised activity → routine deviation → caregiver insight
```

**Datasets** CASAS (Washington State University) — Aruba (1 resident, 6,477 activity instances,
11 classes, 2010–2011) and Milan (1 resident + pet, 2,353 instances, 15 classes, 2009).

---

## 2. Where we are right now

Two tracks exist in this repository and both have real substance:

| Track | Location | State |
|---|---|---|
| **Research / ML** — HAR model comparison | [ml/](ml/) | Framework complete; Approach 1 fully evaluated on Aruba. Approaches 2 & 3 implemented but not yet archived. Anomaly detection not started. |
| **Product / PoC** — caregiver dashboard | [src/](src/) | All six screens built and interactive on mock data. Typecheck clean. Not yet connected to the ML track. |

**The single most urgent item is not technical: almost none of this work is committed to git.**
The repository has one commit (`3a2cf91 Initial commit from Create Next App`). Everything
described below is untracked or unstaged working-tree state. See [§6](#6-immediate-housekeeping).

---

## 3. Done

### Iteration 1 — Research & Planning ✅ Complete

| Owner | Task | Evidence |
|---|---|---|
| Member 1 | Dataset exploration, sensor/activity/preprocessing analysis | [scripts/analyze_aruba.py](scripts/analyze_aruba.py), class distributions in the defense slides |
| Member 2 | Shortlist HAR + anomaly-detection approaches | Literature table (Zhao 2026, Cejudo 2025, Fahad & Tahir 2020); three approaches chosen |
| Member 3 | System requirements, architecture, dashboard & alert design | [smart-home-activity-recognition-poc-spec.md](smart-home-activity-recognition-poc-spec.md) — a full 17-section PoC specification |

Also delivered in this phase: the Complex Computing Problem justification, the overlapping-activity
problem statement (Meal_Preparation vs Wash_Dishes fire the *same* sensors in the *same*
proportions), the evaluation plan, risk register, and the DEI / ethics / legal analysis.

### Iteration 2 — Experimentation & Model Comparison 🟡 In progress

**The shared experiment framework is done** — this was the hard part, and it means all three
approaches are compared on identical data, identical splits and identical metrics.

- [ml/har/data.py](ml/har/data.py) — CASAS parser. Normalises corrupted Aruba states
  (`ONc`, `OFF5`, `OFcF`, `28.55c`), drops non-sensor lines, and pairs `begin`/`end` annotations
  **per activity name** — necessary because Milan has 421 activities that begin while another is
  still open, which a single global stack would mis-pair. Output: Aruba 6,476 segments / 11 classes,
  Milan 2,352 segments / 15 classes.
- [ml/har/features.py](ml/har/features.py) — two representations from one segment definition:
  ~160 hand-crafted features (cyclic time-of-day, weekday, duration, event rate, per-sensor event
  share, first/last sensor, transitions) and token-encoded event sequences
  (`<sensor>_<state>` + time gap + time since start + time of day).
- [ml/har/models/classical.py](ml/har/models/classical.py) — Approach 1: Random Forest, HistGradientBoosting.
- [ml/har/models/sequence.py](ml/har/models/sequence.py) — Approaches 2 & 3: BiLSTM, multi-width 1D-CNN,
  Transformer encoder. All share one input encoding and one classifier head, so the comparison is fair.
- [ml/har/train.py](ml/har/train.py) — shared neural training loop: sqrt-inverse-frequency class
  weights, label smoothing 0.05, AdamW, early stopping on a 10% validation slice **of the training
  fold** (the test fold is never used for model selection).
- [ml/har/evaluate.py](ml/har/evaluate.py) / [ml/har/compare.py](ml/har/compare.py) — every run writes
  `metrics.json`, `per_class.csv`, `confusion.png`, `predictions.csv`; `compare.py` rebuilds
  [ml/results/summary.md](ml/results/summary.md) from all runs on disk.
- Two evaluation protocols: `--split cv` (stratified 5-fold, comparable to the papers) and
  `--split temporal` (first 70% of days train, last 30% test — closer to deployment).

**Results archived so far** (Aruba, 5-fold CV, 6,476 segments, 11 classes):

| Approach | Accuracy | **Macro-F1** | Weighted-F1 | Time |
|---|---|---|---|---|
| 1 — Features + Gradient Boosting | 96.26 ± 0.25 | **84.52 ± 4.24** | 95.92 ± 0.26 | 19 s |
| 1 — Features + Random Forest | 96.36 ± 0.24 | **83.15 ± 4.14** | 95.88 ± 0.26 | 23 s |

Macro-F1 is our headline metric: accuracy is dominated by Relax (2,919) and Meal_Preparation
(1,606), so it hides exactly the failures we care about.

**This is already competitive** — Fahad & Tahir (2020) report 96.19% accuracy on Aruba; we are at
96.3% with a far simpler model. But the per-class breakdown shows the real story:

| Activity | Support | RF recall | HGB recall | Reading |
|---|---|---|---|---|
| Relax, Sleeping, Eating, Bed_to_Toilet, Work | 171–2,919 | 1.00 | ≥0.99 | Solved |
| Meal_Preparation | 1,606 | 0.999 | 0.994 | Solved |
| Housekeeping | 33 | 0.94 | 0.94 | Good |
| Enter_Home / Leave_Home | 431 / 431 | 0.83 / 0.79 | 0.83 / 0.78 | **Confused with each other** |
| Respirate | 6 | 0.50 | 0.67 | Too few instances to learn |
| **Wash_Dishes** | 65 | **0.03** | **0.09** | **Essentially undetected** |

Wash_Dishes is the overlapping-activity problem from the defense slides, confirmed numerically:
it fires M015/M017/M018/M019 in nearly the same proportions as Meal_Preparation, and the model
absorbs it into the majority class. **Fixing this is the core research contribution of
Iteration 2** — it is precisely the "no obvious solution" characteristic we claimed as our CCP.

### Product PoC — delivered ahead of schedule ✅

Iteration 3 assigns dashboard development to Member 3; a high-fidelity functional PoC already
exists (~3,700 lines of TypeScript, Next.js 16 / React 19 / Tailwind v4). All 12 acceptance
criteria in the spec are met:

- **Dataset-agnostic architecture**, which was the spec's central demand.
  [src/types/home.ts](src/types/home.ts) defines generic domain types (`HomeEnvironment`,
  `SensorDefinition`, `SensorEvent`, `RecognizedActivity`, `AnomalyRecord`);
  [src/data/homes.ts](src/data/homes.ts) is a registry of environment configs. No component knows
  it is rendering Aruba — adding Kasteren means adding data, not changing UI.
- **Monitoring page** ([src/app/(app)/monitoring/page.tsx](src/app/(app)/monitoring/page.tsx)) — the
  centrepiece. Time-controlled floor plan: zoom/pan, play/pause/step, draggable timeline, sensor
  state derived from the event stream at the current timestamp, hover/click sensor detail panel,
  "show sensor IDs" toggle, switchable raster-reference / SVG base layer.
- **Floor plans and sensor coordinates** — 40 Aruba sensors and 32 Milan sensors positioned in the
  SVG coordinate system, derived from the reference images by the computer-vision helpers in
  [scripts/](scripts/) (`detect_sensors.py`, `detect_markers.py`, `detect_gray_markers.py`,
  `calibrate_sensors.py`, `grid_aruba.py`) rather than placed by hand.
- **Dashboard** — current activity, recent activities, today's count, anomalies needing attention.
  Deliberately *not* a metrics screen, per spec §7.
- **Activity History**, **Anomalies** (caregiver-readable: observed vs expected vs reason, no raw
  scores), **Homes/Environments**, **Settings**, plus a landing page and persistent sidebar/header
  with the environment selector.
- Mock data is centralised in [src/data/homes/](src/data/homes/) in shapes that map 1:1 onto future
  API responses: 59 Aruba / 46 Milan sensor events, 11 / 15 activity-history entries, 3 anomalies each.
- `npx tsc --noEmit` passes clean.

---

## 4. To do

### Iteration 2 — finish the comparison

- [ ] **Run Approaches 2 and 3 to completion and archive the results.** Only `aruba/cv/rf` and
      `aruba/cv/hgb` exist on disk. BiLSTM, CNN and Transformer are implemented but have no
      archived run. Target: every model × {aruba, milan} × {cv, temporal}.
- [ ] **Run the `temporal` split for everything.** No temporal results exist yet. This is the
      honest, deployment-like number and the one a reviewer will ask about.
- [ ] **Attack the Wash_Dishes / Enter_Home-vs-Leave_Home failures.** Candidate directions:
      sensor-transition and ordering features, duration priors, hierarchical or two-stage
      classification within the kitchen-sensor group, over/under-sampling, focal loss,
      or the GAN-based augmentation Zhao et al. (2026) use for exactly this problem.
- [ ] **Per-member hyper-parameter tuning**, on training folds only — none has been done yet.
- [ ] **Use the temperature sensors.** They are parsed and kept but currently unused.
- [ ] **Regenerate [ml/results/summary.md](ml/results/summary.md)** — it is stale. It lists Milan
      BiLSTM/Transformer rows whose result directories no longer exist, and omits the `hgb` run
      that does. One `py -m har.compare` fixes it.
- [ ] **Write up the comparison and select the winning approach** — the Iteration 2 milestone.
      Report Accuracy, Precision, Recall and F1 per the evaluation plan, with confusion analysis.

### Iteration 3 — integration

- [ ] **Online / sliding-window inference.** Everything so far assumes activity boundaries are
      known (explicit segmentation), because the ground-truth `begin`/`end` labels provide them.
      A live dashboard has no such labels: it must classify the last N events at every new event.
      This is flagged in [ml/README.md](ml/README.md) and is **the single biggest gap between the
      research track and the product**. It also changes the metrics — expect lower numbers, and
      plan to report both settings.
- [ ] **Anomaly detection — not started.** Out of scope for Iteration 2 and absent from `ml/`.
      Needs: a definition of "normal routine" per resident, a deviation model (the shortlisted
      literature uses autoencoders and RNN-based routine models), and a translation layer that
      turns a score into caregiver-readable text. The PoC's `AnomalyRecord` shape
      (observed / expected / reason / severity) is the contract to fill.
- [ ] **Alert logic** — trigger rules, severity, and the false-alert-rate / response-time
      measurement promised in the evaluation plan.
- [ ] **Backend API.** Decide FastAPI vs Next.js route handlers, then serve: environment config,
      sensor stream, recognised activities, anomalies. The frontend types are already
      API-shaped, so this is mostly serialisation.
- [ ] **Replace the frontend mock data with real model output** and prove criterion 4 (sensor state
      follows the timestamp) against a real log rather than a 59-event mock.
- [ ] **Researcher / Evaluation view** (spec §13) — surface accuracy, precision, recall, F1,
      per-class performance and confusion analysis for the research audience, kept clearly
      separate from the caregiver product. Currently the 84.5% Aruba result lives only in
      `ml/results/` and is invisible in the app.
- [ ] **Kasteren as a third environment** (spec §12, optional) — add it as an evaluation-only
      placeholder. `HomeStatus` already supports `"placeholder"` but no home uses it.
- [ ] **End-to-end integration testing** of Sensor Data → HAR → Anomaly → Alerts & Dashboard.

### Final deliverables

- [ ] Deployment outside the development environment (an explicit success criterion).
- [ ] Reliability and response-time measurement.
- [ ] Performance evaluated across *both* homes and across activity patterns — the DEI commitment
      to check for unequal performance across user/activity patterns. Milan is the harder home;
      do not report Aruba alone.
- [ ] Final report, documentation, and the ethics/legal section (data minimisation, CASAS licensing
      compliance, human oversight before any high-stakes decision).

---

## 5. Risks, honestly stated

| Risk | Current reality |
|---|---|
| **Uncommitted work** | One commit in the repo. A disk failure loses the entire project today. |
| **Overlapping activities** | Confirmed, not solved. Wash_Dishes recall is 3–9%. Named as our CCP; a reviewer will ask. |
| **Milan is much harder** | Earlier Milan runs reached only ~29% macro-F1 against ~63% accuracy. 15 classes, pet-contaminated motion data. Zhao et al. report ~80% accuracy on Milan, so there is real headroom — and a real gap to explain. |
| **CV split is optimistic** | Stratified CV lets segments from the same day fall in both train and test. Already acknowledged in the code; the `temporal` split is implemented but unrun. |
| **Explicit segmentation** | Reported numbers assume known activity boundaries. The deployed system will not have them. |
| **Research → product gap** | The two tracks do not touch. Nothing in `src/` reads anything from `ml/results/`. |
| **Rare classes** | Respirate has 6 instances total. No amount of modelling fixes that; say so rather than hiding it in a macro average. |

---

## 6. Immediate housekeeping

1. **Commit everything.** Highest-value action available. Suggested breakdown: the ML pipeline,
   the frontend PoC, the floor-plan assets and CV scripts, the spec, and the results.
2. Regenerate `ml/results/summary.md` (stale, as above).
3. Replace the create-next-app boilerplate in [README.md](README.md) with a real project README.
4. Delete [src/components/ui/PagePlaceholder.tsx](src/components/ui/PagePlaceholder.tsx) — defined,
   never imported, left over from scaffolding.
5. `python` on this machine resolves to the Microsoft Store stub; the `py` launcher works. Use
   `py -m har.run ...` or create a venv in `ml/`.

---

## Appendix — commands

**Frontend** (from the repo root)

```bash
npm run dev          # dev server on :3000
npm run build
npm run lint
npx tsc --noEmit     # typecheck (currently clean)
```

**ML** (from `ml/`; raw CASAS files go in `ml/data/raw/`, git-ignored)

```bash
py -m pip install -r requirements.txt
py -m har.data aruba milan                     # parse + class statistics
py -m har.run --dataset aruba --model rf       # one experiment
py -m har.run --dataset all --model all        # full comparison (~1–1.5 h CPU)
py -m har.run --dataset milan --model bilstm --split temporal --verbose
py -m har.compare                              # rebuild results/summary.md
```

Each run writes `ml/results/<dataset>/<split>/<model>/` containing `metrics.json`,
`per_class.csv`, `confusion.png` and `predictions.csv`.
