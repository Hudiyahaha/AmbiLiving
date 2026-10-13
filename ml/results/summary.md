# HAR results

Mean ± std over folds (cv) or single hold-out (temporal). Values in %.
Macro-F1 is the headline metric: it weights every activity equally, so it
is not inflated by the majority classes (Relax, Meal_Preparation, ...).


## aruba - cv (6476 test segments, 11 classes)

| Approach | Accuracy | Macro-F1 | Weighted-F1 | Macro-P | Macro-R | Time (s) |
|---|---|---|---|---|---|---|
| 1 - Features + Gradient Boosting + pre-segment context + activity history | 98.98 ± 0.08 | **92.92 ± 3.74** | 98.88 ± 0.12 | 94.41 ± 3.57 | 92.04 ± 3.94 | 177 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history + full class balancing | 98.87 ± 0.24 | **92.24 ± 4.11** | 98.87 ± 0.22 | 92.35 ± 4.44 | 93.17 ± 3.87 | 169 |
| 1 - Features + Gradient Boosting + pre-segment context | 98.52 ± 0.20 | **87.56 ± 5.19** | 98.18 ± 0.28 | 89.62 ± 5.79 | 87.04 ± 4.93 | 14 |
| 1 - Features + Random Forest + pre-segment context + activity history | 98.78 ± 0.09 | **87.13 ± 3.83** | 98.38 ± 0.11 | 92.97 ± 5.59 | 86.22 ± 4.10 | 188 |
| 3 - 1D-CNN + pre-segment context | 97.78 ± 0.42 | **86.15 ± 4.53** | 97.52 ± 0.24 | 86.53 ± 4.17 | 86.19 ± 4.76 | 416 |
| 1 - Features + Random Forest + pre-segment context | 98.63 ± 0.17 | **86.09 ± 4.31** | 98.16 ± 0.17 | 90.09 ± 5.88 | 85.40 ± 4.58 | 14 |
| 2 - BiLSTM + pre-segment context | 97.92 ± 0.37 | **85.51 ± 4.63** | 97.63 ± 0.43 | 87.17 ± 5.13 | 85.91 ± 5.32 | 1639 |
| 1 - Features + Gradient Boosting | 96.29 ± 0.32 | **84.52 ± 4.62** | 95.95 ± 0.33 | 86.72 ± 4.62 | 84.01 ± 4.53 | 193 |
| 3 - Transformer | 95.69 ± 0.65 | **83.25 ± 3.93** | 95.55 ± 0.40 | 83.68 ± 4.88 | 84.20 ± 4.16 | 14228 |
| 1 - Features + Random Forest | 96.42 ± 0.21 | **83.23 ± 4.05** | 95.94 ± 0.24 | 87.07 ± 5.97 | 82.65 ± 4.18 | 34 |
| 3 - 1D-CNN | 95.74 ± 0.28 | **82.80 ± 4.21** | 95.33 ± 0.30 | 83.18 ± 3.99 | 83.09 ± 4.68 | 665 |
| 2 - BiLSTM | 95.41 ± 0.47 | **82.25 ± 3.29** | 95.24 ± 0.23 | 82.31 ± 3.18 | 83.63 ± 3.92 | 1454 |

## aruba - temporal (1925 test segments, 11 classes)

| Approach | Accuracy | Macro-F1 | Weighted-F1 | Macro-P | Macro-R | Time (s) |
|---|---|---|---|---|---|---|
<<<<<<< HEAD
| 2 - BiLSTM + pre-segment context | 98.29 ± 0.00 | **90.73 ± 0.00** | 98.68 ± 0.00 | 88.87 ± 0.00 | 95.74 ± 0.00 | 211 |
| 3 - 1D-CNN + pre-segment context | 97.45 ± 0.00 | **90.52 ± 0.00** | 98.09 ± 0.00 | 89.61 ± 0.00 | 95.35 ± 0.00 | 50 |
| 2 - BiLSTM | 96.10 ± 0.00 | **88.52 ± 0.00** | 96.05 ± 0.00 | 89.26 ± 0.00 | 88.78 ± 0.00 | 146 |
| 3 - 1D-CNN | 95.74 ± 0.00 | **85.58 ± 0.00** | 96.06 ± 0.00 | 85.33 ± 0.00 | 86.16 ± 0.00 | 46 |
| 3 - Transformer + pre-segment context | 98.96 ± 0.00 | **84.16 ± 0.00** | 98.86 ± 0.00 | 89.22 ± 0.00 | 82.45 ± 0.00 | 128 |
| 3 - Transformer | 95.90 ± 0.00 | **82.53 ± 0.00** | 95.74 ± 0.00 | 81.39 ± 0.00 | 85.08 ± 0.00 | 132 |
=======
| 1 - Features + Gradient Boosting + pre-segment context | 99.17 | **92.75** | 99.17 | 92.76 | 92.75 | 7 |
| 1 - Features + Random Forest + pre-segment context + activity history | 99.53 | **92.34** | 99.46 | 94.80 | 91.55 | 13 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history | 98.91 | **91.47** | 99.14 | 91.01 | 92.96 | 35 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history + full class balancing | 98.75 | **91.24** | 99.05 | 90.83 | 92.90 | 34 |
| 1 - Features + Random Forest + pre-segment context | 99.38 | **89.63** | 99.22 | 89.58 | 89.70 | 3 |
| 1 - Features + Random Forest | 97.25 | **86.76** | 97.09 | 86.72 | 86.83 | 2 |
| 1 - Features + Gradient Boosting | 97.09 | **86.68** | 97.01 | 86.66 | 86.71 | 7 |
>>>>>>> 25c39847dead9fe1d908935a5e67c04c70c31791

## milan - cv (2352 test segments, 15 classes)

| Approach | Accuracy | Macro-F1 | Weighted-F1 | Macro-P | Macro-R | Time (s) |
|---|---|---|---|---|---|---|
| 1 - Features + Gradient Boosting + pre-segment context + activity history | 97.45 ± 0.82 | **92.52 ± 1.73** | 97.27 ± 0.83 | 95.59 ± 2.35 | 91.63 ± 1.84 | 259 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history + full class balancing | 97.07 ± 0.86 | **91.76 ± 2.52** | 96.93 ± 0.88 | 93.64 ± 3.32 | 91.31 ± 2.45 | 226 |
| 1 - Features + Gradient Boosting | 96.43 ± 0.79 | **91.01 ± 2.03** | 96.28 ± 0.72 | 93.81 ± 2.80 | 90.45 ± 1.93 | 28 |
| 1 - Features + Gradient Boosting + pre-segment context | 97.02 ± 0.47 | **90.97 ± 1.42** | 96.84 ± 0.42 | 93.91 ± 2.72 | 90.17 ± 1.66 | 20 |
| 2 - BiLSTM + pre-segment context | 96.47 ± 0.61 | **90.61 ± 1.77** | 96.36 ± 0.63 | 93.68 ± 2.57 | 90.16 ± 2.57 | 384 |
| 1 - Features + Random Forest + pre-segment context + activity history | 96.94 ± 0.55 | **89.73 ± 1.62** | 96.55 ± 0.57 | 96.57 ± 2.46 | 87.08 ± 1.81 | 54 |
| 3 - Transformer | 94.77 ± 1.55 | **89.18 ± 4.30** | 94.72 ± 1.75 | 89.63 ± 4.21 | 89.85 ± 4.39 | 930 |
| 2 - BiLSTM | 95.66 ± 1.10 | **89.01 ± 3.01** | 95.46 ± 1.14 | 89.58 ± 3.18 | 89.42 ± 2.94 | 621 |
| 1 - Features + Random Forest + pre-segment context | 96.34 ± 0.55 | **87.86 ± 2.11** | 95.83 ± 0.60 | 93.16 ± 3.81 | 85.61 ± 1.98 | 14 |
| 1 - Features + Random Forest | 96.13 ± 0.56 | **87.32 ± 1.74** | 95.60 ± 0.55 | 91.37 ± 3.02 | 85.39 ± 1.51 | 16 |
| 3 - 1D-CNN | 95.03 ± 0.56 | **86.56 ± 0.97** | 94.69 ± 0.52 | 87.50 ± 1.72 | 86.77 ± 1.90 | 332 |
| 3 - 1D-CNN + pre-segment context | 94.86 ± 0.99 | **86.41 ± 2.31** | 94.55 ± 0.91 | 87.54 ± 2.66 | 87.00 ± 1.89 | 203 |

## milan - temporal (862 test segments, 15 classes)

| Approach | Accuracy | Macro-F1 | Weighted-F1 | Macro-P | Macro-R | Time (s) |
|---|---|---|---|---|---|---|
<<<<<<< HEAD
| 2 - BiLSTM | 94.78 ± 0.00 | **93.55 ± 0.00** | 95.24 ± 0.00 | 95.95 ± 0.00 | 91.72 ± 0.00 | 53 |
| 2 - BiLSTM + pre-segment context | 96.06 ± 0.00 | **93.12 ± 0.00** | 96.42 ± 0.00 | 95.23 ± 0.00 | 91.35 ± 0.00 | 43 |
| 3 - Transformer | 95.24 ± 0.00 | **91.63 ± 0.00** | 95.46 ± 0.00 | 95.34 ± 0.00 | 90.37 ± 0.00 | 73 |
| 3 - Transformer + pre-segment context | 95.82 ± 0.00 | **90.08 ± 0.00** | 95.69 ± 0.00 | 95.96 ± 0.00 | 89.29 ± 0.00 | 55 |
| 3 - 1D-CNN + pre-segment context | 94.32 ± 0.00 | **90.02 ± 0.00** | 94.60 ± 0.00 | 92.29 ± 0.00 | 88.75 ± 0.00 | 16 |
| 3 - 1D-CNN | 91.65 ± 0.00 | **85.01 ± 0.00** | 91.62 ± 0.00 | 90.35 ± 0.00 | 84.76 ± 0.00 | 16 |
=======
| 1 - Features + Gradient Boosting + pre-segment context | 96.40 | **84.65** | 96.32 | 88.22 | 84.23 | 7 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history | 96.40 | **84.05** | 96.17 | 87.48 | 83.21 | 35 |
| 1 - Features + Random Forest | 94.90 | **83.52** | 94.48 | 91.21 | 80.34 | 2 |
| 1 - Features + Gradient Boosting | 95.59 | **83.43** | 95.64 | 87.45 | 83.53 | 7 |
| 1 - Features + Random Forest + pre-segment context | 95.13 | **82.99** | 94.58 | 91.35 | 80.05 | 2 |
| 1 - Features + Gradient Boosting + pre-segment context + activity history + full class balancing | 96.29 | **82.53** | 96.16 | 85.88 | 83.77 | 32 |
| 1 - Features + Random Forest + pre-segment context + activity history | 95.13 | **81.16** | 94.39 | 84.78 | 79.05 | 10 |
>>>>>>> 25c39847dead9fe1d908935a5e67c04c70c31791
