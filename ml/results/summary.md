# HAR results

Mean ± std over folds (cv) or single hold-out (temporal). Values in %.
Macro-F1 is the headline metric: it weights every activity equally, so it
is not inflated by the majority classes (Relax, Meal_Preparation, ...).


## aruba - cv (6476 test segments, 11 classes)

| Approach | Accuracy | Macro-F1 | Weighted-F1 | Macro-P | Macro-R | Time (s) |
|---|---|---|---|---|---|---|
| 1 - Features + Random Forest + pre-segment context | 98.63 ± 0.17 | **86.09 ± 4.31** | 98.16 ± 0.17 | 90.09 ± 5.88 | 85.40 ± 4.58 | 39 |
| 1 - Features + Gradient Boosting | 96.26 ± 0.25 | **84.52 ± 4.24** | 95.92 ± 0.26 | 86.96 ± 4.25 | 83.95 ± 4.27 | 19 |
| 1 - Features + Random Forest | 96.36 ± 0.24 | **83.15 ± 4.14** | 95.88 ± 0.26 | 86.99 ± 5.97 | 82.57 ± 4.28 | 23 |
| 2 - BiLSTM | 95.41 ± 0.47 | **82.25 ± 3.29** | 95.24 ± 0.23 | 82.31 ± 3.18 | 83.63 ± 3.92 | 1454 |

## milan - cv (2352 test segments, 15 classes)

| Approach | Accuracy | Macro-F1 | Weighted-F1 | Macro-P | Macro-R | Time (s) |
|---|---|---|---|---|---|---|
| 1 - Features + Random Forest + pre-segment context | 96.34 ± 0.55 | **87.86 ± 2.11** | 95.83 ± 0.60 | 93.16 ± 3.81 | 85.61 ± 1.98 | 22 |
