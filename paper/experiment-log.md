# Experiment log

A dated lab notebook. **Add an entry for every run or batch of runs that produced a number** —
including the ones that did not work. Newest entries at the bottom.

Template:

```
## E<n> — <title>  (<date>, <who>, commit <hash>)
**Question**: what we wanted to find out
**Setup**: home(s), protocol, model(s), seeds, anything non-default
**Command**: py -m har....
**Result**: headline numbers + where they are stored
**Takeaway**: what it means; claim IDs it supports or kills
```

Entries E1–E9 were reconstructed on 18 Nov 2026 from the git history and `ml/README.md`.

---

## E1 — Baseline segment recognition, Aruba  (10 Oct 2026, Hudiya, `70ac0d0`)
**Question**: How well do classical models do with known activity boundaries?
**Setup**: Aruba, 5-fold stratified CV, RF and GB on ~160 hand-crafted features.
**Result**: GB macro-F1 84.5, RF 83.2; accuracy ~96 % (current values after the D3 rescore are in `summary.md`). Wash_Dishes recall 0.03–0.09; Enter/Leave_Home ~0.80 F1.
**Takeaway**: Accuracy matches prior work (Fahad & Tahir 96.19 %) but macro-F1 exposes the overlapping-activity problem from the defense. → C1

## E2 — Pre-segment context  (10–12 Oct 2026, `70ac0d0`, `76eba90`)
**Question**: Can what happened just before an activity separate Enter_Home from Leave_Home?
**Setup**: `--context`: gap since previous event, events and distinct sensors in the previous 10 min. All models, both homes, cv.
**Result**: Aruba GB Enter_Home F1 0.81 → 0.98, Leave_Home 0.81 → 0.98; ~+3 macro-F1 for every model on Aruba; little change on Milan.
**Takeaway**: → C2, C3

## E3 — Activity history  (10 Oct 2026, Aleeza, `f3bbc5b`)
**Question**: Can routine (e.g. washing up follows a meal) separate Wash_Dishes from Meal_Preparation?
**Setup**: `--history`, two-stage, history from stage-1 predictions; rf/hgb; `--balance full` variant; both homes; cv and temporal.
**Result**: Aruba cv 87.2 → 92.9 (Wash_Dishes recall 0.06 → 0.42); Milan cv 91.4 → 92.5. No gain on the temporal split. `--balance full`: Wash_Dishes F1 0.56 but lower macro-F1 (92.24). Per-sensor dwell-time features on top: no gain (0.54 → 0.55). True-label history upper bound 93.4 (not committed).
**Takeaway**: → C4, C4b, C4c, C4d. Temporal non-gain explained by Wash_Dishes label drift.

## E4 — Full model comparison under CV  (12 Oct 2026, Hudiya, `76eba90`)
**Question**: Do the sequence models beat the classical ones?
**Setup**: BiLSTM, 1D-CNN, Transformer (+ ctx variants) on both homes; RF/GB on Milan. 5-fold CV.
**Result**: All within ~3 macro-F1; GB strongest and cheapest. Transformer ~4 h CPU on Aruba.
**Takeaway**: → C1, C2, C2b. Transformer + ctx under cv not run.

## E5 — Temporal split for sequence models  (13 Oct 2026, Ibrahim, `64e14a0`)
**Setup**: BiLSTM, CNN, Transformer (± ctx), both homes, temporal split.
**Result**: In `summary.md`. Milan temporal best = BiLSTM 93.55.

## E6 — Seeds and learning-rate tuning  (13 Oct 2026, Ibrahim, `e0d4759` … `d4bb74a`)
**Question**: Are the temporal results stable across seeds? Does lr 3e-4 help?
**Setup**: 3 seeds for all models (temporal), lr 3e-4 variants for neural models.
**Result**: `experiments.md`. Aruba: GB + ctx 90.19 ± 1.05, BiLSTM + ctx 90.08 ± 0.77. Milan: BiLSTM 94.89 ± 0.79. lr 3e-4 was worse on average in every case except Aruba CNN + ctx (86.75 vs 86.41, well within noise), and much less stable (std up to 6.7).
**Takeaway**: → C4e. Neural models are seed-sensitive on the temporal split.

## E7 — Macro-F1 scoring fix  (13 Oct 2026, Ibrahim, `b544d7d`, `7808fbc`)
**What changed**: macro-F1 now averages only classes present in the test set; every run rescored. → D3
**Takeaway**: Any number written before 13 Oct (including old `ml/README.md` tables) may be stale.

## E8 — Prediction confidence  (13 Oct 2026, Aleeza, `dbc4627`)
**Setup**: every model now writes per-prediction confidence and a summary (mean confidence when right/wrong; mistakes caught by a 60 % / 80 % cutoff).
**Takeaway**: Input for alert design. → C6c

## E9 — Live sliding-window recognition  (14 Nov 2026, Aleeza, `a971cad`, `0210ce3`)
**Question**: How well does recognition work without activity boundaries, compared with LastAct?
**Setup**: D6 protocol. RF, GB (± ctx, ± history, ± balancing, train stride 10), BiLSTM (± history, test stride 1 and 10); 3 seeds for the finalists; smoothing k sweep; `last` and `other` label rules.
**Command**: `py -m har.run_windows --dataset all --model bilstm --seeds 1 2 3`
**Result**: `windows.md`. BiLSTM Milan 45.6 ± 0.6, Aruba 41.9 ± 1.5; GB + history Aruba 43.8 ± 0.4. History hurts BiLSTM (Milan 45.4 → 38.0). Smoothing always hurts. `other` rule: GB Aruba 51.3 / acc 81.2, Milan 35.3.
**Takeaway**: → C5, C5b, C5c, C6, C6b. Plain BiLSTM chosen by the pre-set rule D8.

---

<!-- New entries below this line -->

## E10 — Label drift figure  (18 Nov 2026, Hudiya)
**Question**: Does annotation density change over time enough to explain temporal-split results?
**Command**: `py -m har.label_drift` → `ml/results/label_drift.png`, `label_drift.csv`
**Result**: Aruba Wash_Dishes 20 → 0–5 per month (Nov 2010 → Mar–Jun 2011) while Meal_Preparation stays ~240. Milan the opposite: Kitchen_Activity 90 (Nov) → 342 (Dec), Morning_Meds 1 → 23.
**Takeaway**: Supports C4c; new claim C6d (Milan's training period is sparsely labelled compared with its observation/monitoring periods).

## E11 — Anomaly pipeline, first Milan run (annotations + segment streams)  (18 Nov 2026, Hudiya)
**Question**: Does the D13/D14 pipeline run end to end, and are false alerts in a sensible range?
**Setup**: Milan, 13 monitoring days, 166 injected copies; streams `gt`, `seg`; statistical + autoencoder.
**Result**: Detection 0.86 (gt/stat), 0.87 (seg/stat), but **2.0–2.4 false alerts per clean day**. Breakdown: most false alerts came from the `missed` rule (e.g. "no Leave_Home by 14:15" on 6 of 13 holiday days), which — unlike every other score — used a fixed deadline (90th percentile of first occurrence + 1 h) instead of the calibrated alert budget.
**Change made after seeing these numbers**: `missed` now uses the same calibration as the other scores (leave-one-day-out lateness of each daily activity's first occurrence on the observation days, budget 0.1/day). D14 updated. No other parameter was changed after seeing monitoring-day results; this one change must be reported in the paper.
**Result after the change**: false alerts 1.15 (gt/stat), 0.77 (seg/stat) per clean day; detection 0.80 / 0.79.

## E12 — Aruba first run; reframing as routine deviation  (18 Nov 2026, Hudiya)
**Observed**: Aruba, annotations stream, old statistical detector: **missed meal detection 0.00** (prolonged 0.65, unusual time 0.95, night trips 1.00, inactivity 0.92; 0.95 false alerts/day). Cause: one lateness threshold shared by all daily activities; often-skipped ones (Leave_Home absent on 23 % of observation days) used up the 0.1/day budget.
**Decision (with the team)**: the project is *routine deviation*, not generic anomaly detection (D12 rewritten). Changes: per-activity first-occurrence survival for `missed`; new routine aspects `unusual_order` (transitions), `timeline` (2-hour occupancy blocks) and multi-day `drift` (rolling 7-day window; injected 7-day runs where breakfast moves 20 min later per day); the autoencoder became a stand-alone **generic anomaly-detection baseline**. Run stopped and restarted with the new design.

## E13 — Milan reruns with the routine model (annotations + segment streams)  (18 Nov 2026, Hudiya)
**Run 1** (`--reuse` not possible, new variants): missed detection 0.00 — traced to a bug (`-log(S).max()` instead of `-log(S.min())`). **Run 2** after the fix: routine model detection 0.88 (gt) / 0.88 (seg), missed 1.00 / 0.92, but 3.0 / 2.7 false alerts per clean day. Breakdown of the 39 clean-day alerts (gt): missed 13 (Leave_Home 6, Kitchen_Activity 5), timeline 10, frequency 7, prolonged 4, order 4, inactivity 1. Two causes: (i) a calibration mismatch — the empirical survival is a step function with different ceilings for 12 (calibration) and 13 (monitoring) days; (ii) genuine holiday behaviour (no going out on 6 of 13 Christmas days).
**Change**: (i) fixed with a smooth survival (D14 change 3). (ii) left as is: these are real routine deviations and are reported as such. **Run 3**: detection 0.88 / 0.88, false alerts 2.77 / 2.46 per clean (holiday) day; generic baseline 0.19 / 0.18 detection at 0.54 / 0.46 false alerts per day (it cannot see missed activities or inactivity at all: 0.00). Drift 0 / 2 runs on Milan (13 observation days give a very noisy weekly baseline).

## E14 — Full routine-deviation run, both homes, three streams  (18 Nov 2026, Hudiya)
**Setup**: D13/D14 as rewritten in E12–E13. Aruba: 44 observation / 44 monitoring days, 510 injected single-day copies, 7 drift runs. Milan: 13 / 13 days, 166 copies, 2 drift runs. BiLSTM (seed 1) trained once per home and saved (`bilstm.pt`, git-ignored). Command: `py -m har.run_anomaly --dataset all`.
**Run 1 result (mean detection, routine vs generic; false alerts per clean day)**: Aruba annotations 0.92 vs 0.04 (1.34 / 0.02), segment GB 0.87 vs 0.10, **live BiLSTM 0.15** vs 0.01. Milan 0.88 vs 0.19, 0.88 vs 0.18, live 0.63 vs 0.08. Matched false alerts: routine 56 % vs generic 18 % (Aruba annotations), 55 % vs 25 % (segment), but 13 % vs 17 % on Aruba live.
**Diagnosis of the Aruba live collapse (not a bug)**: (i) *inactivity* — in the observation period the live BiLSTM rarely recognises Leave_Home, so time when the resident is out is labelled Relax/Work; the learned "usual quiet spell during Relax" becomes 188 min (51 min from annotations), so a 3 h injected silence looks normal; (ii) *missed* — deleting the *annotated* cooking segments leaves Aruba's unannotated kitchen movement in the stream; the live model still predicts ~6 cooking episodes on those days (10 on clean days), so cooking never looks absent. (ii) is partly a limit of the injection, not only of recognition.
**Drift**: Aruba 2 / 7 runs (5-day delay) on annotations and segment streams, 0 / 7 live; drift raises ~1.1–1.4 false alerts per clean Aruba day (May–June vs March–April: seasonal routine change). Milan 0 / 2 (1 / 2 live).
**Changes made after seeing these results** (reported; re-run on the cached streams as run 2): (a) the usual-time range shown to caregivers is computed on the circle (sleep showed "usually between 00:17 and 23:27"); (b) activities whose first occurrence of the calendar day is usually the tail of the previous night (≥ 20 % before 04:00, e.g. Sleeping) are excluded from `missed` and `drift`, because "not yet today" is undefined for them (the dashboard showed "Sleeping later than usual: 10:23 vs 03:26"). Dashboard export also de-duplicates drift alerts repeated on consecutive days (display only).

## E15 — Alert routing  (19 Nov 2026, Hudiya)
**Question**: Can the sensitive detector be turned into a tolerable number of caregiver interruptions without losing possible emergencies?
**Setup**: Decision D15 written before evaluation. Routing applied to the operating-point alerts of E14 run 2 (`py -m har.alerts`): notify (inactivity, bathroom/toilet prolonged, night leaving/cooking, missed meds; 2 h cool-down), evening summary (max 3, by priority), dashboard-only (timeline, order).
**Result** (`ml/results/alerts.md`): notifications per clean day 0.07 / 0.09 / 0.20 (Aruba annotations / segment / live), 0.15 / 0.31 / 0.23 (Milan); urgent injected deviations notified 94 / 63 / 7 % (Aruba), 73 / 79 / 51 % (Milan), median delay 43–84 min; non-urgent surfaced 83 / 80 / 5 % (Aruba), 86 / 83 / 38 % (Milan).
**Takeaway**: → C10, C10b. Routing works where recognition works; Aruba segment GB loses night-time cooking notifications (91 % detected, 44 % notified) because the moved episode is mis-labelled and routed to the summary.
**Note**: Aruba's annotations contain duplicate segments that produce identical alerts; the dashboard export lists each once. Evaluation counts are unaffected for detection and slightly inflate alerts per day.

## E16 — Live-demo replay  (19 Nov 2026, Hudiya)

**Setup**: Decision D17. `py -m har.replay` with the cached streams and BiLSTM from E14, routine model on the live (win) stream at 0.1 alerts per normal day per aspect, re-run every 2 minutes of each scenario day.
**Result**: 12/12 scenarios reproduce the evaluated live stream exactly. In every scenario, every batch alert was also raised live (0 missing).
- **Milan**: inactivity notified at 15:58, 1 h 45 min into a 170-min silence. Night-time kitchen activity notified at 03:36 (moved to 03:26). Missed kitchen activity reaches the summary (flagged at 09:35). Extra night toilet trips appear only as one "master bathroom at an unusual time" summary item. The prolonged bathroom visit is not caught: on Milan's live stream such visits are detected 33 % of the time and never notified.
- **Aruba**: the caught examples are rare (inactivity 4 % notified overall). The "extra toilet trips" day is matched only through a mis-recognised "meal preparation at 02:55".
- **Clean days**: Milan's median clean day has 2 summary items and 1 insight. Aruba's has 1 false notification (41 min of quiet at 08:01 while recognised as sleeping).

**Takeaway**: The demo shows the pipeline working in time, and also its failures. Use Milan for presentations; the Aruba scenarios illustrate C8 (live recognition corrupts the routine).
