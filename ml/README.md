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

## Known limitations / next steps

* Explicit segmentation assumes activity boundaries are known. For the live dashboard,
  a sliding-window (online) variant is needed: classify the last N events at each new event.
* Temperature sensors are unused.
* No hyper-parameter search yet. Each approach owner should tune their own model
  using the training folds only.
