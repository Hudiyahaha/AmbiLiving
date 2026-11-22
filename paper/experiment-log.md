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
**Status**: PASS (worked / adopted) · FAIL (did not help; kept for the record) · PENDING (still running) · OPEN (lead, not yet tested)
```

Entries E1–E9 were reconstructed on 18 Nov 2026 from the git history and `ml/README.md`.

---

## At a glance

One line per experiment. Details in the entries below. Update the status when an entry changes.

| # | Experiment | Outcome | Status |
|---|---|---|---|
| E1 | Baseline segment recognition (RF, GB), Aruba | GB macro-F1 84.5; Wash_Dishes almost never found | PASS |
| E2 | Pre-segment context | Enter/Leave_Home 0.81 → 0.98 on Aruba; little change on Milan | PASS |
| E3 | Activity history (segments) | Aruba cv 87.2 → 92.9; no gain on the temporal split; dwell-time features no gain | PASS (cv) · FAIL (temporal, dwell time) |
| E4 | All models under cv | all within ~3 macro-F1; GB best and cheapest | PASS |
| E5 | Temporal split for sequence models | Milan best = BiLSTM 93.6 | PASS |
| E6 | Seeds and learning rate | lr 3e-4 worse and less stable | FAIL (lr change) |
| E7 | Macro-F1 scoring fix | older numbers may be stale | PASS |
| E8 | Prediction confidence stored | input for alerts | PASS |
| E9 | Live sliding windows (LastAct protocol) | BiLSTM Milan 45.6, Aruba 41.9; GB + history Aruba 43.8 | PASS |
| E9 | – smoothing over the last k windows | lowers macro-F1 for every k | FAIL |
| E9 | – history added to the BiLSTM | Milan 45.4 → 38.0, Aruba no gain | FAIL |
| E10 | Label drift figure | Aruba Wash_Dishes labels fade; Milan training period sparsely labelled | PASS |
| E11 | First anomaly run, Milan | too many false alerts (2.0–2.4/day); rule changed | FAIL → fixed |
| E12 | First Aruba run, missed meals | missed detection 0.00; reframed as routine deviation | FAIL → fixed |
| E13 | Milan reruns with the routine model | bug found and fixed; detection 0.88 | PASS |
| E14 | Routine deviation, 3 activity streams | 87–92 % with annotations / segment GB; live BiLSTM Aruba 16 %, Milan 63 % | PASS (gt, seg) · FAIL (Aruba live) |
| E15 | Alert routing | about 1 notification per 11–14 normal days on Aruba | PASS |
| E16 | Live-demo replay | 12/12 scenarios reproduce the evaluated stream | PASS |
| E17 | CNN / Transformer on live windows | neither beats the BiLSTM; Transformer much worse on Aruba (37.1 vs 42.1) | FAIL (BiLSTM kept) |
| E18 | Save the final window model | reloaded model reproduces 100 % of test predictions | PASS |
| E19 | Episode-level view of live recognition | raw stream flickers 13–14×; with a 2-min cleanup Aruba finds 80 % of episodes; Aruba anomaly-pipeline episodes worse than Milan's | PASS · lead tested in E20 |
| E20 | Time-based cleanup of the live stream before routine detection | Aruba live detection 16 % → 45 % at the same false-alert rate; Milan no clear change | PASS (Aruba) · no gain (Milan) |

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

## E17 — CNN and Transformer on live windows  (21 Nov 2026, Aleeza)
**Question**: Does a CNN or Transformer beat the BiLSTM on live windows? (Recent papers use Transformers; we had only tested them with known boundaries.)
**Setup**: D6 protocol, test window every 10th event (same as the `bilstm+te10` runs), 3 seeds, both homes. Rule fixed before the runs: the final model changes only if a model beats the BiLSTM by more than the seed spread on **both** homes.
**Command**: `py -m har.run_windows --dataset all --model cnn --test-stride 10 --seeds 1 2 3` (and `--model transformer`)
**Result**: CNN Milan 43.7 ± 0.6 (BiLSTM 45.4 ± 0.2), Aruba 42.2 ± 0.9 (BiLSTM 42.1 ± 1.4). Transformer Milan 45.1 ± 0.7, Aruba 37.1 ± 2.4 (seeds 37.1, 34.8, 39.5; about 0.6–3 h per Aruba seed on CPU). Stored in `<home>/window100-last/experiments/{cnn,transformer}+te10+s*`.
**Takeaway**: Neither beats the BiLSTM. The CNN ties on Aruba and is worse on Milan; the Transformer ties on Milan and is clearly worse and less stable on Aruba. With ~19k (Aruba) and ~4.6k (Milan) training windows and no pretraining, the attention model has too little data; a GPU would make it faster, not more accurate. Answers the defense question "why not a Transformer like recent papers?".
**Status**: FAIL (BiLSTM kept as the final window model).

## E18 — Save the final window model  (21 Nov 2026, Aleeza, `16e247b`)
**Question**: Can the final BiLSTM be stored and reused without retraining (roadmap 1.1)?
**Setup**: BiLSTM, seed 1, training days only; one file per home with weights, context normalisation, vocabulary, classes and window settings (`ml/models/<home>/window100-bilstm-s1.pt`, about 400 KB).
**Command**: `py -m har.saved_model --dataset all --model bilstm --seed 1 --check`
**Result**: reloaded in a fresh process, predictions match the stored test run on 100 % of windows (Milan 107,934, Aruba 322,880).
**Takeaway**: The replay and a future backend can load `har.saved_model.load(...)` instead of retraining.
**Status**: PASS

## E19 — Episode-level view of live recognition  (21 Nov 2026, Aleeza)
**Question**: Per-event macro-F1 (about 42 on Aruba) punishes every boundary error. Routine detection uses episodes. How good are the live predictions at the episode level, and is flickering the reason live routine detection fails on Aruba (16 % vs 63 % on Milan, E14)?
**Setup**: stored per-event test predictions (`bilstm+s1`; Aruba also `hgb+histpast+bal+tr10+s1`) vs annotated test-day episodes. Episode = run of the same predicted activity. Match = same activity, overlapping within ±15 min. Three versions of the predicted stream: *raw* (every event), *anomaly-pipeline* (exactly what `run_anomaly` uses: every 10th event, runs shorter than 3 points absorbed, per day), *clean2* (runs shorter than 2 min absorbed into the previous one; past only; diagnostic, **not tuned**).
**Command**: `py -m har.episode_eval --dataset all --run bilstm+s1 hgb+histpast+bal+tr10+s1 --write`
**Result** (`ml/results/episodes.md`; found = episode recall, precision = share of predicted episodes that are real, mean over activities):

| Home, model | Stream | Found % | Precision % | Episodes/day (true → predicted) |
|---|---|---|---|---|
| Aruba BiLSTM | raw | 96.2 | 28.1 | 29.2 → 389.8 |
| Aruba BiLSTM | anomaly-pipeline | 65.7 | 37.7 | 29.2 → 38.5 |
| Aruba BiLSTM | clean2 | 79.6 | 53.9 | 29.2 → 29.9 |
| Aruba GB + history | anomaly-pipeline | 57.0 | 47.3 | 29.2 → 30.0 |
| Aruba GB + history | clean2 | 68.7 | 55.2 | 29.2 → 26.0 |
| Milan BiLSTM | raw | 89.8 | 45.6 | 45.3 → 650.9 |
| Milan BiLSTM | anomaly-pipeline | 69.4 | 64.1 | 45.3 → 53.7 |
| Milan BiLSTM | clean2 | 66.3 | 63.1 | 45.3 → 45.5 |

**Takeaway**:
1. The raw live stream flickers badly: 13× (Aruba) to 14× (Milan) more episodes than really happen. Almost every real episode is touched (found 90–96 %), but most predicted episodes are fake.
2. With a simple 2-min cleanup, Aruba's main activities come out well at the episode level (e.g. Meal_Preparation found 89 % / precision 68 %, Sleeping 95 / 61, Bed_to_Toilet 80 / 83, Leave_Home 78 / 85). Eating, Work, Wash_Dishes and Respirate stay weak. This answers "how can you detect deviations if recognition is 42 F1": per-event F1 understates what the episode-level routine needs.
3. **Lead**: on Milan the anomaly pipeline's episodes are as good as clean2 (64 vs 63 precision). On Aruba they are clearly worse (38 vs 54 precision, 66 vs 80 found). Milan's live detection works (63 %) and Aruba's does not (16 %), so the episode-building step may be part of the Aruba failure.
**Status**: PASS (diagnosis). The lead in point 3 was tested in E20. Next test: rerun the routine-deviation evaluation (E14) on Aruba with a cleanup chosen on the observation days, not the test days, and see whether live detection rises above 16 %.

## E20 — Time-based cleanup of the live stream before routine detection  (21 Nov 2026, Aleeza)
**Question**: E19 showed the anomaly pipeline's live episodes are much worse on Aruba than a simple time-based cleanup. Does a better cleanup raise Aruba's live routine-deviation detection (16 % in E14)?
**Setup**: E14 protocol unchanged (same 603 / 166 day copies, routine model, 0.1 alerts per normal day per aspect, same matching rule). One extra live stream `winc`: predicted runs shorter than N minutes are absorbed into the run before (past only). N chosen **on the observation days only**, by episode F1 against the observation-day annotations (grid 0.5–10 min; monitoring days and injections never used): Aruba N = 3 (episode F1 0.498 vs 0.387 for the current 3-point rule), Milan N = 1 (0.679 vs 0.643). Saved BiLSTM (E18) reused. Generic baseline not rerun. Needed a pandas 3 fix in `anomaly_inject.day_events` (segment times cast to ns).
**Command**: `py -m har.run_anomaly --dataset all --methods routine --win-clean auto --tag e20`
**Result** (`ml/results/<home>/anomaly-e20/`; detection % at the operating point):

| Home | Stream | Missed | Prolonged | Unusual time | Night toilet | Inactivity | Mean detection | F1 | False alerts / day |
|---|---|---|---|---|---|---|---|---|---|
| Aruba | win (current) | 5 | 11 | 13 | 39 | 11 | 16 | 16 | 1.30 |
| Aruba | **winc (3 min)** | 21 | 20 | 17 | 81 | 86 | **45** | **38** | 1.34 |
| Milan | win (current) | 77 | 33 | 56 | 49 | 100 | 63 | 48 | 3.08 |
| Milan | winc (1 min) | 62 | 67 | 67 | 69 | 100 | 73 | 53 | 5.00 |

Over the whole budget sweep (`sweep.csv`), Aruba `winc` is better at every false-alert level, e.g. 53 % vs 27 % at about 2.4 false alerts/day and 62 % vs 49 % at about 5. On Milan the two curves are about the same at matched false alerts (win 67 % at 4.1/day, winc 64 % at 3.3 and 73 % at 5.0): the gain at the operating point comes with more false alerts.
Reproduction check: `gt` and `win` reproduce E14 exactly (Aruba 92 % / 16 %, Milan 88 % / 63 %). **`seg` does not**: Aruba 93 % here vs 87 % in E14 (prolonged 89 vs 68), Milan the same 88 %. Unexplained so far, possibly the pandas 3 environment; to check with Hudiya before quoting either number.
**Takeaway**: Part of the Aruba live failure was the episode-building step, not recognition: with a cleanup chosen on observation days, inactivity (11 → 86 %) and night toilet trips (39 → 81 %) are found almost as often as with annotations, at the same false-alert rate. Missed meals, prolonged and unusual-time deviations stay weak (17–21 %); those need better recognition of the activities themselves. Milan, where the live stream already worked, does not gain.
**Status**: PASS on Aruba (adopt the time-based cleanup for the live stream). No gain on Milan. OPEN: the `seg` mismatch.
**Alert routing on E20** (`py -m har.alerts --folder anomaly-e20`, `ml/results/alerts-e20.md`): Aruba urgent deviations notified 7 % → 34 %, notifications per normal day 0.20 → 0.27. Milan urgent 51 % → 64 % but notifications per normal day 0.23 → 0.69 (one every ~1.5 days), so Milan keeps the 3-point rule.
**Adopted in the live demo** (21 Nov): `py -m har.replay` now reads `anomaly-e20` and replays Aruba with the 3-min cleanup (`winc`) and Milan with the original rule (`win`). All 12 scenarios reproduce the evaluated stream, 0 batch alerts missing live; Milan's files are byte-identical to before. Aruba example days changed because they are picked among the copies the cleaned stream catches.

## E21 — Live routine monitoring on pushed events  (22 Nov 2026, Hudiya)
**Question**: Does the backend's live pipeline (saved BiLSTM + saved routine model + D15 routing, run incrementally on pushed events, D18) give the same activities and alerts as the evaluated replay, and is it fast enough to run live?
**Setup**: Routine model refitted and saved with the E20 operating point (`py -m har.routine_live`): Aruba `winc` (3 min) on 44 observation days (2011-03-16 – 2011-04-28), Milan `win` on 13 (2009-12-12 – 2009-12-24), the same numbers of days as E20. Check: each home's real monitoring day in `public/replay/` (Aruba 2011-05-05, Milan 2009-12-29) taken from the raw data, with 150 earlier events as history, pushed (a) as a whole-day re-run every 2 min, (b) in 1-hour (Milan) / 7-minute (Aruba) batches through `LiveMonitor`, (c) over HTTP in 2-hour batches with a clock time (`tests/test_api.py`). Timing over HTTP on the dev laptop (CPU): Aruba, catch-up to 18:00 in one push, then 300 single-event pushes.
**Command**: `py -m har.routine_live --check`; `py -m pytest tests -q` (from `ml/`)
**Result**:

| Home | Predictions (ours / replay) | Identical | Alerts (ours / replay) | Same time raised, type, activity, tier, delivered |
|---|---|---|---|---|
| Aruba | 551 / 551 | 100 % | 2 / 2 | yes (a, b) |
| Milan | 1,159 / 1,159 | 100 % | 3 / 3 | yes (a, b, c) |

Latency: fitting 41 s (Aruba) / 8 s (Milan); re-running a whole day every 2 min 15.5 s / 23.2 s. Live session over HTTP: catch-up push of 3,998 events 4.2 s; single-event pushes median 10 ms, p95 32 ms (max 1.0 s when one push crossed a long silence); a clock-only push over 2 h (63 routine steps) 0.97 s.
**Takeaway**: The live backend reproduces the evaluated live pipeline exactly, event by event, and keeps up with a real home by a wide margin (Aruba produces an event every ~15 s on average).
**Status**: PASS. Feeds ROADMAP 5.2 (latency) and 5.1 (end-to-end test).

## E22 — Per-class results and confidence of the final live window model  (22 Nov 2026, Hudiya)
**Question**: Which activities does the final live BiLSTM recognise, and can its confidence tell right from wrong answers (ROADMAP 1.2, 1.3)?
**Setup**: No retraining. Stored test predictions of `window100-last/experiments/bilstm+s{1,2,3}` (the runs behind C5: last 100 events, test window at every event), both homes. Per-class precision / recall / F1 averaged over seeds; a confidence cutoff sweep (predictions below it treated as unknown) and a reliability table.
**Command**: `py -m har.window_report` → `ml/results/windows_detail.md`
**Result**: Per-class F1 (3-seed mean): Aruba Relax 0.75, Meal_Preparation 0.68, Bed_to_Toilet 0.53, Sleeping 0.45, Enter_Home 0.45, Work 0.41, Eating 0.30, Respirate 0.30, Leave_Home 0.27, Wash_Dishes 0.06. Milan Read 0.77, Sleep 0.76, Desk_Activity 0.70, Kitchen_Activity 0.69, Watch_TV 0.61, Dining 0.53, Master_Bedroom 0.52, the bathrooms 0.46, Leave_Home 0.29, Bed_to_Toilet 0.28, Meditate 0.25, Morning_Meds 0.04, Eve_Meds 0.02. Confidence: accuracy rises steadily with confidence but stays above it (0.4–0.5 → 66–68 % right; 0.5–0.6 → 73–84 %); only 14–15 % of predictions reach 0.6.

| Cutoff | Aruba kept / accuracy on kept / macro-F1 on kept | Milan kept / accuracy / macro-F1 |
|---|---|---|
| none | 100 / 63.8 / 41.9 | 100 / 58.8 / 45.6 |
| 0.4 | 59 / 77.5 / 55.2 | 52 / 73.9 / 56.3 |
| 0.5 | 39 / 82.9 / 61.9 | 30 / 79.2 / 60.2 |
| 0.6 | 14 / 80.0 / 66.6 | 15 / 85.6 / 58.9 |

**Takeaway**: Errors concentrate on the rare activities and on those that share sensors with frequent ones (Leave_Home vs Enter_Home, medicine vs kitchen). The model is under-confident, so the 0.6 cutoff in `metrics.json` is too strict; around 0.4 is the useful floor for "unknown" if one is added to alert routing.
**Status**: PASS (analysis). Not yet applied to routing.

## E23 — Recorded days as live sensor feeds  (22 Nov 2026, Hudiya)
**Question**: Can the dashboard be driven live by recorded days without changing what the pipeline computes (D19)?
**Setup**: `py -m har.feeds` rebuilds the 12 live-demo scenario days (per home: the real monitoring day + 5 injected types; injected days with the E14/E20 injection settings, 3 copies per type and day, seed 0, matched to the scenario by day, type, target, start and note) with full timestamps and 150 events from the evening before. Each feed is pushed through `LiveMonitor` with the saved models; one feed is also played over HTTP as a simulation at 3600× (`tests/test_api.py`), and the Aruba "long silence" day was watched in the browser at 60×→900×.
**Command**: `py -m har.feeds`; `py -m pytest tests -q` (from `ml/`)
**Result**: 12 / 12 feeds give exactly the scenario's predictions (Aruba 525–766 per day, Milan 386–1,159) and alerts (0–4 per day, same time raised, type, activity, tier, delivered). Feeds total 1.4 MB. In the browser the inactivity alert appeared live at 11:32 as a notification, as in the replay.
**Takeaway**: The dashboard now shows the live pipeline itself, not a precomputed result, and on these days it is the evaluated pipeline.
**Status**: PASS.
