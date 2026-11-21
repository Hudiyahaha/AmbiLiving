# 5 Results

All values are percentages. Macro-F1 averages over the activities present in the test data
(D3). Values with ± are mean ± standard deviation over folds (cross-validation) or over three
seeds.

## 5.1 Recognition with known boundaries (RQ1, RQ2)

**Table T1 — macro-F1, segment setting** (source: `ml/results/summary.md`; seeds:
`ml/results/experiments.md`).

| Model | Aruba CV | Aruba temporal | Milan CV | Milan temporal |
|---|---|---|---|---|
| Random Forest | 83.23 ± 4.05 | 86.76 | 87.32 ± 1.74 | 89.48 |
| Gradient Boosting | 84.52 ± 4.62 | 86.68 | 91.01 ± 2.03 | 89.39 |
| BiLSTM | 82.25 ± 3.29 | 88.52 | 89.01 ± 3.01 | **93.55** |
| 1D-CNN | 82.80 ± 4.21 | 85.58 | 86.56 ± 0.97 | 85.01 |
| Transformer | 83.25 ± 3.93 | 82.53 | 89.18 ± 4.30 | 91.63 |
| Gradient Boosting + context | 87.18 ± 4.83 | **92.75** | 90.97 ± 1.42 | 90.69 |
| Gradient Boosting + context + history | **92.92 ± 3.74** | 91.47 | **92.52 ± 1.73** | 90.05 |

Accuracy is 95–99 % for every model on Aruba under cross-validation, while macro-F1 ranges
from 82.3 to 92.9 <!-- C1 -->: accuracy is dominated by Relax and Meal_Preparation and hides
exactly the failures that matter.

**Representation matters more than architecture (RQ1).** Without context, the five models
are within about two macro-F1 points of each other on Aruba cross-validation. Adding the three
pre-segment context features raises every model by about three points (RF 83.23 → 86.14,
GB 84.52 → 87.18, BiLSTM 82.25 → 85.51, CNN 82.80 → 86.15) <!-- C2 --> — more than the gap
between any two architectures. On Milan the context features change little (GB 91.01 → 90.97,
BiLSTM 89.01 → 90.61, CNN 86.56 → 86.41), because Milan's hard cases are not the door
activities. Gradient Boosting is best or close to best everywhere and trains in seconds
(193 s for five folds on Aruba) against 24 minutes for the BiLSTM and about four hours for the
Transformer on CPU <!-- C2b -->.

Repeated seeds on the temporal split (Aruba: GB + context 90.19 ± 1.05, BiLSTM + context
90.08 ± 0.77; Milan: BiLSTM 94.89 ± 0.79) show that the neural models are seed-sensitive;
a lower learning rate (3 × 10⁻⁴) did not help on average and increased the spread up to
± 6.7 points <!-- C4e, E6 -->.

**Context resolves the overlapping activities (RQ2).** On Aruba (GB, cross-validation),
pre-segment context lifts Enter_Home from 0.81 to 0.98 F1 and Leave_Home from 0.81 to 0.98
<!-- C3 -->. Routine history then lifts Wash_Dishes from 0.10 to 0.50 F1 (recall 0.06 → 0.42)
and Respirate from 0.80 to 0.91, taking macro-F1 from 87.18 to 92.92 <!-- C4 -->. On Milan,
history raises macro-F1 from 90.97 to 92.52 <!-- C4b -->. These gains come from the model's own
predictions: no annotation reaches the history features.

**When history does not help.** On the temporal split, history does not improve either home
(Aruba 92.75 → 91.47, Milan 90.69 → 90.05) <!-- C4c -->. Aruba's last 30 % of days contain only
six Wash_Dishes annotations, because the annotation of washing-up fades out from March 2011
while cooking stays constant. The history model flags 15 test Meal_Preparation segments as
Wash_Dishes, 12 of which start within 30 minutes of a meal ending — consistent with
unlabelled washing-up, but not verifiable from the data.

<!-- TODO: Figure F3 (confusion matrices before/after history), F5 (labels per month). -->

## 5.2 Live recognition without boundaries (RQ3)

**Table T3 — sliding window, LastAct protocol, macro-F1 (3 seeds)** (source:
`ml/results/windows.md`).

| Model | Aruba | Milan |
|---|---|---|
| **BiLSTM** (our final window model) | 41.9 ± 1.5 | **45.6 ± 0.6** |
| Gradient Boosting + routine history | **43.8 ± 0.4** | 37.9 (one run) |
| Gradient Boosting | 39.1 ± 0.2 | 38.1 ± 1.0 |
| 1D-CNN (test window every 10th event) | 42.2 ± 0.9 | 43.7 ± 0.6 |
| Transformer (test window every 10th event) | 37.1 ± 2.4 | 45.1 ± 0.7 |
| LastAct (reported) [lastact2026] | 44.6 ± 1.9 | 40.1 ± 0.5 |
| DeepCASAS (reported by LastAct) | 38.6 | 36.7 |

Under LastAct's own protocol our BiLSTM exceeds the published LastAct result on Milan by 5.5
points and is 2.7 points below it on Aruba; Gradient Boosting with routine history is within
LastAct's error bar on Aruba <!-- C5 -->. The window model was selected by a rule fixed before
the runs: use history with the BiLSTM only if it helped on both homes. It did not — on Milan
it lowered macro-F1 from 45.4 to 38.0 — so the plain BiLSTM was chosen <!-- C5b, D8 -->.
Smoothing predictions over the last *k* windows lowered macro-F1 for every *k* tried
<!-- C5c -->.

**Architecture matters little here too.** A 1D-CNN and a Transformer trained under the same
protocol (test window at every 10th event, three seeds) do not beat the BiLSTM, which scores
42.1 ± 1.4 (Aruba) and 45.4 ± 0.2 (Milan) at the same test stride. The CNN ties on Aruba
(42.2 ± 0.9) and is lower on Milan (43.7 ± 0.6). The Transformer ties on Milan (45.1 ± 0.7) but is
lower and less stable on Aruba (37.1 ± 2.4; seeds 34.8–39.5). With about 19 000 (Aruba) and
4 600 (Milan) training windows and no pretraining, the attention model has little data to learn
from. The BiLSTM stays the window model <!-- C5d, E17 -->.

Live recognition is far harder than the segment setting (about 42–46 versus about 92 macro-F1)
<!-- C6 -->: without boundaries the model must decide when an activity has started, and short
or rare activities are swamped by their neighbours. Wash_Dishes and the medication activities
stay near zero F1. Part of Milan's gap is also a distribution shift: its monitoring days are
the Christmas holiday, and the same Gradient Boosting model scores about 46 on the validation
days but 38 on the test days <!-- C6b -->.

**Per-event scores understate what routine detection needs.** Routine detection works on
episodes (a meal, a night's sleep), not on single events. We grouped the BiLSTM's per-event test
predictions into episodes (runs of the same predicted activity) and matched them with the
annotated episodes (same activity, overlapping within ±15 minutes). The raw live stream touches
almost every real episode (96 % on Aruba, 90 % on Milan) but flickers. It produces 13–14 times as
many episodes as really happen (Aruba 390 per day against 29), so most predicted episodes are fake
(precision 28 % and 46 %). Absorbing predicted runs shorter than two minutes into the run before
them uses only the past, so it can run live. On Aruba it gives 30 episodes per day, with 80 % of
real episodes found at 54 % precision. Meal_Preparation (89 % found / 68 % precision), Sleeping
(95 / 61), Bed_to_Toilet (80 / 83) and Leave_Home (78 / 85) are recognised well at this level;
Eating, Work, Wash_Dishes and Respirate stay weak <!-- C6e, E19 -->.

**Table T3b — episode-level view of the live BiLSTM, mean over activities** (source:
`ml/results/episodes.md`).

| Home | Predicted stream | Episodes found | Precision | Episodes per day (true → predicted) |
|---|---|---|---|---|
| Aruba | raw (every event) | 96.2 | 28.1 | 29.2 → 389.8 |
| Aruba | routine pipeline (every 10th event, runs < 3 merged) | 65.7 | 37.7 | 29.2 → 38.5 |
| Aruba | runs < 2 min merged | 79.6 | 53.9 | 29.2 → 29.9 |
| Milan | raw (every event) | 89.8 | 45.6 | 45.3 → 650.9 |
| Milan | routine pipeline (every 10th event, runs < 3 merged) | 69.4 | 64.1 | 45.3 → 53.7 |
| Milan | runs < 2 min merged | 66.3 | 63.1 | 45.3 → 45.5 |

The episodes the routine pipeline used in §5.3 are as good as the two-minute cleanup on Milan, but
clearly worse on Aruba (precision 38 against 54 %). §5.3 tests whether this explains part of the
Aruba result.
