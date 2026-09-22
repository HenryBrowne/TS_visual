from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.datasets.models import DatasetFormat, DatasetSourceType, DatasetStatus


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    source_type: DatasetSourceType
    has_benchmark_scores: bool
    format: DatasetFormat
    status: DatasetStatus
    job_id: str | None
    created_at: datetime
