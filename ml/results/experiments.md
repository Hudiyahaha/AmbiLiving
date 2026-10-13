# Tuning and repeated-seed runs

Mean ± std over seeds (n = number of seeds). Values in %. For cv runs each
seed's score is itself the mean over folds. Settings not shown in the
name are the defaults: lr 1e-3, patience 6, batch size 64.


## aruba - temporal

| Run | n | Macro-F1 | Accuracy | Weighted-F1 | Time per run (s) |
|---|---|---|---|---|---|
| bilstm+ctx | 3 | **87.38 ± 4.46** | 98.60 ± 0.28 | 98.83 ± 0.21 | 193 |
| cnn+ctx | 3 | **83.96 ± 7.52** | 98.67 ± 0.72 | 98.69 ± 0.51 | 62 |
| cnn | 3 | **80.21 ± 3.41** | 96.03 ± 0.14 | 96.05 ± 0.14 | 57 |
| transformer+ctx | 3 | **80.13 ± 1.03** | 98.67 ± 0.54 | 98.59 ± 0.48 | 142 |
| bilstm | 3 | **79.85 ± 4.66** | 96.43 ± 0.17 | 96.51 ± 0.09 | 170 |
| transformer | 3 | **75.53 ± 2.69** | 95.57 ± 0.94 | 95.82 ± 0.71 | 286 |

## milan - temporal

| Run | n | Macro-F1 | Accuracy | Weighted-F1 | Time per run (s) |
|---|---|---|---|---|---|
| bilstm | 3 | **88.57 ± 0.74** | 96.09 ± 0.47 | 96.32 ± 0.37 | 72 |
| bilstm+ctx | 3 | **87.58 ± 1.60** | 96.21 ± 0.38 | 96.39 ± 0.52 | 57 |
| transformer+ctx | 3 | **87.21 ± 0.24** | 95.78 ± 0.24 | 96.04 ± 0.38 | 73 |
| transformer | 3 | **84.56 ± 1.42** | 94.39 ± 0.81 | 94.71 ± 0.60 | 66 |
| cnn+ctx | 3 | **83.85 ± 2.07** | 93.16 ± 1.27 | 93.15 ± 1.05 | 22 |
| cnn | 3 | **77.75 ± 2.15** | 91.07 ± 0.43 | 90.87 ± 0.72 | 14 |
