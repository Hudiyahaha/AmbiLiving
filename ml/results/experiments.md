# Tuning and repeated-seed runs

Mean ± std over seeds (n = number of seeds). Values in %. For cv runs each
seed's score is itself the mean over folds. Settings not shown in the
name are the defaults: lr 1e-3, patience 6, batch size 64.


## aruba - temporal

| Run | n | Macro-F1 | Accuracy | Weighted-F1 | Time per run (s) |
|---|---|---|---|---|---|
| cnn+ctx | 3 | **83.96 ± 7.52** | 98.67 ± 0.72 | 98.69 ± 0.51 | 62 |
| cnn | 3 | **80.21 ± 3.41** | 96.03 ± 0.14 | 96.05 ± 0.14 | 57 |
| bilstm | 3 | **79.85 ± 4.66** | 96.43 ± 0.17 | 96.51 ± 0.09 | 170 |

## milan - temporal

| Run | n | Macro-F1 | Accuracy | Weighted-F1 | Time per run (s) |
|---|---|---|---|---|---|
| bilstm | 3 | **88.57 ± 0.74** | 96.09 ± 0.47 | 96.32 ± 0.37 | 72 |
| cnn+ctx | 3 | **83.85 ± 2.07** | 93.16 ± 1.27 | 93.15 ± 1.05 | 22 |
| cnn | 3 | **77.75 ± 2.15** | 91.07 ± 0.43 | 90.87 ± 0.72 | 14 |
