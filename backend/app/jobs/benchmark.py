"""Full-dataset batch benchmark: refits every series in one dataset against
the default feature catalog and every model in the zoo, writing per-series,
per-model scores to the leaderboard cache table. Runs as a FastAPI
BackgroundTask -- owns its own DB session since the request's session is
torn down once the response is sent.
"""

from app.core.db import SessionLocal
from app.ingestion.loader import load_series
from app.ingestion.models import Series
from app.jobs.models import Job, JobStatus
from app.models.leaderboard import upsert_leaderboard_entry
from app.models.refit import refit_series
from app.profiling.cache import get_or_compute_profile


def run_benchmark_job(job_id: str, dataset_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return

        job.status = JobStatus.running
        job.progress_pct = 0.0
        db.commit()

        series_ids = [
            row.series_id
            for row in db.query(Series.series_id)
            .filter(Series.dataset_id == dataset_id)
            .order_by(Series.series_id)
            .all()
        ]
        total = len(series_ids)

        for i, series_id in enumerate(series_ids, start=1):
            df, frequency = load_series(db, dataset_id, series_id)
            profile = get_or_compute_profile(db, df, dataset_id=dataset_id, series_id=series_id, frequency=frequency)
            result = refit_series(df, series_id=series_id, frequency=frequency, toggle_state={}, profile=profile)

            for model_name, metrics in result["metrics"].items():
                upsert_leaderboard_entry(db, dataset_id, series_id, model_name, metrics, job_id)

            job.progress_pct = round(100 * i / total, 2) if total else 100.0
            db.commit()

        job.status = JobStatus.succeeded
        job.result_ref = f"leaderboard:{dataset_id}:{total}_series"
        db.commit()
    except Exception as exc:  # noqa: BLE001 -- job failures must be recorded, not raised into the background task runner
        db.rollback()
        job = db.get(Job, job_id)
        if job is not None:
            job.status = JobStatus.failed
            job.error = str(exc)
            db.commit()
    finally:
        db.close()
