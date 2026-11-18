# 3 Data

We use two single-resident CASAS homes [casas].

| | Aruba | Milan |
|---|---|---|
| Residents | 1 | 1 (+ pet) |
| Period | 4 Nov 2010 – 11 Jun 2011 (220 days) | 16 Oct 2009 – 6 Jan 2010 (65 days) |
| Binary sensors | 34 (31 motion, 3 door) | 31 (28 motion, 3 door) |
| Binary events | 1,602,979 | 421,392 |
| Annotated activity instances (segments) | 6,476 | 2,352 |
| Activity classes | 11 | 15 |

**Parsing.** The raw logs contain corrupted states (e.g. `ONc`, `OFF5`, `OFcF` in Aruba),
which we normalise; lines that are not sensor events are dropped. Temperature readings are
parsed but not used. Annotations are `begin`/`end` markers on events. We pair them **per
activity name** rather than with a single stack, because Milan has 421 activities that begin
while another is still open, and a global stack would mis-pair them (D4). One Aruba Sleeping
instance contains only temperature readings and is dropped, giving 6,476 instead of 6,477
segments.

**Class imbalance.** Both homes are heavily imbalanced. In Aruba, Relax (2,919) and
Meal_Preparation (1,606) make up 70 % of instances while Wash_Dishes has 65 and Respirate 6.
In Milan, Kitchen_Activity has 554 instances while Eve_Meds has 19 and Meditate 17.

**Overlapping activities.** Aruba's Meal_Preparation and Wash_Dishes fire the same kitchen
motion sensors (M015, M017, M018, M019) in nearly the same proportions (Figure F2), and
Enter_Home and Leave_Home both consist of almost the same four events
(`D004 OPEN, M030 ON, D004 CLOSE, M030 OFF`).

**Label drift.** Annotation density changes over time. In Aruba, Wash_Dishes is annotated about
20 times a month in November 2010 but 0–5 times a month from March 2011, while
Meal_Preparation stays near 240 a month; only 6 Wash_Dishes labels fall in the last 30 % of
days. Milan drifts the other way: Kitchen_Activity is annotated 90 times in November 2009 but
342 times in December, and Morning_Meds once in November but 23 times in December, so the
training period (to 11 December) is labelled far more sparsely than the observation and
monitoring periods; Chores is annotated only in the first month. Figure F5 shows these counts.
This matters for any chronological split (Section 5).

**Splits.** Explicit-segmentation experiments use stratified 5-fold cross-validation (for
comparability with prior work) and a temporal split (first 70 % of days train, last 30 % test;
D2). Live experiments and the anomaly study use LastAct's chronological 60/20/20 day split
(D6, D13): Aruba trains before 16 Mar 2011, observes 16 Mar – 28 Apr (44 days) and monitors
29 Apr – 11 Jun (44 days); Milan trains before 12 Dec 2009, observes 12 – 24 Dec (13 days) and
monitors 25 Dec – 6 Jan (13 days, a holiday period).

<!-- F5: ml/results/label_drift.png (claims C4c, C6d). -->
