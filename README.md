# AmbiLiving

**Ambient-sensor activity recognition and caregiver monitoring** — FYP F26-108
(Aleeza Azhar · Hudiya e Zehra · Ibrahim Babar; supervisor Dr. Labiba Fahad).

Passive motion and door sensors in an elderly resident's home are turned into
what the resident was *doing* (sleeping, cooking, leaving home, …), checked
against their own routine, and shown to a caregiver as a few actionable alerts:

```
sensors → activity recognition → routine deviation → alert routing → caregiver dashboard
```

Data: CASAS **Aruba** (1 resident, 2010–2011) and **Milan** (1 resident + pet, 2009–2010).

## Repository

| Folder | What is in it |
|---|---|
| [`ml/har/`](ml/har/) | Python research code: data parsing, five recognition models, sliding windows, routine-deviation detection, alert routing, replay export |
| [`ml/api/`](ml/api/) | Backend (FastAPI): live recognition, replay streaming, data for the dashboard |
| [`ml/results/`](ml/results/) | Every archived experiment (`metrics.json`, per-class tables, confusion matrices) and the summary tables |
| [`src/`](src/) | Caregiver dashboard (Next.js 16, React 19, Tailwind v4) |
| [`paper/`](paper/) | Paper drafts, claims, decisions (D1…) and the experiment log |
| [`poster/`](poster/) | FYP poster (`py build.py` renders `ambiliving-poster.html`) |

Where the project stands: [PROJECT_STATUS.md](PROJECT_STATUS.md). What is left, in order: [ROADMAP.md](ROADMAP.md).

## Run it

You need Node.js 20+ and Python 3.11+ (on Windows use the `py` launcher; `python` may be the Store stub).

**1. Backend** — from `ml/`:

```bash
py -m pip install -r requirements.txt
py -m api                      # http://127.0.0.1:8000, interactive docs at /docs
```

The saved models (`ml/models/`) and exported data are in the repository, so the
backend runs without the raw datasets.

**2. Dashboard** — from the repository root, in a second terminal:

```bash
npm install
npm run dev                    # http://localhost:3000
```

The dashboard reads the backend at `http://127.0.0.1:8000` (set
`NEXT_PUBLIC_AMBILIVING_API` to change it). If the backend is not running it
falls back to the data bundled with the app; the header badge says which.

## Reproduce an experiment

Put the raw CASAS files at `ml/data/raw/aruba.txt` and `ml/data/raw/milan.txt`
(git-ignored), then from `ml/`:

```bash
py -m har.run --dataset aruba --model hgb --context          # known-boundary recognition
py -m har.run_windows --dataset all --model bilstm --seeds 1  # live sliding-window recognition
py -m pytest tests -q                                       # backend tests
```

All experiment commands and how to read their output: [ml/README.md](ml/README.md).

## Checks

```bash
npx tsc --noEmit     # typecheck
npm run lint
```
