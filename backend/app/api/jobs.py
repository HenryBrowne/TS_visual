from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.jobs.benchmark import run_benchmark_job
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
def start_benchmark_job(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = Job(job_type="benchmark", status=JobStatus.pending)
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_benchmark_job, job.id)
    return job
