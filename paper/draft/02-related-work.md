# 2 Related work

> All citation details below must be verified against the original papers before submission
> (see `paper/references.md`). Numbers quoted here are as reported by the cited authors.

**Activity recognition from ambient sensors.** The CASAS testbeds [casas] are the standard
benchmark for ambient-sensor HAR. Most work uses *explicit segmentation*: each annotated
activity instance is classified from the events between its begin and end labels. Fahad and
Tahir [fahad2020] combine activity recognition and anomaly detection on CASAS homes and report
96.19 % accuracy on Aruba and 96.33 % on Milan. Zhao et al. [zhao2026] address noisy, sparse
and imbalanced binary-sensor data across six CASAS datasets with a stacking neural network and
GAN-based augmentation, reporting about 90 % accuracy on Aruba and 80 % on Milan. Because
accuracy is dominated by frequent activities, we report macro-F1 as the headline metric
and show that it separates models that look identical by accuracy.

**Recognition without boundaries.** A deployed system sees an unsegmented event stream.
Sliding-window approaches classify the last *N* events at each new event. DeepCASAS [deepcasas]
and LastAct [lastact2026] work in this setting; LastAct defines a raw-stream protocol
(chronological 60/20/20 day split, a test window at every event, label = most recent annotated
activity) and reports 44.6 ± 1.9 macro-F1 on Aruba and 40.1 ± 0.5 on Milan. We adopt that
protocol unchanged so our live numbers are directly comparable.

**Routines, deviations and anomalies.** Cejudo et al. [cejudo2025] propose a two-step
system that learns older adults' daily routines with recurrent models (RNN, BiRNN, ConvLSTM,
attention-RNN) and detects deviations from them. Fahad and Tahir [fahad2020] use an
autoencoder to flag anomalous activities (unusual duration or number of sub-events) and days
(unusual number of daily activities). Much of this literature uses "anomaly" and "deviation"
interchangeably; we separate them. A generic anomaly detector scores how rare an observation
is; a routine model states what is usual *for this person* — including what should have
happened and has not — and reports the difference. We keep an autoencoder as a generic
baseline to show what this distinction buys. Both cited works evaluate on annotated
activities. Public CASAS data contain no labelled deviations, so evaluation relies on injected
or simulated ones; we inject them into the raw sensor events, which allows the effect of
recognition errors on deviation detection to be measured — a link that, to our knowledge, is
rarely quantified.

**Products.** Commercial ambient-monitoring systems such as Zemplee Sense and OdeCare provide
presence and routine monitoring with caregiver dashboards, but expose sensor-level information
rather than recognised activities.

<!-- TODO (ROADMAP 6.3): add a HAR survey, online-segmentation work beyond LastAct/DeepCASAS,
     and work on evaluating routine/anomaly detection without labels. Check how [cejudo2025]
     and [fahad2020] construct their test sets and compare with D13. -->
