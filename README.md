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
    main.py
    api/          routers: series.py, leaderboard.py, jobs.py
    core/         config, db session
    profiling/    statistical diagnostics
    features/     feature engineering + before/after comparison
    models/       stats + ML model wrappers (statsforecast/mlforecast)
    llm/          diagnostic prompt templates, structured-output parsing
    jobs/         background task workers, job status updates
  requirements.txt
  tests/
frontend/         Vite React app
data/              M4/M5 raw + processed (gitignored)
```

## Branching model

- `main` — stable, deployable
- `develop` — integration branch
- `feature/<name>` — new functionality
- `fix/<name>` — bug fixes
- `release/<version>` — release preparation

Work happens on `feature/*` or `fix/*` branches off `develop`, merged back via PR.
`release/*` branches cut from `develop` and merge into both `main` and `develop`.

## Setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Git Bash; .venv/bin/activate on WSL
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```
