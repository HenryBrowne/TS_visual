from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.datasets.models import Dataset, DatasetFormat, DatasetSourceType, DatasetStatus
from app.datasets.service import resolve_dataset_id
from app.imports.schema import IngestRequest
from app.jobs.benchmark import run_benchmark_job
from app.jobs.ingest_and_profile import run_ingest_and_profile_job
from app.jobs.models import Job, JobStatus
from app.jobs.schemas import JobRead

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/benchmark", response_model=JobRead)
def start_benchmark_job(
    background_tasks: BackgroundTasks, dataset_id: str | None = None, db: Session = Depends(get_db)
):
    resolved_dataset_id = resolve_dataset_id(db, dataset_id)
    if resolved_dataset_id is None:
        raise HTTPException(status_code=400, detail="No ready dataset available to benchmark")

    job = Job(job_type="benchmark", status=JobStatus.pending)
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_benchmark_job, job.id, resolved_dataset_id)
    return job


@router.post("/ingest-and-profile", response_model=JobRead)
def start_ingest_and_profile_job(
    request: IngestRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    dataset = Dataset(
        name=request.name,
        source_type=DatasetSourceType.user_upload,
        has_benchmark_scores=False,
        format=DatasetFormat(request.format),
        status=DatasetStatus.processing,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    job = Job(job_type="ingest_and_profile", status=JobStatus.pending)
    db.add(job)
    db.commit()
    db.refresh(job)

    dataset.job_id = job.id
    db.commit()

    background_tasks.add_task(
        run_ingest_and_profile_job, job.id, dataset.id, request.upload_id, request.format, request.column_mapping
    )
    return job
