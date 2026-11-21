# Claims → evidence

Every number the paper uses must appear here with the file it comes from. Values are %
unless they are per-class F1 (0–1). "Segment" = known activity boundaries; "window" = live,
last 100 events at every event.

**Status**: ✅ supported · 🟡 supported but needs a caveat or one more run · ⬜ planned, no evidence yet · ❌ dropped (keep the row and say why)

## Activity recognition — segment setting (RQ1, RQ2)

| ID | Claim | Evidence | Status |
|---|---|---|---|
| C1 | All five recognisers reach 95–99 % accuracy but differ in macro-F1; accuracy hides failures on rare/overlapping classes, so macro-F1 is the headline metric | [summary.md](../ml/results/summary.md): Aruba cv accuracy 95.4–99.0, macro-F1 82.3–92.9 | ✅ |
| C2 | Representation matters more than architecture: on Aruba cv, pre-segment context adds ~3 macro-F1 to every model (RF 83.23→86.14, GB 84.52→87.18, BiLSTM 82.25→85.51, CNN 82.80→86.15), more than the spread between models | summary.md, Aruba cv | 🟡 Aruba only — on Milan cv context changes little (GB 91.01→90.97, BiLSTM 89.01→90.61, CNN 86.56→86.41). Say so. Transformer + ctx missing under cv (ROADMAP 1.4) |
| C2b | Gradient Boosting is the best or near-best model and trains in seconds vs minutes (BiLSTM, CNN) or hours (Transformer) on CPU | summary.md "Time (s)" column: Aruba cv GB 193 s, BiLSTM 1454 s, Transformer 14 228 s | ✅ |
| C3 | Pre-segment context fixes Enter_Home vs Leave_Home (Aruba cv, GB): F1 0.81 → 0.98 for both | `ml/results/aruba/cv/hgb/per_class.csv` (0.8124 / 0.8066) vs `hgb+ctx/per_class.csv` (0.9779 / 0.9756) | ✅ |
| C4 | Routine history built only from the model's own predictions lifts Wash_Dishes (Aruba cv, GB + ctx): F1 0.10 → 0.50, recall 0.06 → 0.42; Respirate F1 0.80 → 0.91; macro-F1 87.18 → 92.92 | `aruba/cv/hgb+ctx/per_class.csv` vs `aruba/cv/hgb+ctx+hist/per_class.csv`; summary.md | ✅ |
| C4b | Milan cv also gains from history: GB + ctx 90.97 → 92.52 | summary.md | ✅ |
| C4c | History does **not** help on the temporal split (Aruba 92.75 → 91.47, Milan 90.69 → 90.05), consistent with Wash_Dishes annotations fading from ~20/month (Nov 2010) to 0–5/month (from Mar 2011): only 6 Wash_Dishes labels in Aruba's last 30 % of days | summary.md; F5 [label_drift.png](../ml/results/label_drift.png) / `label_drift.csv`: Wash_Dishes 20, 7, 17, 9, 5, 2, 5, 0 per month (Nov 2010 – Jun 2011) | ✅ |
| C4d | Upper bound: history from true labels reaches 93.4 on Aruba cv, so predicted history loses almost nothing | ml/README.md (run "not committed") | 🟡 re-run and archive before citing |
| C4e | Best segment results: Aruba cv 92.92 ± 3.74 (GB + ctx + hist), Aruba temporal 92.75 (GB + ctx; 3 seeds 90.19 ± 1.05), Milan cv 92.52 ± 1.73 (GB + ctx + hist), Milan temporal 93.55 (BiLSTM; 3 seeds 94.89 ± 0.79) | summary.md, [experiments.md](../ml/results/experiments.md) | ✅ |

## Activity recognition — live window setting (RQ3)

| ID | Claim | Evidence | Status |
|---|---|---|---|
| C5 | Under the LastAct protocol, our BiLSTM reaches Milan 45.6 ± 0.6 macro-F1 (LastAct 40.1 ± 0.5) and Aruba 41.9 ± 1.5 (LastAct 44.6 ± 1.9); GB + routine history reaches Aruba 43.8 ± 0.4 | [windows.md](../ml/results/windows.md), 3 seeds | ✅ — LastAct numbers are as reported in their paper, not re-run |
| C5b | The window model was chosen by a rule fixed before the runs (BiLSTM + history only if history helped on both homes); it did not on Milan (45.4 → 38.0 at test stride 10), so plain BiLSTM was chosen | windows.md; decision D8 | ✅ |
| C5c | Smoothing predictions over the last k windows lowered macro-F1 for every k; validation picked k = 1 | windows.md | 🟡 archive the smoothing runs' numbers in the log |
| C5d | Neither a 1D-CNN nor a Transformer beats the BiLSTM on live windows (test stride 10, 3 seeds): CNN Aruba 42.2 ± 0.9 / Milan 43.7 ± 0.6, Transformer 37.1 ± 2.4 / 45.1 ± 0.7, BiLSTM 42.1 ± 1.4 / 45.4 ± 0.2 | windows.md; experiment log E17 | ✅ |
| C6e | At the episode level the raw live BiLSTM stream finds 96 % (Aruba) / 90 % (Milan) of annotated episodes but predicts 13–14× too many (precision 28 / 46 %); merging runs < 2 min gives Aruba 80 % found, 54 % precision, 30 vs 29 episodes/day | [episodes.md](../ml/results/episodes.md); E19 | ✅ |
| C6 | Live recognition is far harder than segment recognition (~42–46 vs ~92 macro-F1); rare and overlapping activities stay poor — e.g. BiLSTM seed 1: Aruba Wash_Dishes F1 0.09, Milan Eve_Meds 0.02 / Morning_Meds 0.02 | `<home>/window100-last/experiments/bilstm+s1/per_class.csv` | 🟡 replace with 3-seed mean table (ROADMAP 1.2) |
| C6b | Milan's test days (25 Dec – 6 Jan) are a holiday period: validation ≈ 46 vs test ≈ 38 macro-F1 for the same GB model | windows.md | ✅ |
| C6d | Milan's annotation density changes sharply over time: Kitchen_Activity 55 / 90 / 342 / 67 annotations in Oct / Nov / Dec / Jan (partial months Oct, Jan), Morning_Meds 11 / 1 / 23 / 6 — so the training period (to 11 Dec) is annotated much more sparsely than the observation and monitoring periods | `ml/results/label_drift.csv` | ✅ |
| C6c | The live BiLSTM is rarely confident: Aruba seed 1, 88 % of predictions have confidence < 0.6; accuracy on the rest is 79.7 % | `aruba/window100-last/experiments/bilstm+s1/metrics.json` → `confidence` | 🟡 summarise over seeds and homes (ROADMAP 1.3); relevant to alert design |

## Routine deviation and system (RQ4, RQ5)

Source for every number below: `ml/results/anomaly.md` (generated from `ml/results/<home>/anomaly/summary.json`). Filled in when the full run finishes.

| ID | Claim (hypothesis until supported) | Evidence | Status |
|---|---|---|---|
| C7 | A per-resident routine model detects injected routine deviations far better than a generic anomaly detector: 87–92 % (Aruba) and 88 % (Milan) vs 4–19 % with annotated or segment activities; at matched false alerts 56 vs 18 %, 55 vs 25 % (Aruba), 88 vs 38 % (Milan), 63 vs 22 % (Milan live). The generic detector finds 0 % of missed meals and inactivity on every stream | `ml/results/anomaly.md` (T4 + matched table) | ✅ |
| C7b | Gradual drift (breakfast +20 min/day) is detected in 2 / 7 Aruba runs (median 5 days) on annotation and segment streams, 0 / 7 live; Milan 0 / 2 (1 / 2 live). Clean Aruba weeks raise 0.69–0.90 drift alerts per day (May–June vs March–April) | `anomaly.md` drift column | 🟡 weak result; report as such |
| C8 | Detection degrades little from annotations to segment GB (92 → 87 % Aruba, 88 → 88 % Milan) and sharply to the live BiLSTM on Aruba (→ 16 %), less on Milan (→ 63 %). Mechanisms: wrong learned quiet-spell norm when Leave_Home is missed (188 vs 51 min for Relax; inactivity 93 → 11 %), and unannotated kitchen movement predicted as cooking (missed 98 → 5 %) | `anomaly.md`; diagnosis in experiment log E14 | ✅ |
| C8c | A past-only time-based cleanup of the live stream (runs < N min merged; N chosen on observation days: Aruba 3, Milan 1) raises Aruba live detection 16 → 45 % at 1.30 → 1.34 false alerts/day (inactivity 11 → 86, night toilet 39 → 81; missed / prolonged / unusual time 17–21 %); better at every sweep point; no gain on Milan at matched false alerts | `ml/results/<home>/anomaly-e20/summary.json`, `sweep.csv`; E20 | ✅ (Aruba segment row did not reproduce, 93 vs 87 %; not used) |
| C8b | On Milan's holiday monitoring days, clean-day alerts include genuine routine changes: cooking late on 5 days, no leaving home by mid-afternoon on 3, 10 timeline changes | `ml/results/milan/anomaly/alerts_gt_routine.csv` | ✅ |
| C10 | Routing by urgency (D15) turns ~1.3 detected deviations per normal day into 0.07–0.09 notifications per clean day on Aruba (one every 11–14 days) and 0.15–0.31 on Milan, while notifying 94 % / 63 % (Aruba annotations / segment GB) and 73 % / 79 % (Milan) of urgent injected deviations, median delay 43–71 min; missed meals and night toilet trips reach the evening summary in 98–100 % of cases with recognised activities | `ml/results/alerts.md`, `<home>/anomaly/routing.json` | ✅ |
| C10c | With the cleanup, Aruba urgent deviations notified rise 7 → 34 % at 0.27 notifications/clean day; Milan 51 → 64 % but 0.69/day, so Milan keeps the 3-point rule | [alerts-e20.md](../ml/results/alerts-e20.md) | ✅ |
| C10b | Routing depends on the activity label: Aruba segment GB detects night-time cooking/leaving in 91 % of cases but notifies only 44 %, because mis-recognised episodes are routed to the summary | `alerts.md` per-type table vs `anomaly.md` | ✅ |
| C9 | The live pipeline runs within an acceptable per-event latency and false-alert rate per day | ROADMAP 3.2, 5.2 | ⬜ |

## Limitations to state (not claims, but must appear)

- Two homes, one resident each (Milan also has a pet), from 2009–2011.
- No real routine-deviation labels in CASAS; results rely on synthetic injection into the raw sensor stream.
- Concurrent activities (e.g. washing up while cooking) are not represented in Aruba's labels.
- Respirate has 6 instances in total; per-class numbers for it are unreliable.
- History features feed the model's own earlier predictions back in; a wrong recognition can affect later ones.
- LastAct / DeepCASAS numbers are taken from the LastAct paper, not reproduced.
