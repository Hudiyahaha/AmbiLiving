# 8 Conclusion

We built and evaluated an end-to-end ambient-sensor pipeline for older adults living alone,
from raw motion and door events to caregiver-readable routine deviations, on two CASAS homes.

Three lessons stand out. First, for activity recognition the *representation* matters more than
the model: a few past-only context features fix the confusions that motivated the work, and a
fast Gradient Boosting model is as good as deep sequence models when activity boundaries are
known. Second, what caregivers need is **routine deviation**, not anomaly detection: a model of
the resident's own routine — including what should have happened and has not — finds most
injected deviations and explains each one in the resident's own terms, while a generic outlier
detector finds few and cannot see absence at all. Third, the weak link is live recognition:
without activity boundaries, recognition errors corrupt the routine the system learns, so
deviations that would be obvious with correct activities disappear.

Next steps follow directly: improve live recognition of the few activities that alerts depend
on (leaving home, cooking, medication), cross-check absence-based alerts against the raw
sensor stream, let caregivers mark expected changes such as holidays, and validate the
pipeline on more homes and on real, rather than injected, routine changes.
