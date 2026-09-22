from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SeriesDiagnosticCache(Base):
    __tablename__ = "series_diagnostic_cache"

    series_id: Mapped[str] = mapped_column(String, primary_key=True)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_features: Mapped[list] = mapped_column(JSON, nullable=False)
    suggested_models: Mapped[list] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
