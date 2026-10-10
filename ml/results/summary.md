# HAR results

Mean ± std over folds (cv) or single hold-out (temporal). Values in %.
Macro-F1 is the headline metric: it weights every activity equally, so it
is not inflated by the majority classes (Relax, Meal_Preparation, ...).


## aruba - cv (6476 test segments, 11 classes)

| Approach | Accuracy | Macro-F1 | Weighted-F1 | Macro-P | Macro-R | Time (s) |
|---|---|---|---|---|---|---|
| 1 - Features + Gradient Boosting + pre-segment context + activity history | 98.98 ± 0.08 | **92.92 ± 3.74** | 98.88 ± 0.12 | 94.41 ± 3.57 | 92.04 ± 3.94 | 177 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history + full class balancing | 98.87 ± 0.24 | **92.24 ± 4.11** | 98.87 ± 0.22 | 92.35 ± 4.44 | 93.17 ± 3.87 | 169 |
| 1 - Features + Gradient Boosting + pre-segment context | 98.50 ± 0.17 | **87.18 ± 4.83** | 98.13 ± 0.22 | 89.12 ± 5.46 | 86.77 ± 4.65 | 103 |
| 1 - Features + Random Forest + pre-segment context + activity history | 98.78 ± 0.09 | **87.13 ± 3.83** | 98.38 ± 0.11 | 92.97 ± 5.59 | 86.22 ± 4.10 | 188 |
| 1 - Features + Random Forest + pre-segment context | 98.66 ± 0.16 | **86.14 ± 4.34** | 98.19 ± 0.16 | 90.12 ± 5.92 | 85.46 ± 4.61 | 36 |
| 1 - Features + Gradient Boosting | 96.29 ± 0.32 | **84.52 ± 4.62** | 95.95 ± 0.33 | 86.72 ± 4.62 | 84.01 ± 4.53 | 193 |
| 1 - Features + Random Forest | 96.42 ± 0.21 | **83.23 ± 4.05** | 95.94 ± 0.24 | 87.07 ± 5.97 | 82.65 ± 4.18 | 34 |
| 2 - BiLSTM | 95.41 ± 0.47 | **82.25 ± 3.29** | 95.24 ± 0.23 | 82.31 ± 3.18 | 83.63 ± 3.92 | 1454 |

## aruba - temporal (1925 test segments, 11 classes)

| Approach | Accuracy | Macro-F1 | Weighted-F1 | Macro-P | Macro-R | Time (s) |
|---|---|---|---|---|---|---|
| 1 - Features + Gradient Boosting + pre-segment context | 99.17 | **92.75** | 99.17 | 92.76 | 92.75 | 7 |
| 1 - Features + Random Forest + pre-segment context + activity history | 99.53 | **92.34** | 99.46 | 94.80 | 91.55 | 13 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history | 98.91 | **91.47** | 99.14 | 91.01 | 92.96 | 35 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history + full class balancing | 98.75 | **91.24** | 99.05 | 90.83 | 92.90 | 34 |
| 1 - Features + Random Forest + pre-segment context | 99.38 | **89.63** | 99.22 | 89.58 | 89.70 | 3 |
| 1 - Features + Random Forest | 97.25 | **86.76** | 97.09 | 86.72 | 86.83 | 2 |
| 1 - Features + Gradient Boosting | 97.09 | **86.68** | 97.01 | 86.66 | 86.71 | 7 |

## milan - cv (2352 test segments, 15 classes)

| Approach | Accuracy | Macro-F1 | Weighted-F1 | Macro-P | Macro-R | Time (s) |
|---|---|---|---|---|---|---|
| 1 - Features + Gradient Boosting + pre-segment context + activity history | 97.45 ± 0.82 | **92.52 ± 1.73** | 97.27 ± 0.83 | 95.59 ± 2.35 | 91.63 ± 1.84 | 259 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history + full class balancing | 97.07 ± 0.86 | **91.76 ± 2.52** | 96.93 ± 0.88 | 93.64 ± 3.32 | 91.31 ± 2.45 | 226 |
| 1 - Features + Gradient Boosting + pre-segment context | 97.07 ± 0.75 | **91.41 ± 1.44** | 96.91 ± 0.69 | 94.46 ± 2.28 | 90.50 ± 1.77 | 42 |
| 1 - Features + Gradient Boosting | 96.39 ± 0.91 | **91.09 ± 2.08** | 96.23 ± 0.85 | 94.09 ± 2.99 | 90.38 ± 2.07 | 42 |
| 1 - Features + Random Forest + pre-segment context + activity history | 96.94 ± 0.55 | **89.73 ± 1.62** | 96.55 ± 0.57 | 96.57 ± 2.46 | 87.08 ± 1.81 | 54 |
| 1 - Features + Random Forest + pre-segment context | 96.47 ± 0.64 | **87.97 ± 2.31** | 95.97 ± 0.70 | 93.06 ± 4.12 | 85.83 ± 2.02 | 10 |
| 1 - Features + Random Forest | 96.05 ± 0.74 | **86.71 ± 1.85** | 95.48 ± 0.76 | 89.95 ± 1.62 | 84.96 ± 1.79 | 10 |

## milan - temporal (862 test segments, 15 classes)

| Approach | Accuracy | Macro-F1 | Weighted-F1 | Macro-P | Macro-R | Time (s) |
|---|---|---|---|---|---|---|
| 1 - Features + Gradient Boosting + pre-segment context | 96.40 | **84.65** | 96.32 | 88.22 | 84.23 | 7 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history | 96.40 | **84.05** | 96.17 | 87.48 | 83.21 | 35 |
| 1 - Features + Random Forest | 94.90 | **83.52** | 94.48 | 91.21 | 80.34 | 2 |
| 1 - Features + Gradient Boosting | 95.59 | **83.43** | 95.64 | 87.45 | 83.53 | 7 |
| 1 - Features + Random Forest + pre-segment context | 95.13 | **82.99** | 94.58 | 91.35 | 80.05 | 2 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history + full class balancing | 96.29 | **82.53** | 96.16 | 85.88 | 83.77 | 32 |
| 1 - Features + Random Forest + pre-segment context + activity history | 95.13 | **81.16** | 94.39 | 84.78 | 79.05 | 10 |
