# paper/ — research-paper tracking

This folder holds everything needed to write the AmbiLiving research paper, kept up to date
**as the work happens** so that writing the paper becomes assembly rather than archaeology.

| File | What it holds | Update it when |
|---|---|---|
| [outline.md](outline.md) | Research questions, contributions, section-by-section plan, figure/table list, status of each section | The story of the paper changes, or a section gets drafted |
| [claims.md](claims.md) | Every claim the paper will make → the exact result file and number that supports it | A result lands that the paper will cite, or a claim turns out unsupported |
| [experiment-log.md](experiment-log.md) | Dated lab notebook: what was run, why, the command, the outcome, the commit | **Every** run that produced a number (including failed or negative ones) |
| [decisions.md](decisions.md) | Methodology decisions and why they were made (protocols, metrics, model-selection rules) | Before running an experiment whose protocol you are choosing |
| [references.md](references.md) | Papers and products we cite, what we use each for, verification status | You read or cite a new paper |
| [draft/](draft/) | Section drafts in Markdown, one file per section | At the end of each roadmap phase |

## Rules that keep the paper honest

1. **No number in a draft unless it is in `claims.md`** with a file path. Numbers in the paper
   must be regenerable from `ml/results/`.
2. **Decide the protocol before you see the result.** Write the decision in `decisions.md`
   first (this is how the window model was chosen — see D8 — and it is worth saying so in
   the paper).
3. **Log negative results too.** "Smoothing always hurt" and "history does not help on the
   temporal split" are findings, and reviewers trust papers that report them.
4. **Always report both homes.** Aruba-only claims are not allowed (DEI commitment, and Milan
   behaves differently).
5. **Say which setting a number comes from**: known activity boundaries (segment) or live
   sliding window. They are not comparable.

## Where results live

- Segment setting: [ml/results/summary.md](../ml/results/summary.md) (single runs, cv and temporal),
  [ml/results/experiments.md](../ml/results/experiments.md) (3-seed repeats and lr tuning).
- Live window setting: [ml/results/windows.md](../ml/results/windows.md).
- Per-run files: `ml/results/<home>/<split>/<model>/` → `metrics.json`, `per_class.csv`,
  `confusion.png`, `predictions.csv(.gz)`.
- The ordered to-do list is [ROADMAP.md](../ROADMAP.md); each step names the paper section it feeds.
