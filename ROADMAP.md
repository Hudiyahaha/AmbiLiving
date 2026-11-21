# AmbiLiving — Roadmap to completion

This is the **single ordered to-do list** for the project. Work top to bottom: each phase
needs what the phase before it produces. Tick a box when its *Done when* is true, and add a
line to [paper/experiment-log.md](paper/experiment-log.md) for anything that produced a number.

The **Paper** column says which part of the research paper a step feeds (see
[paper/outline.md](paper/outline.md)); claim IDs (C1, C2, …) are in [paper/claims.md](paper/claims.md).

Where we are (18 Nov 2026): Phases 1–2 of the original plan are done — activity recognition is
finished for both the known-boundary and the live sliding-window setting. Everything from
anomaly detection onward is still open. Details: [PROJECT_STATUS.md](PROJECT_STATUS.md).

```
Phase 0  Housekeeping            ← start here (≈ 1 day)
Phase 1  Freeze activity recognition (HAR)
Phase 2  Anomaly detection        ← main open research work
Phase 3  Alerts
Phase 4  Integration (backend + dashboard)
Phase 5  System evaluation & deployment
Phase 6  Write-up (paper, report, poster, demo)
```

Write the paper **while** you go: each phase ends with a "draft the section" step, so the
paper is mostly written by the time Phase 5 finishes.

---

## Phase 0 — Housekeeping

| # | Step | Done when | Paper |
|---|---|---|---|
| ☐ 0.1 | Commit `poster/` | It is on `main` | — |
| ☐ 0.2 | Refresh the result tables and "Known limitations" in [ml/README.md](ml/README.md) | Every number matches `ml/results/summary.md` / `windows.md` (they predate the 13 Oct macro-F1 fix; e.g. Milan temporal GB + ctx reads 84.65 there vs 90.69 in `summary.md`) | Reproducibility |
| ☐ 0.3 | Replace the create-next-app [README.md](README.md) with a real project README (what, how to run both tracks, where results live) | A new teammate can run the app and one experiment from it alone | — |
| ☐ 0.4 | Delete the unused [PagePlaceholder.tsx](src/components/ui/PagePlaceholder.tsx) | `npx tsc --noEmit` still clean | — |
| ☐ 0.5 | Tag the current results: `git tag har-results-v1` | Tag pushed; the paper's HAR numbers cite this tag | Reproducibility |

## Phase 1 — Freeze activity recognition

The models are chosen; this phase makes them usable by later phases and gets the HAR part of
the paper written while the details are fresh.

| # | Step | Done when | Paper |
|---|---|---|---|
| ☐ 1.1 | **Save trained models to disk.** No script persists a model today (only the parsed data is cached). Add a `--save` option for the final segment model (GB + ctx + history) and the final window model (BiLSTM), trained on the train days only | Model files load in a fresh process and reproduce the stored test predictions | Method §Implementation |
| ☐ 1.2 | **Per-class table for the window setting** for the final BiLSTM, both homes, mean over 3 seeds | Table in `ml/results/windows.md`; rare classes (Wash_Dishes, Respirate, meds) reported explicitly | C6, Results §HAR-live |
| ☐ 1.3 | **Confidence analysis.** `metrics.json` already stores mean confidence on right vs wrong answers and how many mistakes a 60 % / 80 % "unknown" cutoff catches. Summarise it for the final models | One small table: cutoff → % predictions kept, accuracy on kept | Feeds Phase 3 (alerts should not fire on low-confidence activities) |
| ☐ 1.4 | *(Optional)* Transformer + context under cv on both homes — the only missing cell in the cv tables (~4 h CPU per home) | Row present in `summary.md`, or the gap stated in the paper | C1 |
| ☐ 1.5 | **Draft paper sections: Dataset, HAR method, HAR results (both settings)** | Drafts in `paper/draft/` cite only numbers listed in `paper/claims.md` | §3, §4.1–4.3, §5.1–5.2 |

## Phase 2 — Routine-deviation detection (main open research work)

CASAS has **no anomaly labels**, so the evaluation design (2.2) is the hard, publishable part.
Decide it before building models, and record the decision in [paper/decisions.md](paper/decisions.md).

| # | Step | Done when | Paper |
|---|---|---|---|
| ☑ 2.1 | **Define what an anomaly is**, in caregiver terms. Candidate types: *missed* activity (no meal / no meds by a usual time), *unusual duration* (very long bathroom visit, very short sleep), *unusual time* (activity at an atypical hour, night wandering), *unusual frequency* (many Bed_to_Toilet trips in one night), *prolonged inactivity* | A short taxonomy (5–6 types), each with a one-line caregiver meaning and the activities it applies to in each home | §4.4 Problem definition |
| ☑ 2.2 | **Fix the evaluation protocol.** First check exactly how Fahad & Tahir (2020) and Cejudo et al. (2025) evaluate on CASAS. Likely design: train the routine model on train days; on held-out test days **inject synthetic anomalies** of each type (delete a meal, stretch a bathroom visit, move an activity to 3 am, …) with known positions; measure precision / recall / F1 per type and false alarms per day on un-injected days | Protocol written in `paper/decisions.md` *before* any anomaly result is seen | §4.5, D-entries |
| ☑ 2.3 | **Routine model — simple baseline first.** Per resident and per activity: time-of-day, duration and daily-count distributions from train days; flag test values outside a percentile band | `ml/har/anomaly.py` (or similar) + results archived like the HAR runs (`ml/results/<home>/anomaly/<model>/`) | Baseline row |
| ☑ 2.4 | **Learned routine model.** One model from the shortlisted literature, e.g. an autoencoder over daily activity vectors (Fahad & Tahir) or an RNN next-activity model (Cejudo et al.) | Compared with 2.3 on the same protocol | C7 |
| ☑ 2.5 | **Error-propagation experiment — the key system result.** Run anomaly detection on three activity streams: (a) annotated ground truth, (b) segment-model predictions, (c) live window-model predictions. Report how much anomaly F1 and false alarms degrade from (a) to (c) | One table: anomaly type × stream. This directly tests the CCP claim that "HAR errors propagate to anomaly detection" | C8, §5.3 — likely the paper's main new finding |
| ☑ 2.6 | **Explanation layer.** Turn each detection into the dashboard's `AnomalyRecord`: `observed`, `expected`, `reason`, `severity` (no raw scores, per spec §11) | Function output validates against [src/types/home.ts](src/types/home.ts) `AnomalyRecord` | §4.6 |
| ☑ 2.7 | **Draft paper sections: anomaly method and results** | Drafts in `paper/draft/` | §4.4–4.6, §5.3 |

## Phase 3 — Alerts

| # | Step | Done when | Paper |
|---|---|---|---|
| ☑ 3.1 | **Alert rules:** which anomalies alert, severity mapping, a confidence floor (from 1.3), de-duplication / cool-down so one event does not alert repeatedly | Rules written in `paper/decisions.md` and implemented in one module | §4.6 |
| ☑ 3.2 | **Measure false-alert rate** (alerts per normal day) and **detection delay** (time from injected anomaly to alert) on the Phase 2 protocol | Table archived with the anomaly results | Evaluation plan: "Alerts: false-alert rate + response time"; §5.4 |

## Phase 4 — Integration

| # | Step | Done when | Paper |
|---|---|---|---|
| ☐ 4.1 | **Decide the backend**: FastAPI (Python, loads the models from 1.1 directly) vs Next.js route handlers calling a Python process. FastAPI is the simpler fit since all models are Python | Decision + reason in `paper/decisions.md` | §4.7 System |
| ☑ 4.2 | *(Done as a precomputed causal replay, D17: `har.replay` + `/live`; a streaming endpoint is still open with 4.1)* **Replay service:** stream a recorded CASAS day event by event (adjustable speed) as if it were live | Endpoint emits events in timestamp order | — |
| ◐ 4.3 | *(Offline in `har.replay`: BiLSTM every 10th event + routine model + routing, re-run every 2 min of the day)* **Live inference:** window model classifies the last 100 events at each event; anomaly + alert modules run on its output | Endpoints for current activity, activity history, anomalies | §4.7 |
| ☐ 4.4 | **Connect the dashboard:** replace the generated JSON ([realData.ts](src/data/homes/realData.ts)) and the sample anomalies (`arubaMock.ts`, `milanMock.ts`) with API calls | Monitoring, Activities, Anomalies and Dashboard pages show live API data | — |
| ☐ 4.5 | **Researcher / Evaluation view** (spec §13): HAR and anomaly metrics, per-class tables, confusion matrices, kept apart from the caregiver screens | Page reads the archived `metrics.json` files | Demo |
| ☐ 4.6 | *(Optional)* Kasteren as a placeholder third home (spec §12) | Listed with `status: "placeholder"` | — |

## Phase 5 — System evaluation & deployment

| # | Step | Done when | Paper |
|---|---|---|---|
| ☐ 5.1 | **End-to-end tests:** sensor stream → HAR → anomaly → alert → dashboard, on at least one injected-anomaly day per home | Test script passes; the injected anomaly shows up as an alert on the dashboard | §5.4 |
| ☐ 5.2 | **Response time & reliability:** per-event inference latency, event-to-alert latency, behaviour over a long replay (memory, crashes) | Numbers archived; median and 95th percentile reported | Evaluation plan "System"; §5.4 |
| ☐ 5.3 | **Fairness across homes and activities** (DEI commitment): put Aruba and Milan side by side for every headline number; list activities with low per-class F1 | Section of the report; no Aruba-only claims anywhere | §6 Discussion, Ethics |
| ☐ 5.4 | **Deploy outside the dev machine** (e.g. a cloud VM or a teammate's laptop from a clean checkout) | Someone outside the team opens the dashboard and sees a replayed day | Success criterion |

## Phase 6 — Write-up

| # | Step | Done when | Paper |
|---|---|---|---|
| ☐ 6.1 | **Pick a target venue** (conference or journal) — fixes page limit and format | Venue + deadline in `paper/outline.md` | — |
| ☐ 6.2 | **Assemble the paper** from `paper/draft/`; every number traced to `paper/claims.md` | Full draft; each claim marked *supported* | All |
| ☐ 6.3 | **Related work** from [paper/references.md](paper/references.md); verify every citation's details from the original paper | No "to verify" left in `references.md` | §2 |
| ☐ 6.4 | **FYP final report** (reuses the paper's sections plus requirements, design, ethics/legal, DEI) | Report submitted | — |
| ☐ 6.5 | **Update the poster** with the headline results and the error-propagation finding | Poster on `main` | — |
| ☐ 6.6 | **Demo script** for the final defense: one replayed day, an injected anomaly, the alert, the researcher view | Rehearsed once end to end | — |
