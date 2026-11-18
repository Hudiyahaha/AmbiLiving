# Paper outline

**Status legend**: ✅ results in hand · 🟡 partly in hand · ⬜ not started

**Target venue**: _not chosen yet_ (ROADMAP 6.1) — page limit and format depend on it.

## Working title (pick later)

- *From Sensor Events to Caregiver Alerts: Activity Recognition and Routine-Deviation Detection
  with Ambient Sensors, With and Without Activity Boundaries*
- *Routine Deviation, Not Anomaly: Detecting Changes in an Older Adult's Own Routine from Ambient Sensors*

## Research questions

| RQ | Question | Status | Claims |
|---|---|---|---|
| RQ1 | With known activity boundaries, does the choice of model (classical features vs BiLSTM / CNN / Transformer) matter more or less than the input representation? | ✅ | C1, C2 |
| RQ2 | Can routine context — what happened just before and earlier in the day, taken only from the model's own predictions — separate activities that fire the same sensors (Enter/Leave_Home, Wash_Dishes vs Meal_Preparation)? | ✅ | C3, C4 |
| RQ3 | How well does recognition work live, without activity boundaries, compared with the state of the art under the same protocol? | ✅ | C5, C6 |
| RQ4 | How can deviations from a resident's own routine be detected and evaluated when the data has no deviation labels — and how does a routine model compare with generic anomaly detection? | ✅ | C7 |
| RQ5 | How much do recognition errors degrade routine-deviation detection and false-alert rates in the full pipeline? | ✅ | C8 |

RQ5 is likely the most novel contribution: most papers evaluate recognition and routine/anomaly
detection separately, on ground-truth activities. It also directly tests the "interdependence"
and "significant consequences" characteristics claimed in the defense (CCP slide).

## Contributions (draft)

1. A controlled comparison of five recognisers on two CASAS homes under three protocols
   (5-fold CV, temporal split, live sliding window), with 3-seed repeats. → C1, C2, C5
2. Two past-only context features (pre-segment activity; prediction-based routine history)
   that fix the overlapping-activity failures, with an analysis of when history does *not*
   help (label drift). → C3, C4
3. A live sliding-window recogniser that matches or beats LastAct under its own protocol. → C5
4. A per-resident **routine model** (daily activities and their usual times, durations, counts,
   order, day timeline, quiet spells and weekly drift) that reports deviations as observed vs
   expected, an evaluation protocol that injects routine deviations into the raw sensor
   stream, a comparison with generic anomaly detection, and a quantification of error
   propagation from recognition to deviation detection. → C7, C8
5. _(Phase 4–5)_ An open, dataset-agnostic caregiver dashboard driven by the live pipeline,
   with latency measurements. → C9

## Sections

| § | Section | Content | Evidence | Status |
|---|---|---|---|---|
| 1 | Introduction | Ageing in place; cameras/wearables vs ambient sensors; existing products report *which sensor fired*, not *what the resident did* (semantic gap); RQs; contributions | Defense slides 3–7 | 🟡 text exists in slides |
| 2 | Related work | Ambient-sensor HAR (Zhao 2026, Fahad & Tahir 2020, DeepCASAS, LastAct); routine/anomaly detection (Cejudo 2025, Fahad & Tahir 2020); commercial systems (Zemplee, OdeCare) | [references.md](references.md) | 🟡 needs verified citations |
| 3 | Data | CASAS Aruba & Milan; class counts; parsing (corrupted states, per-activity begin/end pairing, 421 overlapping Milan activities); label drift | `ml/har/data.py`, ml/README | ✅ |
| 4.1 | Problem setting | Segment (known boundaries) vs live window (last 100 events, every event) | D4, D6 | ✅ |
| 4.2 | Recognisers | RF, GB on ~160 hand-crafted features; BiLSTM, 1D-CNN, Transformer on token sequences; shared head and training loop | `ml/har/models/`, `train.py` | ✅ |
| 4.3 | Context features | Pre-segment context; two-stage routine history from predictions | D5, `features.py`, `window_history.py` | ✅ |
| 4.4 | Routine model | Routine aspects and the deviation each can show; routine deviation vs generic anomaly detection | D12 | ✅ |
| 4.5 | Evaluation protocol | Synthetic routine deviations injected into raw sensor events; three activity streams | D13 | ✅ |
| 4.6 | Scores, calibration, explanations | Per-aspect scores; alert budget; observed-vs-expected text | D14 | ✅ |
| 4.7 | System | Replay → live inference → routine deviation → alert → dashboard; dataset-agnostic types | ROADMAP 4.x | 🟡 dashboard exists |
| 5.1 | Results: segment HAR | Tables T1, T2; per-class; context/history ablation | C1–C4 | ✅ |
| 5.2 | Results: live HAR | Table T3 vs LastAct / DeepCASAS; per-class | C5, C6 | 🟡 per-class table missing (ROADMAP 1.2) |
| 5.3 | Results: routine deviation | Per deviation type and drift; routine model vs generic AD; error propagation across 3 activity streams | C7, C8 | ✅ drafted (`draft/05-results-routine.md`) |
| 5.4 | Results: alert routing (+ later: latency) | Notifications vs summary per day; urgent deviations notified; delay | C10, C10b (C9 latency pending) | ✅ routing drafted (`draft/05-results-alerts.md`) |
| 6 | Discussion (drafted) | Representation > architecture; why history fails on the temporal split (drift); Milan holiday test period; rare classes; history feedback loop; limits of synthetic deviations; Milan holiday = real routine change | claims.md "limitations" | 🟡 |
| 7 | Ethics & limitations | Privacy, consent, data minimisation, human oversight; two homes, one resident each; no real deviation labels | Defense slide 23 | 🟡 |
| 8 | Conclusion | Lessons and next steps | — | ✅ drafted |

## Planned figures and tables

| ID | What | Source | Status |
|---|---|---|---|
| F1 | Pipeline diagram: sensors → HAR → routine deviation → alert → dashboard | poster / defense slide 16 | 🟡 redraw |
| F2 | Wash_Dishes vs Meal_Preparation event traces (same sensors, same proportions) | defense slide 13 | ✅ |
| F3 | Confusion matrices, best segment model, both homes (before/after history) | `ml/results/<home>/cv/hgb+ctx*/confusion.png` | ✅ |
| F4 | Live-window confusion matrix, BiLSTM, both homes | `ml/results/<home>/window100-last/experiments/bilstm+s*/confusion.png` | ✅ |
| F5 | Label drift: annotations per month for selected activities, both homes | `ml/results/label_drift.png` (`python -m har.label_drift`) | ✅ |
| F6 | Detection vs false alerts per day, per stream and detector | `ml/results/anomaly_curve.png` | ✅ |
| F7 | Dashboard screenshot (monitoring page with a live alert) | ROADMAP 4.4 | ⬜ |
| T1 | All models × homes × {cv, temporal}, macro-F1 & accuracy | `ml/results/summary.md` | ✅ |
| T2 | Context / history ablation with per-class F1 for the hard classes | `summary.md`, `per_class.csv` | ✅ |
| T3 | Live window comparison vs LastAct / DeepCASAS | `ml/results/windows.md` | ✅ |
| T4 | Routine-deviation detection per type, stream and detector | `ml/results/anomaly.md` | ✅ |
| T5 | Alert routing per home and stream | `ml/results/alerts.md` | ✅ |
