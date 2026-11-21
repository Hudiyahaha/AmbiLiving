# References

What we cite and why. Details below come from the defense slides and the repository; **every
entry marked "verify" must be checked against the original paper** (authors, title, venue,
year, DOI, and any number we quote) before it goes into the paper.

| Key | Reference (as we currently have it) | What we use it for | Numbers we quote | Status |
|---|---|---|---|---|
| casas | CASAS smart-home datasets, Center for Advanced Studies in Adaptive Systems, Washington State University (Aruba, Milan). Cite the dataset paper the CASAS site asks for (likely Cook et al., "CASAS: A Smart Home in a Box", *IEEE Computer*, 2013) | Data | Aruba 6,477 / Milan 2,353 instances (slides); 6,476 / 2,352 segments after parsing | verify citation + licence terms |
| zhao2026 | Zhao et al., 2026, "Deep Learning-Based Human Activity Recognition Using Binary Ambient Sensors" | Related work (HAR); stacking NN + GAN/ASGAN augmentation for imbalance; 6 CASAS datasets | ~90 % Aruba, ~80 % Milan accuracy | verify |
| cejudo2025 | A. Cejudo, A. Beristain, A. Almeida, K. Rebescher, C. Martín, I. Macía, "Smart home-assisted anomaly detection system for older adults: a deep learning approach with a comprehensive set of daily activities", *Medical & Biological Engineering & Computing* 63, 1821–1835 (2025). doi:10.1007/s11517-025-03308-y | Related work (routine/anomaly); two-step anomaly detection; RNN, BiRNN, ConvLSTM, Attention-RNN | 4.38 % MSE (slides) | **bibliographic details verified 18 Nov**; datasets (slides say Aruba, Cairo, Milan), the MSE figure and the anomaly evaluation protocol still to check in the full text |
| fahad2020 | L. G. Fahad, S. F. Tahir, "Activity recognition and anomaly detection in smart homes", *Neurocomputing* 423, 362–372 (2021; online 12 Nov 2020). doi:10.1016/j.neucom.2020.10.102 | Related work (HAR + anomaly); PNN for recognition, H2O autoencoder for anomalies. Per the abstract: anomalous **days** are identified from the number of daily activities; anomalous **activities** from unusual duration or number of sub-events — close to our `prolonged` / frequency types | Accuracy 96.19 % Aruba, 96.33 % Milan, 90.06 % Cairo, 94.90 % Tulum (slides) | **bibliographic details verified 18 Nov**; accuracy figures and how anomalies were evaluated still to check in the full text. First author appears to be the project supervisor — confirm |
| lastact2026 | Z. Liu, R. Fang, J. Lu, F. Dou, "LastAct: Trajectory-guided latest-activity localization for real-time smart-home activity recognition", arXiv:2606.00260 (v1 29 May 2026; later versions exist) | Live sliding-window protocol (D6) and baseline numbers | Aruba 44.6 ± 1.9, Milan 40.1 ± 0.5 macro-F1 | **title/authors verified 18 Nov**; Aruba 44.6 / Milan 40.1 match a leaderboard listing; confirm ± values and protocol details in the latest arXiv version and cite that version |
| deepcasas | DeepCASAS — original paper to be found; numbers as reported by LastAct | Live-setting baseline | Aruba 38.6, Milan 36.7 macro-F1 (via LastAct) | find original + verify |
| alaghbari2022 | Alaghbari et al., 2022 — mentioned in `ml/README.md` as a CV-protocol paper | Protocol comparability | — | find + verify |
| zemplee | Zemplee Sense (commercial product) | Motivation: existing products report presence, not activities | — | cite product page with access date |
| odecare | OdeCare (commercial product) | Same as above | — | cite product page with access date |

## To find

- [ ] A survey of ambient-sensor HAR (for the intro/related-work framing).
- [ ] Work on online / streaming segmentation for CASAS beyond LastAct and DeepCASAS.
- [ ] Work on evaluating anomaly detection without ground-truth labels (synthetic injection).
- [ ] Ethics / privacy of in-home monitoring of older adults (for §7).
