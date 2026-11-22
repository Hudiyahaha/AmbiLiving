# Sliding-window results (raw event stream)

No activity boundaries are given. Each sample is the last 100 sensor events, and
the label is the activity of the most recent annotated event. The protocol follows
LastAct (Liu et al., 2026, arXiv:2606.00260), so the numbers can be compared with it:

- days split in time order: first 60% train, middle 20% validation, last 20% test
- training windows every 50 events (`tr10` = every 10)
- one test window per event
- macro-F1 over the activities present in the test days

All values are in %, as mean ± std over 3 seeds. Run them with `python -m har.run_windows`.

These numbers are not comparable with the segment results in `summary.md`. The
segment results get the begin and end of each activity for free.

## Final comparison (test window at every event)

| Model | Aruba macro-F1 | Aruba acc | Milan macro-F1 | Milan acc |
|---|---|---|---|---|
| **BiLSTM** (final model) | 41.9 ± 1.5 | 63.8 | **45.6 ± 0.6** | 58.8 |
| Gradient Boosting + routine history (`hgb+histpast+bal+tr10`) | **43.8 ± 0.4** | 69.8 | 37.9* | 54.9* |
| Gradient Boosting (`hgb+tr10`) | 39.1 ± 0.2 | 67.1 | 38.1 ± 1.0 | 54.4 |
| CNN (`cnn+te10`, test every 10th event) | 42.2 ± 0.9 | 66.6 | 43.7 ± 0.6 | 57.6 |
| Transformer (`transformer+te10`, test every 10th event) | 37.1 ± 2.4 | 62.9 | 45.1 ± 0.7 | 58.1 |
| LastAct (reported) | 44.6 ± 1.9 | | 40.1 ± 0.5 | |
| DeepCASAS (reported by LastAct) | 38.6 | | 36.7 | |

\* Single run. Validation chose no history for Milan, so it was not repeated.

## Does routine history help?

| Model | Aruba | Milan |
|---|---|---|
| Gradient Boosting, no history → with history | 39.1 → **43.8** | 38.0 → 37.9 (single runs) |
| BiLSTM, no history → with history (test every 10th event) | 42.1 → 41.1 | 45.4 → 38.0 |

History built from the model's own earlier predictions lifts the lightweight model on
Aruba to the level of LastAct. It does not help the BiLSTM, and on Milan it hurts. The
final model was chosen with a rule fixed before these runs: BiLSTM + history only if
history helped on both homes, otherwise plain BiLSTM.

## Other findings

- **Smoothing** predictions over the last k windows lowered macro-F1 for every k tried,
  because short activities get averaged away. Validation picked k = 1, i.e. no smoothing.
- **The "Other" label rule** (unannotated events labelled Other, the product setting)
  gives Aruba 51.3 / acc 81.2 and Milan 35.3 with Gradient Boosting. See `window100-other/`.
- Wash_Dishes, Respirate and the medicine activities stay near 0 F1 in the window setting.
- Milan's test days (25 Dec – 6 Jan) are a holiday period: validation macro-F1 was about
  46 and test about 38 for the same Gradient Boosting model.

## Per-class results and confidence (final BiLSTM)

Full tables: [`windows_detail.md`](windows_detail.md) (`python -m har.window_report`).

- The frequent activities are recognised far better than the rare ones: Aruba Relax 0.75 and
  Meal_Preparation 0.68 F1 vs Wash_Dishes 0.06, Leave_Home 0.27, Respirate 0.30; Milan Read
  0.77 and Sleep 0.76 vs Eve_Meds 0.02, Morning_Meds 0.04, Meditate 0.25.
- The model is under-confident: answers given at 40–50 % confidence are right 66–68 % of the
  time. A 0.4 "unknown" cutoff keeps 52–59 % of predictions at 74–78 % accuracy; the 0.6
  cutoff stored in `metrics.json` keeps only about 15 %.

Per-seed outputs are in `<home>/window100-last/experiments/<model>+s<seed>/`.
