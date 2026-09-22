from fastapi import FastAPI

from app.api.jobs import router as jobs_router
from app.core.db import Base, engine
from app.jobs import models as job_models  # noqa: F401  (registers Job with Base metadata)

app = FastAPI(title="TS Forecast Benchmark API")

app.include_router(jobs_router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}
