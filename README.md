# Time Series Forecasting Benchmark App

An interactive app that imports time series benchmark datasets (M4, M5), profiles each
series (seasonality, trend, stationarity, intermittency, missing data, outliers), uses an
LLM to suggest data-quality fixes and features (cross-checked against real calendar/holiday
data), engineers those features, and benchmarks statistical models (ARIMA, ETS, Theta)
against ML models (LightGBM/XGBoost). Results are shown via a React workbench.

## Architecture

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
1. Dashboard — leaderboard, cache-only.
2. Series explorer — searchable/filterable list.
3. Workbench — multi-select series comparison (up to ~4–5), per-series feature toggles,
   shared overlay chart (solid = actual, dashed = forecast).

## Project layout

```
backend/
  app/
    main.py         FastAPI app, CORS, router registration, startup table creation
    api/            routers: series.py, leaderboard.py, jobs.py
    core/           config (.env), db session, frequency alias mapping
    ingestion/      M4 loader/normalizer, Series metadata, parquet loader (with lru_cache)
    profiling/      statistical diagnostics battery + Postgres profile cache
    llm/            diagnostic prompts, structured-output client, holiday cross-check,
                     Postgres diagnostic cache
    features/       feature catalog, engineering (column builders), before/after deltas
    models/         stats (statsforecast) + ML (LightGBM/XGBoost) wrappers, refit
                     orchestration, metrics, leaderboard aggregation
    jobs/           Job model/schemas, background batch benchmark worker
  requirements.txt
  tests/            pytest suite (profiling, features, llm, models, leaderboard)
frontend/           Vite React app (Dashboard / Explorer / Workbench)
  src/
    api/client.js   fetch wrapper for the backend API
    pages/          one file + stylesheet per view
    components/     SeriesChart (chart.js overlay), SeriesCard (workbench accordion)
data/               M4/M5 raw + processed (gitignored; populated by ingestion)
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

### 3. Ingest data

```bash
# still in backend/, with the venv active
python -m app.ingestion.m4 --group Daily --limit 50
```

Downloads M4 Daily (cached under `data/raw/` after the first run), normalizes a 50-series
subset into `series_id | timestamp | value`, writes it to
`data/processed/m4_daily_sample.parquet`, and indexes each series' metadata in Postgres.
Increase `--limit` (or drop it — default 50) for a larger sample; `--group` also accepts
Yearly/Quarterly/Monthly/Weekly/Hourly.

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

Re-run step 3 (ingestion) only if you want to expand the sample or refresh the raw data;
it's idempotent (safe to re-run, upserts by `series_id`).

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
