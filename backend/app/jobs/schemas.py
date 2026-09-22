from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.jobs.models import JobStatus


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_type: str
    status: JobStatus
    progress_pct: float
    result_ref: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
