# Abstract

Ambient sensors let older adults be monitored at home without cameras or wearables, but
existing systems report which sensor fired, not what the resident did or whether today differs
from their routine. We study the full pipeline — sensor events, recognised activity, routine
deviation, caregiver alert — on two CASAS smart homes. For activity recognition, five models
under cross-validation, a temporal split and a live sliding window show that the input
representation matters more than the architecture: three past-only context features and a
routine history built from the model's own predictions raise macro-F1 to 92.9 (Aruba) and 92.5
(Milan) with known activity boundaries, resolving the Enter/Leave_Home and
Wash_Dishes/Meal_Preparation confusions. Without boundaries, a BiLSTM reaches 45.6 macro-F1 on
Milan, above the published LastAct result under the same protocol. We then separate **routine
deviation** from generic anomaly detection: a per-resident routine model learns which activities
happen daily and by when, how long, at what time, how often, in what order, what each part of the
day looks like, how long the home is usually quiet, and how this drifts over a week, and reports
every deviation as observed versus usual for this person. Injecting five kinds of deviation into
the raw sensor stream, the routine model detects 87–92 % of them with recognised activities, while
a generic autoencoder detects 4–19 % and none of the missed meals or periods of inactivity. With
the live recogniser, detection drops to 16 % on Aruba and 63 % on Milan; we trace the loss to
recognition errors that corrupt the *learned routine itself*, not only the monitored day.
Routing deviations by urgency reduces push notifications to one every one to two weeks on Aruba
while still notifying 94 % of injected possible emergencies from annotated activities.

<!-- Numbers: C4e, C5, C7, C8, C10. -->
