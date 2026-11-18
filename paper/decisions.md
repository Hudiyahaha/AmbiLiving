# Methodology decisions

Record a decision **before** running the experiment it governs. Each entry: what was decided,
why, what alternatives were rejected, and where it is implemented. These become the paper's
Method section and answer the reviewer question "why did you do it this way?".

Template:

```
## D<n> — <short title>  (<date>, <who>)
**Decision**:
**Why**:
**Alternatives rejected**:
**Implemented in**:
```

---

## D1 — Macro-F1 is the headline metric  (Oct 2026)
**Decision**: Report macro-F1 first; accuracy, weighted-F1, macro precision and recall alongside.
**Why**: Accuracy is dominated by Relax (2,919) and Meal_Preparation (1,606) on Aruba and Kitchen_Activity on Milan; it hides failures on the rare and overlapping activities the project is about.
**Alternatives rejected**: Accuracy alone (used by several prior CASAS papers, so still reported for comparison).
**Implemented in**: `ml/har/evaluate.py`, `compare.py`.

## D2 — Two segment protocols: stratified 5-fold CV and temporal split  (Oct 2026)
**Decision**: Report both. CV for comparability with prior work; temporal (first 70 % of days train, last 30 % test) as the deployment-like number.
**Why**: Stratified CV lets segments from the same day fall into train and test, so it is optimistic.
**Implemented in**: `ml/har/run.py --split cv|temporal`.

## D3 — Macro-F1 averages only activities present in the test set  (13 Oct 2026, Ibrahim)
**Decision**: Classes with zero test support are excluded from the macro average; all runs rescored.
**Why**: On the temporal split some activities never occur in the test days; counting them as F1 = 0 penalises the model for something it could not be tested on.
**Implemented in**: commit `b544d7d`, `ml/har/rescore.py`.

## D4 — Explicit segmentation with per-activity begin/end pairing  (Oct 2026)
**Decision**: A segment is every motion/door event between an activity's `begin` and `end`; begins and ends are paired per activity name.
**Why**: Milan has 421 activities that begin while another is still open; a single global stack mis-pairs them.
**Implemented in**: `ml/har/data.py`.

## D5 — Routine history uses only the model's own predictions  (10 Oct 2026, Aleeza)
**Decision**: Two-stage model; history features come from stage-1 predictions (out-of-fold inside the training fold), never from annotations.
**Why**: A deployed system only knows what it recognised earlier; using labels would leak and overstate results.
**Implemented in**: `features.activity_history`, `run.py --history`; window version in `window_history.py`.

## D6 — Live setting follows the LastAct protocol  (Nov 2026, Aleeza)
**Decision**: Window = last 100 events; days split chronologically 60/20/20; training windows every 50 events; one test window per event; label = activity of the most recent annotated event.
**Why**: The live product has no activity boundaries; using a published protocol makes our numbers directly comparable with LastAct and DeepCASAS.
**Implemented in**: `ml/har/windows.py`, `run_windows.py`.

## D7 — Two label rules for unannotated events  (Nov 2026, Aleeza)
**Decision**: `last` (the most recent annotated activity; comparable with LastAct) is the headline; `other` (unannotated → "Other", the real product setting) is reported separately.
**Implemented in**: `run_windows.py --label last|other`; results in `window100-last/`, `window100-other/`.

## D8 — Window-model selection rule fixed in advance  (Nov 2026, Aleeza)
**Decision**: Use BiLSTM + routine history only if history improves both homes; otherwise plain BiLSTM. Outcome: plain BiLSTM (history hurt Milan).
**Why**: Prevents picking the configuration that looks best on test data.
**Implemented in**: `ml/results/windows.md`.

## D9 — No prediction smoothing  (Nov 2026, Aleeza)
**Decision**: k = 1 (no smoothing over recent windows), chosen on the validation days.
**Why**: Every k > 1 lowered macro-F1; short activities get averaged away.

## D10 — Shared neural training recipe  (Oct 2026)
**Decision**: sqrt-inverse-frequency class weights, label smoothing 0.05, AdamW, early stopping on a 10 % validation slice of the training fold; one shared input encoding and classifier head for BiLSTM / CNN / Transformer.
**Why**: Makes the architecture comparison fair; the test fold is never used for model selection.
**Implemented in**: `ml/har/train.py`, `models/sequence.py`.

## D11 — Dashboard demo day  (13 Oct 2026, Aleeza)
**Decision**: Train GB + ctx on the first 70 % of days; show the unseen test day with the most distinct annotated activities.
**Implemented in**: `ml/har/export_dashboard.py`.

---

## D12 — We detect *routine deviations*, not generic anomalies  (18 Nov 2026, reframed the same day)
**Decision**: The project's goal is **routine deviation detection**: learn *this resident's own* routine from their own observation days and report how today departs from it, as *observed vs expected for this person*. It is not generic anomaly (outlier) detection.

| | Generic anomaly detection | Routine deviation (ours) |
|---|---|---|
| Reference | whatever is statistically rare in the data | this resident's learned routine |
| Unit | an outlying point or window | an aspect of the routine: what, when, how long, how often, in what order, and how the routine changes over days |
| Absence | cannot flag what did not happen | "has not happened by the time it always has" is a first-class deviation |
| Output | an anomaly score | observed vs expected, in the resident's own terms |
| Meaning | abnormal = bad | a deviation is a *change*; it may be benign (a holiday) or a concern; severity says how much attention it needs |

**Routine model** — the aspects of the routine we model, and the deviation each one can show:

| Routine aspect | Deviation | Caregiver meaning |
|---|---|---|
| Which activities happen every day, and by when | `missed` | a daily activity has not happened by the time it always has (no cooking today) |
| How long each activity lasts | `prolonged` | an activity is lasting far longer than usual (possible fall or illness in the bathroom) |
| When each activity happens | `unusual_time` | an activity at an hour it never happens (cooking or going out at 3 am) |
| How often each activity happens per day | `frequency` | many more repetitions than usual (night-time toilet trips) |
| In what order activities follow each other | `unusual_order` | a transition this resident never makes |
| What the day looks like hour by hour | `timeline` | a two-hour stretch of the day looks unlike the usual day at that time |
| How long the home is usually quiet during each activity | `inactivity` | silence far longer than usual for what the resident is doing, while at home |
| How the routine evolves across days | `drift` | over a week, an activity's usual time or daily count shifts (breakfast getting later each day) |

**Why**: This is what was promised in the defense ("ambient sensors → HAR → specific activity → **routine deviation** → caregiver insight") and what caregivers act on. Generic anomaly detection is kept only as a **baseline** to show the difference (D14).
**Terminology**: "routine deviation" in the paper, report and dashboard. Code file names (`anomaly*.py`) and the `AnomalyRecord` type keep their names to avoid churn.

## D13 — Evaluation protocol: synthetic routine deviations injected into the raw sensor stream  (18 Nov 2026)
**Decision**:
- Same chronological split as the live HAR protocol (D6): **first 60 % of days** train the recognisers; the **middle 20 %** is the *observation period* in which each resident's routine is learned; the **last 20 %** is the monitoring period.
- **Single-day deviations.** For every monitoring day and type, up to **3 copies** (different random targets) get one deviation edited into the **raw sensor events** (and the matching annotations), so the recognisers have to see it through the sensors, exactly as in deployment:
  - `missed`: delete every event inside the target daily activity's segments that day (Meal_Preparation / Kitchen_Activity — Milan's Morning_Meds is annotated on only 47 % of training days, so it is not a daily activity);
  - `prolonged`: stretch one short-activity segment's events by +60–120 min and shift the rest of the day later;
  - `unusual_time`: move one cooking or Leave_Home segment's events to 01:00–04:30;
  - `night_frequency`: insert 4 Bed_to_Toilet episodes (copied from training days) between 00:30 and 05:30;
  - `inactivity`: delete all events in a 2.5–4 h window starting 08:00–15:00 while the resident is at home.
- **Multi-day drift.** Runs of **7 consecutive monitoring days** in which the first cooking episode after 05:00 is moved later by 20 min × day number (day 7: +140 min).
- Three activity streams for the same days: **(a)** annotations (perfect recognition), **(b)** the segment recogniser (GB + context, annotated boundaries), **(c)** the live window recogniser (BiLSTM, last 100 events, every 10th event).
- **Metrics**: per type, *detection rate*, *false alerts per clean day*, day-level *precision / recall / F1* on a balanced set (that type's injected days vs as many clean days), *detection delay* (minutes; days for drift). A sweep of the alert budget gives a detection vs false-alert curve.
- **Matching**: `missed` and `drift` injections count as detected only by an alert of that kind naming the target activity (drift: within the 7-day run); any other injection counts if any alert falls between 30 min before its start and 60 min after its end.

**Why**: CASAS has no deviation labels. Injecting at the sensor level is what lets us measure how recognition errors propagate (RQ5). The routine is learned from each stream's own output, as a deployed system would have to; window episodes and annotated segments differ in duration by construction.
**Known weaknesses (state in the paper)**: synthetic deviations are cleaner than real ones; Milan has 13 observation and 13 monitoring days, its monitoring days are the Christmas holiday (so some "false" alerts on clean days are genuine routine changes), and only 2 overlapping drift runs fit.

## D14 — Routine model, generic baseline and alert budget  (18 Nov 2026)
**Decision**: Fitted per home and per stream on the observation period only.
- **Routine model (ours)**, one score per aspect in D12: robust z of log duration; smoothed time-of-day density; running daily-count z; **survival of the first occurrence** (`missed`: score = −log P(not yet happened by now), estimated from the observation days, so an activity done every day by 09:00 becomes surprising at 09:30 while an often-skipped one never does); first-order transition probabilities (`unusual_order`); a 48-bin activity-occupancy profile scored over two-hour blocks (`timeline`); silence length relative to the current activity's usual long silence (`inactivity`); and per-activity first-occurrence time and daily count over a rolling 7-day window against the observation period (`drift`).
- **Generic anomaly-detection baseline**: an MLP autoencoder over episode features (activity, start time, log duration, count so far today, time since the previous same activity), after Fahad & Tahir (2020). It flags episodes it reconstructs poorly. It has no notion of absence, order, day structure or drift — that is the point of the comparison.
- **Thresholds** are calibrated on the observation period (leave-one-day-out for the routine model, leave-one-week-out for drift, 5-fold by day for the autoencoder) so that each score raises on average **0.1 alerts per normal day**; the sweep varies this from 0.02 to 1.

**Changes made after seeing monitoring-day results** (all must be reported in the paper):
1. *E11, Milan first run*: `missed` used a fixed deadline (90th percentile of first occurrence + 1 h) and produced most false alerts; changed to a calibrated lateness score.
2. *E12, Aruba first run*: that lateness score used one threshold across activities, so often-skipped activities (Leave_Home absent on 23 % of observation days) used up the budget and **no** missed meal was detected. Replaced by the per-activity first-occurrence survival score above. At the same time the work was reframed as routine deviation (order, timeline and drift added; the autoencoder became a stand-alone generic baseline instead of sharing the absence rules).

3. *E13, Milan rerun*: the empirical first-occurrence survival is a step function; leave-one-day-out calibration (12 days) and monitoring (13 days) then have different score ceilings, so "later than on any observed day" exceeded the threshold on monitoring days but only tied it during calibration — the budget was not respected. Replaced by a smooth survival (smoothed skip probability + normal curve over the usual first-occurrence time). A code bug found at the same time (`-log(S).max()` instead of `-log(S.min())`) had made `missed` fire on nothing.

**Why**: Calibrating by alerts per normal day fixes the false-alert rate in caregiver terms and makes all aspects comparable.

## Open decisions (make these before the matching ROADMAP step)

- **D15 — Alert rules**: which deviations notify a caregiver at once vs only appear in the daily summary, confidence floor, cool-down (ROADMAP 3.1)
- **D16 — Backend technology** (ROADMAP 4.1)
