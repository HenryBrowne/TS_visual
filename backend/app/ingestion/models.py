from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Series(Base):
    __tablename__ = "series"

    series_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[str] = mapped_column(String, nullable=False)
    n_obs: Mapped[int] = mapped_column(Integer, nullable=False)
    start_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
