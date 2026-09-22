from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.jobs import router as jobs_router
from app.api.leaderboard import router as leaderboard_router
from app.api.series import router as series_router
from app.core.db import Base, engine
from app.features import models as feature_models  # noqa: F401  (registers SeriesFeatureConfig)
from app.ingestion import models as ingestion_models  # noqa: F401  (registers Series)
from app.jobs import models as job_models  # noqa: F401  (registers Job)
from app.llm import models as llm_models  # noqa: F401  (registers SeriesDiagnosticCache)
from app.models import leaderboard as leaderboard_models  # noqa: F401  (registers LeaderboardEntry)
from app.profiling import models as profiling_models  # noqa: F401  (registers SeriesProfileCache)

app = FastAPI(title="TS Forecast Benchmark API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(leaderboard_router)
app.include_router(series_router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}
