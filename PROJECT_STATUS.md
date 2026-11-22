# AmbiLiving — FYP Progress & Roadmap

**Project** F26-108-AmbiLiving — *Ambient-sensor human activity recognition and caregiver monitoring*
**Team** Aleeza Azhar · Hudiya e Zehra · Ibrahim Babar
**Supervisor** Dr. Labiba Fahad
**Status date** 19 November 2026 (previous updates: 18 November, 10 October 2026)

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

**Datasets** CASAS (Washington State University) — Aruba (1 resident, 6,476 activity segments,
11 classes, 2010–2011) and Milan (1 resident + pet, 2,352 segments, 15 classes, 2009–2010).

---

## 2. Where we are right now

| Track | Location | State |
|---|---|---|
| **Research / ML** — activity recognition | [ml/](ml/) | **Done for both settings.** All five models run on both homes under both protocols, with 3-seed repeats. Known-boundary (segment) results are ~92–95 macro-F1; the live sliding-window setting is finished and a final model chosen (BiLSTM). |
| **Research / ML** — routine deviation + alerts | [ml/har/anomaly.py](ml/har/anomaly.py), [alerts.py](ml/har/alerts.py) | **Done and evaluated.** Per-resident routine model (8 aspects incl. weekly drift) vs a generic anomaly-detection baseline, on three activity streams; alert routing (notify / evening summary / dashboard). Results: [anomaly.md](ml/results/anomaly.md), [alerts.md](ml/results/alerts.md). |
| **Product / PoC** — caregiver dashboard | [src/](src/) | All six screens built. Monitoring and activity history play back **one real CASAS day per home** with model predictions; anomalies are the routine model's alerts on real days. Data comes from the backend API, with the bundled files as fallback. Typecheck clean. |
| **Backend** | [ml/api/](ml/api/) | **Started (22 Nov, D16).** FastAPI service: homes, exported day and anomalies, replay scenarios streamed live (server-sent events), live recognition with the saved BiLSTM. Tests in `ml/tests/`. The dashboard uses it (ROADMAP 4.4): every page loads from the API, and Monitoring shows the live BiLSTM's answer for the last 100 events at the playback position. |
| **Poster** | [poster/](poster/) | Draft rendered to `AmbiLiving-Poster.pdf`. Concept/architecture only, no results yet (ROADMAP 6.5). |

**Git state.** All ML and app work is on `main` (PR #1 `babar`, 18 Oct; PRs #2 and #3 `aleeza`,
14–18 Nov, including the final sliding-window results). Working branch for the roadmap and paper
tracking: `hudiya`.

**What to do next, in order:** [ROADMAP.md](ROADMAP.md). **Paper tracking:** [paper/](paper/).

---

## 3. Done

### Iteration 1 — Research & Planning ✅ Complete

| Owner | Task | Evidence |
|---|---|---|
| Member 1 | Dataset exploration, sensor/activity/preprocessing analysis | [scripts/analyze_aruba.py](scripts/analyze_aruba.py), class distributions in the defense slides |
| Member 2 | Shortlist HAR + anomaly-detection approaches | Literature table (Zhao 2026, Cejudo 2025, Fahad & Tahir 2020); three approaches chosen |
| Member 3 | System requirements, architecture, dashboard & alert design | [smart-home-activity-recognition-poc-spec.md](smart-home-activity-recognition-poc-spec.md) — a full 17-section PoC specification |

### Iteration 2 — Experimentation & Model Comparison ✅ Complete

**Shared framework** ([ml/har/](ml/har/)): CASAS parser with per-activity begin/end pairing
(`data.py`), hand-crafted features and token sequences (`features.py`), RF / Gradient Boosting
(`models/classical.py`), BiLSTM / 1D-CNN / Transformer (`models/sequence.py`), shared training loop
(`train.py`), evaluation and summary tables (`evaluate.py`, `compare.py`, `experiments.py`,
`rescore.py`). Two protocols: stratified 5-fold CV and a temporal split (first 70% of days train,
last 30% test). Macro-F1 ignores activities absent from the test set (fixed and rescored 13 Oct).

**Every model × {Aruba, Milan} × {cv, temporal} is archived** in [ml/results/summary.md](ml/results/summary.md),
with 3-seed repeats and a learning-rate tuning pass (lr 3e-4) in [ml/results/experiments.md](ml/results/experiments.md).

**Two feature additions solved the overlap problems from the defense slides:**

- **Pre-segment context** (`--context`): gap since the previous event, events and distinct sensors in
  the 10 minutes before. Past-only, so it works live. Fixes Enter_Home vs Leave_Home on Aruba
  (F1 0.81 → 0.98 each).
- **Activity history** (`--history`): a two-stage model. Stage 1 recognises each segment; its
  *predictions* (never ground-truth labels) become routine features — time since each activity
  last ended, whether it was the most recent, how often it happened today. Wash_Dishes usually
  follows a meal, so on Aruba cv its recall goes 0.06 → 0.42 (F1 0.10 → 0.50).

**Best results, known activity boundaries** (macro-F1 %, single run unless noted):

| | Aruba cv | Aruba temporal | Milan cv | Milan temporal |
|---|---|---|---|---|
| Best model | GB + ctx + history | GB + ctx | GB + ctx + history | BiLSTM |
| Macro-F1 | **92.92 ± 3.74** | **92.75** (3 seeds: 90.19 ± 1.05) | **92.52 ± 1.73** | **93.55** (3 seeds: 94.89 ± 0.79) |
| Accuracy | 98.98 | 99.17 | 97.45 | 94.78 |

Findings worth stating in the report:

1. All approaches land within a few points of each other; **the representation matters more than the
   architecture** (context adds ~3 points to every model on Aruba).
2. Gradient Boosting is the strongest or close to it and runs in seconds, against minutes for the
   BiLSTM/CNN and hours for the Transformer on CPU.
3. History helps on cv but **not on the temporal split** — Aruba's last 30% of days has only 6
   Wash_Dishes labels because annotation of it fades out from March 2011.
4. Milan, which looked much harder in early runs (~29 macro-F1 in October), now scores on par with Aruba.

### Iteration 3 (ML side) — live sliding-window recognition ✅ Complete

The live product has no activity boundaries. `har.run_windows` ([ml/har/windows.py](ml/har/windows.py),
[ml/har/run_windows.py](ml/har/run_windows.py), [ml/har/window_history.py](ml/har/window_history.py))
classifies the **last 100 events at every event**, with a chronological 60/20/20 day split matching
the LastAct protocol (Liu et al., 2026) so results are comparable with published work.

Final results (macro-F1 %, mean ± std over 3 seeds; full table in [ml/results/windows.md](ml/results/windows.md)):

| Model | Aruba | Milan |
|---|---|---|
| **BiLSTM — chosen as the window model** | 41.9 ± 1.5 | **45.6 ± 0.6** |
| Gradient Boosting + routine history | **43.8 ± 0.4** | 37.9 (1 run) |
| Gradient Boosting | 39.1 ± 0.2 | 38.1 ± 1.0 |
| LastAct (reported) | 44.6 ± 1.9 | 40.1 ± 0.5 |
| DeepCASAS (reported by LastAct) | 38.6 | 36.7 |

- We **beat LastAct on Milan** and are within its error bar on Aruba (with GB + history).
- The model choice followed a rule fixed in advance: BiLSTM + history only if history helped on
  both homes. It did not (Milan 45.4 → 38.0), so the final model is plain BiLSTM.
- Smoothing over the last k windows always hurt; validation picked k = 1.
- With unannotated events labelled "Other" (the real product setting), GB reaches Aruba 51.3
  macro-F1 / 81.2 accuracy and Milan 35.3 (`window100-other/`).
- **These numbers are not comparable with the segment results above**, which get activity
  boundaries for free. Report both settings.

### Product PoC ✅ Built, partially connected

- Next.js 16 / React 19 / Tailwind v4, dataset-agnostic types ([src/types/home.ts](src/types/home.ts))
  and an environment registry ([src/data/homes.ts](src/data/homes.ts)).
- Screens: Dashboard, Monitoring (time-controlled floor plan with zoom/pan/playback and sensor
  detail), Activity History, Anomalies, Homes, Settings, plus a landing page.
- Floor plans with 40 Aruba / 32 Milan sensors positioned by the CV helpers in [scripts/](scripts/).
- **Real data:** `py -m har.export_dashboard` trains GB + context on the first 70% of days and
  exports one unseen test day per home to [src/data/homes/generated/](src/data/homes/generated/)
  ([realData.ts](src/data/homes/realData.ts) loads it), with per-activity confidence:
  - Aruba 2011-04-20 — 5,957 sensor events, 31 / 32 activities recognised correctly.
  - Milan 2010-01-03 — 9,126 sensor events, 64 / 67 correct.
  - Boundaries still come from the annotations; the dashboard does not yet run the window model.
- `npx tsc --noEmit` passes clean (checked 18 Nov).

---

## 4. To do

The ordered, step-by-step plan lives in **[ROADMAP.md](ROADMAP.md)** (single source of truth —
do not duplicate it here). In short:

0. Housekeeping — refresh `ml/README.md` tables, tag results (poster, README and cleanup done 22 Nov).
1. Freeze activity recognition — save trained models, per-class window table, confidence analysis.
2. ~~Routine-deviation detection~~ — done (D12–D14, E11–E14).
3. ~~Alert routing~~ — done (D15, E15).
   Open follow-ups: a fairer missed-meal injection (remove all kitchen movement, not only
   annotated cooking), better live recognition of Leave_Home / cooking / meds.
4. Integration — backend, live replay + inference, dashboard on real API data, researcher view.
5. System evaluation & deployment — end-to-end tests, latency, both-homes fairness, deploy.
6. Write-up — paper (tracked in [paper/](paper/)), final report, poster, demo.

---

## 5. Risks, honestly stated

| Risk | Current reality |
|---|---|
| **Live pipeline weak on Aruba** | Routine deviations are found 87–92 % of the time with annotated or segment-recognised activities, but only 16 % with the live BiLSTM on Aruba (63 % on Milan): live recognition errors corrupt the learned routine. Biggest technical risk now; frame it as a finding and as the next research step. |
| **Live accuracy is much lower** | ~42–46 macro-F1 in the window setting vs ~92 with known boundaries. Competitive with the literature, but a reviewer will see the gap; frame it with the LastAct comparison. |
| **Rare / overlapping classes** | Solved with known boundaries (history), not in the window setting. Respirate has 6 instances in total — say so rather than hiding it in a macro average. |
| **Label drift** | Aruba stops annotating Wash_Dishes from Mar 2011; Milan's test days are a holiday period (validation ~46 vs test ~38 for GB). Temporal per-class scores are noisy. |
| **History feedback loop** | History features use the model's own earlier predictions; one wrong recognition can affect the next in a live system. |
| **Research → product gap** | Narrower: the dashboard shows a real day and routine deviations found on real days, with how each was delivered. A live demo (`/live`) now replays days through the live BiLSTM and routine model, minute by minute (D17). A FastAPI backend now streams those replays and recognises activities from posted events (D16), and the dashboard reads from it (bundled files only as fallback), but the routine model does not yet run online. |

---

## Appendix — commands

**Frontend** (from the repo root)

```bash
npm run dev          # dev server on :3000 (reads the API at NEXT_PUBLIC_AMBILIVING_API, default http://127.0.0.1:8000)
npm run build
npm run lint
npx tsc --noEmit     # typecheck (currently clean)
```

**Backend** (from `ml/`; `py -m pip install -r requirements.txt` adds FastAPI and uvicorn)

```bash
py -m api                          # http://127.0.0.1:8000, interactive docs at /docs
py -m pytest tests -q              # backend tests (one needs ml/data/raw/aruba.txt)
```

**ML** (from `ml/`; raw CASAS files go in `ml/data/raw/`, git-ignored). On this machine `python`
resolves to the Microsoft Store stub; use the `py` launcher or a venv.

```bash
py -m pip install -r requirements.txt
py -m har.data aruba milan                                         # parse + class statistics
py -m har.run --dataset all --model hgb --context --history         # best segment model
py -m har.run --dataset milan --model bilstm --split temporal --verbose
py -m har.run_windows --dataset all --model bilstm --seeds 1 2 3    # live sliding-window model
py -m har.export_dashboard                                         # real day → src/data/homes/generated/
py -m har.compare                                                  # rebuild results/summary.md
```

Segment runs write `ml/results/<home>/<cv|temporal>/<model>/`; window runs write
`ml/results/<home>/window100-<last|other>/<tag>/`. Each holds `metrics.json`, `per_class.csv`,
`confusion.png` and `predictions.csv(.gz)`.
