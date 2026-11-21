# 1 Introduction

Most older adults want to keep living in their own homes, but families and caregivers cannot
watch over them around the clock. Cameras are intrusive, especially in bedrooms and bathrooms,
and wearables depend on the resident remembering to wear and charge them. **Ambient sensors**
— passive infrared motion sensors, door contacts and temperature sensors fixed in the home —
avoid both problems: they record no images and ask nothing of the resident.

Commercial ambient-sensor products (for example Zemplee Sense and OdeCare) already monitor
presence and raise alerts, but they report *which sensor fired and when*, not *what the
resident was doing*. A caregiver who sees "M018 ON 09:54" still has to work out that this was
breakfast being prepared. Closing this semantic gap requires two stages that are usually
studied separately: **human activity recognition (HAR)**, which turns sensor events into
activities, and **routine-deviation detection**, which learns the resident's *own* routine and
decides whether today departs from it in a way a caregiver should hear about. This is not generic
anomaly detection: the reference is this person's routine, a missing activity matters as much as
an unusual one, and the output is *observed versus expected for this resident* rather than an
outlier score.

Three problems make this hard in practice. First, some activities fire the same sensors in
the same proportions — washing dishes and preparing a meal, or entering and leaving the home —
so they cannot be told apart from the events of the activity alone. Second, almost every
published HAR result assumes the start and end of each activity are known, because the
annotations provide them; a deployed system has no such boundaries and must classify the
stream as it arrives. Third, routine and anomaly detectors are normally evaluated on annotated
activities; in deployment they consume the recogniser's *predictions*, and recognition errors
propagate into missed deviations and false alerts.

We study the full pipeline — sensors → recognised activity → routine deviation → caregiver
alert — on two CASAS smart homes (Aruba and Milan) and ask:

- **RQ1** With known activity boundaries, does the choice of model matter more or less than
  the input representation?
- **RQ2** Can routine context, taken only from the model's own earlier predictions, separate
  activities that fire the same sensors?
- **RQ3** How well does recognition work live, without boundaries, compared with the state of
  the art under the same protocol?
- **RQ4** How can deviations from a resident's own routine be detected and evaluated when the
  data has no deviation labels, and how does this compare with generic anomaly detection?
- **RQ5** How much do recognition errors degrade routine-deviation detection and false-alert
  rates?

**Contributions.**

1. A controlled comparison of five recognisers (Random Forest, Gradient Boosting, BiLSTM,
   1D-CNN, Transformer) on two homes under three protocols — stratified 5-fold
   cross-validation, a temporal split, and a live sliding window — with repeated seeds.
2. Two past-only context features — activity just before a segment, and a routine history
   built from the recogniser's own predictions — that resolve the Enter/Leave_Home and
   Wash_Dishes/Meal_Preparation confusions, together with an analysis of when the history does
   not help (label drift).
3. A live sliding-window recogniser that beats the published LastAct result on Milan under
   LastAct's own protocol.
4. A per-resident **routine model** covering which activities happen daily and by when, how
   long, at what time, how often, in what order, what each part of the day looks like, how long
   the home is usually quiet, and how all of this drifts over a week; an evaluation protocol that
   injects routine deviations into the **raw sensor stream**; a comparison with generic anomaly
   detection; and a measurement of how deviation detection degrades from annotated activities to
   segment predictions to live predictions.
5. An open, dataset-agnostic caregiver dashboard that shows recognised activities and routine
   deviations as plain-language observed-versus-expected statements instead of raw scores.

<!-- Section 1 numbers: none. Claims used later: C1–C9. -->
