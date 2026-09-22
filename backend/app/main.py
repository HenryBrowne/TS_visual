from fastapi import FastAPI

from app.api.jobs import router as jobs_router
from app.api.series import router as series_router
from app.core.db import Base, engine
from app.features import models as feature_models  # noqa: F401  (registers SeriesFeatureConfig)
from app.ingestion import models as ingestion_models  # noqa: F401  (registers Series)
from app.jobs import models as job_models  # noqa: F401  (registers Job)
from app.profiling import models as profiling_models  # noqa: F401  (registers SeriesProfileCache)

app = FastAPI(title="TS Forecast Benchmark API")

app.include_router(jobs_router)
app.include_router(series_router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}
