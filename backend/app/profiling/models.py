from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SeriesProfileCache(Base):
    __tablename__ = "series_profile_cache"

    dataset_id: Mapped[str] = mapped_column(String, ForeignKey("datasets.id"), primary_key=True)
    series_id: Mapped[str] = mapped_column(String, primary_key=True)
    profile: Mapped[dict] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
