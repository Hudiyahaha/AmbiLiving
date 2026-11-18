# 6 Discussion

**Representation over architecture.** With known boundaries, adding three past-only context
features moved every Aruba model more than switching between any two architectures, and the
cheapest model (Gradient Boosting) was best or near best throughout (§5.1). For a deployed
system on modest hardware this matters more than a fraction of a macro-F1 point.

**Routine context only helps when the labels are stable.** Routine history resolved the
Wash_Dishes/Meal_Preparation confusion under cross-validation but not on the temporal split,
because Wash_Dishes is barely annotated in Aruba's final months (Figure F5). Milan drifts the
other way: its December annotations are four times denser than November's. Any chronological
evaluation on CASAS inherits these annotation-density shifts, and per-class scores on later
days should be read with them in mind.

**Routine deviation is not anomaly detection.** The generic autoencoder caught almost nothing
that the routine model caught (§5.3), even when allowed more false alerts. The reason is
structural, not a matter of tuning: an outlier detector scores what is present, so it cannot
see a meal that did not happen or a silence where movement was expected, and it has no notion
of order, of the shape of a day, or of a routine that changes slowly. A per-resident routine
model makes these explicit and phrases every alert as *observed versus usual for this
person*, which is also what a caregiver can act on.

**Recognition errors propagate in specific, explainable ways.** With annotated activities or
the segment recogniser, the routine model detects most injected deviations. With the live
window recogniser on Aruba, detection collapses. Two mechanisms explain most of it:

1. *Corrupted routine, not just corrupted days.* The routine is learned from the recogniser's
   own output. When the live model fails to recognise the resident leaving home, hours spent
   away are labelled as relaxing, and the learned "usual quiet spell while relaxing" grows from
   under an hour to about three. A real three-hour silence then looks normal. Recognition
   errors in the observation period silently widen what counts as normal.
2. *Activities the sensors still suggest.* Deleting every annotated cooking episode leaves
   unannotated kitchen movement in Aruba's stream, and a live recogniser reasonably calls it
   cooking, so the meal never looks missed. This is partly a limit of injecting deviations
   through annotations, and partly a real ambiguity: from motion sensors alone, being in the
   kitchen and cooking are hard to separate.

Absence- and timing-based deviations that depend only on sensor silence or on clearly
recognised activities survive better. This suggests a practical design rule: alerts that
depend on *rare or short* activities (medication, washing up, leaving home) need either
better recognition of those specific activities or a cross-check against the raw sensors
before they reach a caregiver.

**Milan versus Aruba.** The live pipeline holds up much better on Milan than on Aruba,
although the two live recognisers have similar macro-F1 on the monitoring days (§5.3). Milan's
monitoring-period annotations are dense, so the injected deviations remove most of the
relevant sensor activity, and its observation and monitoring periods are only two weeks apart.
Aruba's sparse annotations and the six-week gap between periods make both the injections and
the learned routine noisier. This is a hypothesis to test with more homes.

**False alerts are partly real changes.** Milan's monitoring days are the Christmas holiday;
many alerts on "clean" days — no going out by mid-afternoon, a different evening — are genuine
departures from the routine learned two weeks earlier. On Aruba, most clean-day drift alerts
compare May–June with March–April, which is plausibly seasonal. Counting these as false alerts
is conservative. A deployed system needs a way for caregivers to mark a change as expected
(a holiday, a visit), and to let the routine adapt.

**Alert budget.** At 0.1 alerts per normal day for each routine aspect, the routine model
raises about 1.3 alerts per day on Aruba with annotated or segment activities. That is too
many to send as notifications. The aspects differ in urgency — a long silence or a very long
bathroom visit warrants a notification; a different afternoon or a slow drift belongs in a
daily summary — so the next step is to route deviations by severity rather than lower every
threshold (ROADMAP 3.1).

<!-- Numbers referenced qualitatively here come from §5.3 / claims C7, C7b, C8, C8b. -->
