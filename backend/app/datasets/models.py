import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DatasetSourceType(str, Enum):
    reference = "reference"
    user_upload = "user_upload"


class DatasetFormat(str, Enum):
    long = "long"
    wide = "wide"


class DatasetStatus(str, Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[DatasetSourceType] = mapped_column(SAEnum(DatasetSourceType), nullable=False)
    has_benchmark_scores: Mapped[bool] = mapped_column(Boolean, nullable=False)
    format: Mapped[DatasetFormat] = mapped_column(SAEnum(DatasetFormat), nullable=False)
    status: Mapped[DatasetStatus] = mapped_column(SAEnum(DatasetStatus), nullable=False, default=DatasetStatus.processing)
    job_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
