# 7 Ethics and limitations

**Privacy and consent.** Ambient sensors record no images or audio, but a stream of motion
and door events still reveals intimate routines — when someone sleeps, uses the bathroom or
leaves home. A deployed system needs the resident's informed consent, should keep raw events
only as long as needed to learn and monitor the routine (data minimisation), and should store
them pseudonymised and secured. We use only the public CASAS datasets, under their research-use
terms.

**Human oversight.** Alerts are prompts for a caregiver to check in, not decisions. The
dashboard shows *what was observed* and *what is usual for this resident* in plain language so
that the caregiver, not the model, judges whether something is wrong. No high-stakes action
(e.g. calling emergency services) should be triggered automatically from these outputs.

**Fairness across residents and activities.** Performance is not uniform. Recognition of rare
and short activities (washing up, medication) is poor in the live setting, and
routine-deviation detection inherits these weaknesses: a missed medication cannot be detected if medication is
never recognised. We report every result for both homes and per activity type rather than as a
single average, so that unequal performance is visible.

**Limitations.**

- *Two homes, one resident each*, recorded in 2009–2011; Milan also has a pet, whose movement
  triggers motion sensors. Results may not transfer to other homes, layouts or residents.
- *No real deviation labels.* Routine-deviation results rely on synthetic injections. They are cleaner and
  more clearly defined than real deviations, so detection rates are likely optimistic; false
  alerts on clean days may include real but unlabelled deviations.
- *Short observation periods.* Routine models are learned from 44 (Aruba) and 13 (Milan)
  observation days. Milan's 13 monitoring days are the Christmas holiday, a genuine shift in
  routine.
- *Concurrent activities* (e.g. washing up while cooking) are not represented in Aruba's labels,
  so they can be neither learned nor evaluated.
- *Label drift* in the annotations makes per-class scores on chronological splits noisy.
- *Feedback loop.* Routine-history features feed the model's own earlier predictions back in;
  one wrong recognition can influence later ones.
- *Baselines.* LastAct and DeepCASAS numbers are taken from the LastAct paper, not reproduced.
