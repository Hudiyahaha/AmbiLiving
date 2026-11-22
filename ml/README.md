# AmbiLiving - Human Activity Recognition (HAR)

Recognises daily activities from CASAS ambient-sensor logs (Aruba, Milan).
This is Iteration 2 of the FYP: implement several approaches on the same data
and compare them with the same protocol. Anomaly detection is out of scope here.

## Setup

```bash
cd ml
pip install -r requirements.txt
```

Put the raw CASAS files in `ml/data/raw/` (git-ignored):

```
ml/data/raw/aruba.txt
ml/data/raw/milan.txt
```

## Usage

All commands run from `ml/`.

```bash
python -m har.data aruba milan                     # parse + class statistics
python -m har.run --dataset aruba --model rf       # one experiment
python -m har.run --dataset all --model all        # full comparison (~1-1.5 h on CPU)
python -m har.run --dataset milan --model bilstm --split temporal --verbose
python -m har.run --dataset all --model all --context  # + pre-segment context features
python -m har.run --dataset all --model hgb --context --history  # + activity history (best)
python -m har.compare                              # rebuild results/summary.md
```

Each run writes `results/<dataset>/<split>/<model>/`:

| File | Contents |
|---|---|
| `metrics.json` | per-fold + mean/std accuracy, macro/weighted F1, macro P/R, config |
| `per_class.csv` | precision / recall / F1 / support per activity |
| `confusion.png` | row-normalised confusion matrix |
| `predictions.csv` | every test segment with true and predicted label |

`results/summary.md` collects all runs into one table.

## Pipeline

```
raw log ──► data.py ──► activity segments ──┬─► features.handcrafted_features ─► Approach 1 (rf / hgb)
                                           └─► features.encode_sequences ─────► Approach 2 (bilstm)
                                                                                Approach 3 (cnn / transformer)
                                    evaluate.py ◄── same splits, same metrics for every approach
```

### Data preparation (`har/data.py`)

* Normalises corrupted Aruba states (`ONc`, `OFF5`, `OFcF`, `CLOSED`, `28.55c`) and drops
  non-sensor lines (`ENTERHOME`, `LEAVEHOME`).
* Pairs `begin`/`end` annotations **per activity name**. Milan has 421 activities
  that begin while another is still open, so a single global stack would mis-pair them.
* A *segment* is every motion/door event between an activity's begin and end
  (explicit segmentation, as in most CASAS HAR papers). Temperature readings are
  kept separately and not used yet.
* Result: Aruba 6,476 segments / 11 classes, Milan 2,352 segments / 15 classes.
  (One Aruba Sleeping instance contains only temperature readings and is dropped.)

### Approaches

| # | Model | Input | Owner idea |
|---|---|---|---|
| 1 | `rf` Random Forest, `hgb` Gradient Boosting | 160-ish hand-crafted features: time of day, weekday, duration, event rate, per-sensor event share, first/last sensor, transitions | Member 1 |
| 2 | `bilstm` Bidirectional LSTM | ordered event sequence: token `<sensor>_<state>` + time gap, time since start, time of day | Member 2 |
| 3 | `cnn` multi-width 1D-CNN, `transformer` Transformer encoder | same sequence input as #2 | Member 3 |

All neural models append the segment context (time of day, duration, ...) before the
classifier head, use sqrt-inverse-frequency class weights for imbalance, label
smoothing 0.05, AdamW, and early stopping on a 10% validation slice of the
**training** fold (the test fold is never used for model selection).

### Pre-segment context (`--context`)

In Aruba, Enter_Home and Leave_Home segments contain almost the same events
(`D004 OPEN, M030 ON, D004 CLOSE, M030 OFF`), so every model tops out around 0.80 F1
on them. What separates them is what happened *before* the door opened: a silent
house means someone is entering, recent motion inside means someone is leaving.
`--context` adds three past-only features (gap since the previous event, number of
events and distinct sensors in the previous 10 minutes). It uses no future data,
so it still works live. Results are stored as `<model>+ctx`.

Aruba, Gradient Boosting, 5-fold: Enter_Home F1 0.81 → 0.98, Leave_Home 0.80 → 0.98,
macro-F1 0.845 → 0.876.

### Activity history (`--history`)

Wash_Dishes fires the same kitchen sensors (M015/M017/M018/M019) in nearly the same
proportions as Meal_Preparation, so with segment features alone every model recognises
only 3-9% of it. What separates them is the routine around them: in Aruba 38 of 65
Wash_Dishes instances directly follow Eating, and 59 start within two hours of a meal.
None overlap a Meal_Preparation label.

`--history` adds, for every activity class: log time since it last ended, whether it was
the most recent activity, and how many times it already happened that day
(`features.activity_history`). It is a two-stage model, and **no ground-truth label
reaches the features**: stage 1 recognises each segment from its own events; the history
is built from stage-1 *predictions* (out-of-fold via an inner 3-fold CV on the training
fold, and from the full stage-1 model on the test fold). A deployed system works the same
way: it only knows what it recognised earlier. Results are stored as `<model>+ctx+hist`.

`--balance full` (hgb) uses full instead of square-root inverse-frequency weights. It
trades precision for recall on rare classes and is stored as `+bal`.

Results with Gradient Boosting (macro-F1, %):

| | Aruba cv | Aruba temporal | Milan cv | Milan temporal |
|---|---|---|---|---|
| hgb + ctx | 87.18 | **92.75** | 91.41 | **84.65** |
| hgb + ctx + hist | **92.92** | 91.47 | **92.52** | 84.05 |

* Aruba cv: Wash_Dishes recall 0.06 -> 0.42 (F1 0.10 -> 0.50), Respirate F1 0.80 -> 0.91.
  With `--balance full`: Wash_Dishes recall 0.55, F1 0.56, but Respirate precision drops,
  so macro-F1 is lower (92.24).
* With true instead of predicted history labels (an upper bound, not committed), Aruba cv
  reaches 93.4: the stage-1 predictions lose almost nothing, because the activity that
  matters most (Eating) is recognised at F1 1.00.
* The temporal split does **not** show the gain. Its Aruba test set (last 30% of days)
  holds only 6 Wash_Dishes labels: Wash_Dishes annotations fall from ~20/month in
  Nov 2010 to 0-5/month from March 2011, while Meal_Preparation stays at ~240/month.
  The history model flags 15 test Meal_Preparation segments as Wash_Dishes; 12 of them
  start within 30 minutes of Eating ending (vs 4% of all test Meal_Preparation). That
  is consistent with unlabelled washing-up, but cannot be verified from the data.
* Random Forest gains much less (Aruba cv Wash_Dishes recall 0.03 -> 0.08): with
  `max_features="sqrt"` the few history columns are rarely chosen among ~200 features.
* Per-sensor dwell-time features (time spent at each sensor) were also tried on top of
  history and added nothing (Wash_Dishes F1 0.54 -> 0.55), so they are not included.

Segments longer than `--max-len` (default 128) events are uniformly subsampled so
long activities (Sleeping) keep their full sensor footprint.

### Evaluation protocol

* `--split cv` (default): stratified 5-fold over segments. Comparable to the papers on
  the slides (Zhao 2026, Alaghbari 2022), but slightly optimistic because segments from
  the same day can land in both train and test.
* `--split temporal`: first 70% of days train, last 30% test. Closer to deployment.

**Headline metric: macro-F1.** Accuracy is dominated by Relax / Meal_Preparation /
Kitchen_Activity; macro-F1 weights every activity equally, so it exposes failures on
rare or overlapping classes (Wash_Dishes, Respirate, Eve_Meds).

## Sliding windows on the raw event stream (`har.run_windows`)

The live product has no activity boundaries, so `har.run_windows` classifies the last
100 events at every event, with a chronological 60/20/20 day split (LastAct protocol).
`--history` adds routine-history features built from a first model's own predictions.
Final numbers and the model choice are in `results/windows.md`.

    python -m har.run_windows --dataset all --model bilstm --seeds 1 2 3

## Routine-deviation detection (`har.run_anomaly`)

The goal is **routine deviation**, not generic anomaly detection: `har.anomaly.RoutineModel`
learns *this resident's* routine — which activities happen daily and by when, how long, at
what time, how often, in what order, what each part of the day looks like, how long the home
is usually quiet — and `RoutineDrift` tracks how it evolves over a week. Alerts say what was
observed vs what is usual for this person. A generic autoencoder (`GenericAD`) is kept only
as a baseline.

CASAS has no deviation labels, so `har.anomaly_inject` copies every monitoring day and plants
one of five deviations (missed activity, prolonged activity, unusual time, extra night-time
toilet trips, long inactivity) directly into the **raw sensor events**, plus 7-day drift runs
(breakfast 20 min later each day). Three activity streams are produced for the same days —
annotations, the segment recogniser (GB + context) and the live window BiLSTM — and each
routine is learned from that stream on the observation period (middle 20 % of days),
calibrated to 0.1 alerts per normal day per routine aspect. Protocol: decisions D12–D14 in
`../paper/decisions.md`.

    python -m har.run_anomaly --dataset all     # ~1 h on CPU (BiLSTM inference dominates)
    python -m har.anomaly_report                # -> results/anomaly.md, anomaly_curve.png
    python -m har.alerts                        # routing: notify / summary / insight -> results/alerts.md
    python -m har.export_anomalies              # deviations found on real days -> dashboard JSON

Results: [`results/anomaly.md`](results/anomaly.md).

### Live demo replay (`har.replay`)

    python -m har.replay                        # after run_anomaly; -> ../public/replay/*.json

Replays a real monitoring day and one injected day per deviation type, for each home, through
the live BiLSTM and the routine model. Every 2 minutes of the day the routine model is re-run
on only what has happened so far, so alerts appear when a live system would raise them. The
exporter checks that the replay reproduces the evaluated live stream and raises every batch
alert (decision D17). The dashboard plays the files on the **Live demo** page (`/live`).

## Backend API (`api/`, decision D16)

    py -m api                                   # http://127.0.0.1:8000, docs at /docs
    py -m pytest tests -q

A FastAPI service over the files and models above. CORS allows the Next.js dev server
(`AMBILIVING_CORS` overrides it).

| Route | What it returns |
|---|---|
| `GET /homes` | Each home and whether its saved window model is available / loaded |
| `GET /homes/{home}/day`, `/anomalies` | The exported dashboard day and real-day routine deviations |
| `POST /homes/{home}/recognise` | Activity + confidence for the last 100 posted sensor events (saved BiLSTM, ~20 ms after the first call); `every=N` also returns a history |
| `GET /replay`, `/replay/{home}/{scenario}` | The D17 replay index and one whole scenario |
| `GET /replay/{home}/{scenario}/stream` | The scenario as server-sent events in timestamp order: `clock`, `event`, `prediction`, `alert` (at the second it was raised); `speed`, `start`, `end`, `only`, `tick` |
| `GET /homes/{home}/routine` | The saved routine model: observation period, stream rule, thresholds, usual day |
| `POST /homes/{home}/sessions` | Start live monitoring (`monitorFrom`: first day to monitor) |
| `POST /sessions/{id}/events` | Push sensor events in time order (and optionally `now`): runs the BiLSTM every 10th event, the routine model every 2 min of the clock and D15 routing; returns new predictions, new alert IDs, the day's routed alerts and any days that ended |
| `GET /sessions/{id}`, `DELETE` | Current activity, today's episodes and alerts, recently ended days |

### Live routine model (`har.routine_live`, decision D18)

    python -m har.routine_live --check          # fit + save models/<home>/routine.pkl, then verify

Fits the routine model as at the E20 operating point (observation days, live BiLSTM
predictions, Aruba 3-minute cleanup / Milan 3-point rule, 0.1 alerts per normal day) and
saves it next to the BiLSTM. `--check` replays each home's real monitoring day from the raw
data and requires the same predictions and alerts as `public/replay/` (E21). Live sessions
in the API use `LiveMonitor`, which processes pushed events incrementally with the same result.

## Results (5-fold CV, macro-F1 %)

Full table with accuracy / weighted-F1 / P / R / timing: [`results/summary.md`](results/summary.md).

| Approach | Aruba | Aruba +ctx | Milan | Milan +ctx | CPU time (Aruba) |
|---|---|---|---|---|---|
| 1 - Features + Gradient Boosting | 84.5 | **87.6** | **91.0** | **91.0** | 19 s |
| 1 - Features + Random Forest | 83.2 | 86.1 | 87.3 | 87.9 | 23 s |
| 2 - BiLSTM | 82.3 | 85.5 | 89.0 | 90.6 | 24 min |
| 3 - 1D-CNN | 82.8 | 86.2 | 86.6 | 86.4 | 11 min |
| 3 - Transformer | 83.3 | - | 89.2 | - | ~4 h (CPU) |

Accuracy is 95-98.6% for every model; macro-F1 is what separates them.

Findings:

1. **All approaches land within ~3 macro-F1 points.** The representation matters more
   than the architecture: adding pre-segment context improves every model on Aruba
   by +3 points, more than switching between any two models.
2. **Gradient Boosting on hand-crafted features is the strongest and by far the
   cheapest** (seconds vs. minutes/hours on CPU), which matters for a deployable system.
3. **Remaining hard cases are the overlap classes the slides predicted:**
   * Aruba Wash_Dishes: F1 ≈ 0.15 for every model. 59 of 65 instances are predicted as
     Meal_Preparation (same kitchen sensors, same proportions, 65 vs 1,606 samples).
   * Milan Chores: F1 ≈ 0.35-0.42 (23 samples, spread across many rooms).
   * Aruba Respirate: 6 samples only; per-fold scores are unstable (hence the ±5 std).
4. Context fixes Enter_Home / Leave_Home (Aruba F1 0.81 → 0.98) but does not fix
   Wash_Dishes, whose distinguishing cue (it usually follows a meal) needs more than an
   event count. See `preceding_profile` in `features.py` (work in progress).

## Known limitations / next steps

* Explicit segmentation assumes activity boundaries are known. For the live dashboard,
  a sliding-window (online) variant is needed: classify the last N events at each new event.
* `--history` relies on earlier recognitions; in a live system one wrong recognition
  can affect the next. It is only implemented for rf / hgb.
* Concurrent activities (e.g. washing up while cooking) are not represented in the Aruba
  labels, which record one activity at a time, so they can be neither learned nor evaluated.
* Label density drifts over time in Aruba (Wash_Dishes, Eating, Housekeeping) and Milan
  (Chores only in the first month), which makes temporal-split per-class scores noisy.
* Temperature sensors are unused.
* No hyper-parameter search yet. Each approach owner should tune their own model
  using the training folds only.
