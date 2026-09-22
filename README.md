# Time Series Forecasting Benchmark App

An interactive app that imports time series data — reference benchmark datasets (M4, M5)
or your own CSV via a 4-step import wizard — profiles each series (seasonality, trend,
stationarity, intermittency, missing data, outliers), uses an LLM to suggest data-quality
fixes and features (cross-checked against real calendar/holiday data), engineers those
features, and benchmarks statistical models (ARIMA, ETS, Theta) against ML models
(LightGBM/XGBoost). Results are shown via a React workbench.

## Architecture

**Datasets:** every series belongs to a `dataset` (`reference` — M4/M5, seeded once via
`scripts/seed_reference_datasets.py`, has published benchmark scores — or `user_upload`,
via the import wizard, no external benchmark). `series_id` is only unique *within* a
dataset, so every series-scoped table is keyed by `(dataset_id, series_id)`, and every
series/leaderboard endpoint takes an optional `dataset_id` query param — omit it and the
backend defaults to the most-recently-created `ready` dataset (this app has no
user/session concept, so "most-recently-used" degrades to "most-recently-created").

**Two-tier compute model:**
- **Batch tier** — full M4/M5 benchmark runs offline as an async job, results cached in
  Postgres. Powers the leaderboard (pure cache read).
- **Live tier** — operates on a stratified sample (~200–500 series). Single-series refits
  (stats + ML only) are synchronous API calls, no job queue.

**API shape:**
- Cache reads: plain sync `GET` endpoints (series list/search, profile, last-remembered
  feature config, leaderboard).
- Live refit: sync `POST /api/series/{id}/refit` — body is feature toggle state, response
  is metrics + forecast, persists the new config as a side effect.
- Batch work: async job pattern — `POST /api/jobs/...` returns a `job_id`,
  `GET /api/jobs/{job_id}` is polled for `{status, progress_pct, result_ref}`. FastAPI
  `BackgroundTasks` with job state tracked in a Postgres `jobs` table.

**Frontend (React):**
1. Landing (`/`) — routes a first-time visitor: an existing ready upload → its dashboard;
   an upload mid-import → its job-progress view; neither, and the M4 demo hasn't been
   shown yet → the M4 dashboard (and marks it shown); otherwise → the import blocker.
2. Dashboard (`/`, or `/demo` to force the M4 reference dataset) — leaderboard, cache-only.
3. Series explorer (`/explorer`) — searchable/filterable list.
4. Workbench (`/workbench`) — multi-select series comparison (up to ~4–5), per-series
   feature toggles, shared overlay chart (solid = actual, dashed = forecast).
5. Import wizard (`/import`) — upload → map columns → preview & validate → name & confirm,
   then polls the ingest-and-profile job and redirects to the explorer once ready.

## Project layout

```
backend/
  app/
    main.py         FastAPI app, CORS, router registration, startup table creation
    api/            routers: datasets.py, imports.py, series.py, leaderboard.py, jobs.py
    core/           config (.env), db session, frequency alias mapping, path constants
    datasets/       Dataset model/schema, default-dataset resolution
    imports/        CSV upload storage, format/column-role detection, validation
    ingestion/      M4 loader/normalizer, shared Series-table writer, Series metadata,
                     parquet loader (with lru_cache)
    profiling/      statistical diagnostics battery + Postgres profile cache
    llm/            diagnostic prompts, structured-output client, holiday cross-check,
                     Postgres diagnostic cache
    features/       feature catalog, engineering (column builders), before/after deltas
    models/         stats (statsforecast) + ML (LightGBM/XGBoost) wrappers, refit
                     orchestration, metrics, leaderboard aggregation
    jobs/           Job model/schemas, background batch-benchmark and
                     ingest-and-profile workers
  scripts/          seed_reference_datasets.py -- seeds M4/M5, not run through the wizard
  requirements.txt
  tests/            pytest suite (profiling, features, llm, models, leaderboard, imports)
frontend/           Vite React app (Landing / Dashboard / Explorer / Workbench / Import)
  src/
    api/client.js   fetch wrapper for the backend API
    pages/          one file + stylesheet per view
    components/     SeriesChart (chart.js overlay), SeriesCard (workbench accordion),
                     JobProgress (shared job-polling UI)
data/               M4/M5 raw + processed + user uploads (all gitignored)
docker-compose.yml  local Postgres
```

## Branching model

- `main` — stable, deployable
- `develop` — integration branch
- `feature/<name>` — new functionality
- `fix/<name>` — bug fixes
- `release/<version>` — release preparation

Work happens on `feature/*` or `fix/*` branches off `develop`, merged back via PR.
`release/*` branches cut from `develop` and merge into both `main` and `develop`.

## Running it locally

These steps take a fresh clone to a working app with data loaded. Run them in order the
first time; after that, see [Day-to-day startup](#day-to-day-startup) below.

### 1. Start Postgres

```bash
docker compose up -d
```

This starts Postgres 16 on **host port 5435** (not the default 5432 — that port, and
5433/5434, were already taken by other local Postgres instances on the original dev
machine; check `docker-compose.yml` if you need to change it, and update the connection
strings below to match).

### 2. Backend: environment and dependencies

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Git Bash; .venv/bin/activate on WSL; .venv\Scripts\Activate.ps1 on PowerShell
pip install -r requirements.txt

cp .env.example .env
# then edit backend/.env and set ANTHROPIC_API_KEY (needed for the LLM diagnostic layer —
# see app/llm/client.py and app/llm/cache.py). DATABASE_URL already points at the
# docker-compose Postgres above.
```

### 3. Seed the M4 reference dataset

```bash
# still in backend/, with the venv active
python -m scripts.seed_reference_datasets --group Daily --limit 50
```

Downloads M4 Daily (cached under `data/raw/` after the first run), normalizes a 50-series
subset into `series_id | timestamp | value`, writes it to `data/processed/`, creates a
`datasets` row (`source_type='reference'`), and indexes each series' metadata in Postgres.
Increase `--limit` (or drop it — default 50) for a larger sample; `--group` also accepts
Yearly/Quarterly/Monthly/Weekly/Hourly. Safe to re-run — reuses the existing dataset row
rather than duplicating it.

### 4. Run the backend

```bash
# still in backend/, with the venv active
uvicorn app.main:app --port 8000 --reload
```

Creates any missing tables on startup. Check `http://localhost:8000/api/health` →
`{"status": "ok"}`. Interactive API docs at `http://localhost:8000/docs`.

### 5. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The backend allows CORS from this origin
(`app/main.py`) — if you serve the frontend from a different port, update the
`allow_origins` list there.

### 6. Populate the leaderboard (optional but recommended)

The Dashboard's leaderboard is empty until a batch benchmark job has run once:

```bash
curl -X POST http://localhost:8000/api/jobs/benchmark
```

Poll `GET /api/jobs/{id}` (returned in the response above) until `status` is
`succeeded`, or just watch the progress bar on the Dashboard page — refits every
ingested series against every model in the zoo and writes to the leaderboard cache. With
a cold profile/diagnostic cache this takes a few minutes for 50 series (profiling's
STL/ADF/KPSS battery is the slow part); it's fast on subsequent runs since profiles are
cached.

## Day-to-day startup

Once the one-time setup above is done, each new session just needs:

```bash
docker compose up -d                                    # Postgres (project root)

cd backend && source .venv/Scripts/activate              # backend
uvicorn app.main:app --port 8000 --reload

cd frontend && npm run dev                                # frontend, separate terminal
```

Re-run step 3 only if you want to expand the M4 sample or refresh the raw data; it's
idempotent (safe to re-run, upserts by `(dataset_id, series_id)`). To add your own data,
use the import wizard at `/import` instead — no CLI step needed.

## Running tests

```bash
cd backend
source .venv/Scripts/activate
pytest tests/ -v
```

No live Postgres or API key needed — the suite uses synthetic series and an in-memory
SQLite session for the leaderboard tests, and only exercises the deterministic parts of
the LLM layer (holiday cross-check, prompt building). Only the running app itself (the
`GET /api/series/{id}/features` endpoint, via `app/llm/client.py`) makes real API calls,
which need `ANTHROPIC_API_KEY` set in `backend/.env`.
