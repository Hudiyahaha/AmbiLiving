## 5.4 From deviations to caregiver alerts

Source: `ml/results/alerts.md` (`python -m har.alerts`, decision D15). Detection is unchanged
from §5.3; routing decides delivery. Possible emergencies — a long silence at home, a very long
bathroom or toilet visit, leaving home or cooking between midnight and 05:00, a missed
medication — are pushed as **notifications** (2-hour cool-down). Other missed activities,
prolonged activities, unusual times, frequency changes and drift go into one **evening summary**
of at most three items. Timeline and order deviations stay on the **dashboard**.

**Table T5 — routing at the operating point.**

| Home | Activity stream | Notifications per clean day | Summary items per clean day | Urgent deviations notified | Median notification delay | Non-urgent deviations surfaced |
|---|---|---|---|---|---|---|
| Aruba | Annotations | 0.07 | 1.34 | **94 %** | 63 min | 83 % |
| Aruba | Segment GB | 0.09 | 1.18 | 63 % | 68 min | 80 % |
| Aruba | Live BiLSTM | 0.20 | 0.68 | 7 % | 84 min | 5 % |
| Milan | Annotations | 0.15 | 1.54 | 73 % | 43 min | 86 % |
| Milan | Segment GB | 0.31 | 1.15 | **79 %** | 71 min | 83 % |
| Milan | Live BiLSTM | 0.23 | 1.69 | 51 % | 55 min | 38 % |

*Urgent* injected deviations are long inactivity, prolonged bathroom or toilet visits and
night-time leaving or cooking; *non-urgent* are missed meals, other prolonged activities and extra
night-time toilet trips. A non-urgent deviation counts as surfaced if it appears in a
notification or in the (capped) evening summary.

Routing turns about 1.3 detected deviations per normal day into **one push notification every
5–14 days** on Aruba and every 3–7 days on Milan <!-- C10 -->, while still notifying 94 % (Aruba)
and 73 % (Milan) of urgent injected deviations from annotated activities, and 63 % and 79 % from
the segment recogniser, with a median delay of about an hour <!-- C10 -->. Missed meals and extra
night toilet trips reach the caregiver through the summary in 98–100 % of cases with recognised
activities.

Routing also makes error propagation visible in a new way. On Aruba with the segment recogniser,
night-time cooking is still *detected* in 91 % of cases (§5.3) but *notified* in only 44 %:
when the moved cooking episode is recognised as another activity, the deviation is still
unusual, but it no longer reads as "cooking at 3 am", so it is routed to the summary instead of
a notification <!-- C10b -->. A routing rule is only as reliable as the activity label it is
conditioned on.
