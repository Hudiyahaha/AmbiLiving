# 4 Method

## 4.1 Problem settings

**Segment setting.** Each annotated activity instance is one sample: every motion and door
event between its begin and end. This is the setting of most CASAS papers; the boundaries are
given for free.

**Live window setting.** No boundaries are available. At an event, the sample is the last 100
events, and the target is the activity of the most recent annotated event (LastAct's protocol,
D6). A live system makes one such prediction per event (or, in our routine-deviation pipeline, every
10th event).

## 4.2 Recognisers

**Approach 1 — hand-crafted features + classical classifiers.** Each sample becomes a
fixed-length vector (138 features for Milan, 150 for Aruba): log duration, number of events,
event rate, start and end time of day and weekday (as sine/cosine), number of distinct
sensors, mean and maximum inter-event gap, transition rate, and for every binary sensor its
share of all events, its share of ON/OPEN events, and whether it is the first or last sensor.
We train a Random Forest (500 trees, balanced class weights) and a histogram Gradient Boosting
classifier (square-root inverse-frequency sample weights, early stopping).

**Approaches 2 and 3 — sequence models.** Each event becomes a token `<sensor>_<state>` with
four timing features (log gap to the previous event, log time since the sample start, time of
day as sine/cosine). Samples longer than 128 events are uniformly subsampled so that long
activities keep their whole sensor footprint. A BiLSTM (64 hidden units per direction, mean +
max pooling), a multi-width 1D-CNN (kernels 3, 5, 9) and a 2-layer Transformer encoder share
the same embedding, the same pooled-representation-plus-context head, and the same training
recipe: AdamW, label smoothing 0.05, square-root inverse-frequency class weights, and early
stopping on a 10 % validation slice of the *training* data (D10). Sharing everything except
the encoder makes the comparison an architecture comparison.

## 4.3 Context features

**Pre-segment context** (`+ctx`) adds three past-only features: the gap since the previous
event, and the number of events and of distinct sensors in the 10 minutes before the sample.
A silent house before the door opens indicates someone entering; recent movement inside
indicates someone leaving.

**Routine history** (`+hist`) adds, for every activity class: log time since it last ended,
whether it was the most recent activity, and how many times it has happened so far that day.
It is computed in two stages: a first model recognises each sample from its own events, and the
history is built from these **predictions**, never from annotations (out-of-fold predictions
on the training data; the full first-stage model on test data; D5). A deployed system has the
same information: only what it recognised earlier. The intended cue is that washing up
usually follows a meal — in Aruba 38 of 65 Wash_Dishes instances directly follow Eating and 59
start within two hours of a meal.

## 4.4 Routine deviation, not generic anomaly detection

Our goal is to detect **deviations from this resident's own routine**, not statistical outliers
(D12). The two are often used interchangeably, but they differ in what they compare against and
what they can say:

| | Generic anomaly detection | Routine deviation (ours) |
|---|---|---|
| Reference | whatever is rare in the data | the resident's learned routine |
| Unit | an outlying point or window | an aspect of the routine: what, when, how long, how often, in what order, and how it changes over days |
| Absence | cannot flag what did not happen | "has not happened by the time it always has" is a first-class deviation |
| Output | an anomaly score | observed vs expected for this resident |
| Meaning | abnormal = bad | a deviation is a change — benign (a holiday) or a concern; severity says how much attention it needs |

The **routine model** is learned per resident and represents eight aspects of the routine, each
with the deviation it can reveal:

| Routine aspect | Deviation | Caregiver meaning |
|---|---|---|
| which activities happen every day, and by when | missed | a daily activity has not happened by the time it nearly always has |
| how long each activity lasts | prolonged | far longer than usual (possible fall or illness) |
| when each activity happens | unusual time | an activity at an hour it never happens (possible confusion) |
| how often each activity happens per day | frequency | many more repetitions than usual (night-time toilet trips) |
| which activity follows which | unusual order | a transition the resident never makes |
| what the day looks like hour by hour | timeline | a two-hour stretch unlike the usual day at that time |
| how long the home is usually quiet during each activity | inactivity | silence far longer than usual for what the resident is doing, at home |
| how the routine evolves | drift | over a week, an activity's usual time or frequency shifts |

## 4.5 Evaluation protocol

CASAS contains no labelled routine deviations, so we inject them (D13). Every monitoring day is
copied, and up to three copies per type receive one deviation, edited directly into the **raw
sensor events** and the matching annotations:

- *missed*: delete every event inside the daily cooking activity's segments that day;
- *prolonged*: stretch one short activity's events in time by 60–120 minutes and shift the rest
  of the day later;
- *unusual time*: move one cooking or Leave_Home segment's events to 01:00–04:30;
- *night toilet trips*: insert four Bed_to_Toilet episodes, copied from training days, between
  00:30 and 05:30;
- *inactivity*: delete all events in a 2.5–4 hour window starting 08:00–15:00 while the resident
  is at home;
- *drift*: in runs of seven consecutive monitoring days, move the first cooking episode after
  05:00 later by 20 minutes per day (day 7: +140 minutes).

Because the edit is made to the sensor events, every recogniser has to *see* the deviation
through the sensors. Detection then runs on three **activity streams** for the same days:
(a) the annotations (perfect recognition, an upper bound), (b) the segment recogniser (Gradient
Boosting + context with annotated boundaries), and (c) the live window recogniser (BiLSTM on the
last 100 events, run every 10th event; runs shorter than three predictions are merged into the
previous episode). Stream (c) is what a deployed system would see.

All streams use the 60/20/20 day split: recognisers train on the first 60 % of days; each
routine is learned from **its own stream** on the middle 20 % (the *observation period*, as
after installation); the last 20 % is monitored. Learning the routine from the stream it will
be applied to matters, because window episodes and annotated segments differ in duration by
construction.

**Metrics.** Per type: the *detection rate* (share of injected deviations matched by an alert);
*false alerts per clean day* (alerts on the untouched monitoring days); a day-level
*precision / recall / F1* on a balanced set of that type's injected days and as many clean
days; and the *detection delay*. A missed or drift injection is matched only by an alert of that
kind naming the target activity (drift: within the run); any other injection by any alert from
30 minutes before its start to 60 minutes after its end.

## 4.6 Scores, calibration and explanations

Each routine aspect has one score, computed from the observation period of the same stream
(D14):

- **missed**: the first-occurrence time of each activity present on at least half of the
  observation days is modelled as a skip probability plus a normal curve over its usual time;
  the score at time *h* is −log P(not yet happened by *h*). An activity done every day by 09:00
  becomes surprising at 09:30, while one that is often skipped never does.
- **prolonged**: robust z-score of log duration (median and MAD) per activity.
- **unusual time**: surprise under a Gaussian-smoothed 48-bin time-of-day density per activity.
- **frequency**: running daily-count z-score per activity.
- **unusual order**: −log P(activity | previous activity) from first-order transition counts.
- **timeline**: the activity occupying each half-hour of the day is scored against the
  observation-period occupancy of that half-hour; the mean surprise over a two-hour block, minus
  its expected value, is the score.
- **inactivity**: a daytime silence while at home, divided by the usual long silence (95th
  percentile) *for the current activity* — a quiet hour while relaxing is normal, while cooking
  it is not.
- **drift**: for each daily activity, the mean first-occurrence time and daily count over a
  rolling seven-day window, as a z-score against the observation period.

What the resident is doing — and whether they are at home — comes from the stream itself, so
recognition errors affect every aspect, including the absence-based ones.

**Generic anomaly-detection baseline.** Following Fahad and Tahir [fahad2020], an MLP
autoencoder (32-8-32) reconstructs a feature vector per episode (activity, start time, log
duration, count so far that day, time since the previous episode of the same activity) and
flags poorly reconstructed episodes. It has no notion of absence, order, day structure or drift.

**Calibration.** No threshold is chosen on monitoring days. Each score is calibrated on the
observation period — leave-one-day-out (routine model), leave-one-week-out (drift), 5-fold by
day (baseline) — so that it raises on average **0.1 alerts per normal day** (the operating
point). Varying this budget from 0.02 to 1 traces detection against false alerts.

**Explanations.** Every alert becomes a record with a title, what was observed, what is usual
*for this resident*, a plain-language reason and a severity, with no raw scores (spec §11);
for example *"Bed to toilet is taking much longer than usual — 1.6 h, started 02:10 — usually
1 min to 4 min."*

<!-- TODO: replace the example with a real alert from ml/results/<home>/anomaly/alerts_*.csv. -->
