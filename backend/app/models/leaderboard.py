from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


class LeaderboardEntry(Base):
    """One model's backtest score on one series, from the most recent batch
    benchmark job. Re-running the job overwrites a series/model's prior row
    rather than accumulating history, since the leaderboard reflects the
    latest full-dataset run, not a time series of runs.
    """

    __tablename__ = "leaderboard_entries"
    __table_args__ = (
        UniqueConstraint("dataset_id", "series_id", "model_name", name="uq_leaderboard_dataset_series_model"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String, ForeignKey("datasets.id"), nullable=False)
    series_id: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    mae: Mapped[float] = mapped_column(Float, nullable=False)
    rmse: Mapped[float] = mapped_column(Float, nullable=False)
    smape: Mapped[float] = mapped_column(Float, nullable=False)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def upsert_leaderboard_entry(
    db: Session, dataset_id: str, series_id: str, model_name: str, metrics: dict, job_id: str
) -> None:
    row = (
        db.query(LeaderboardEntry)
        .filter(
            LeaderboardEntry.dataset_id == dataset_id,
            LeaderboardEntry.series_id == series_id,
            LeaderboardEntry.model_name == model_name,
        )
        .one_or_none()
    )
    if row is None:
        row = LeaderboardEntry(dataset_id=dataset_id, series_id=series_id, model_name=model_name, job_id=job_id, **metrics)
        db.add(row)
    else:
        row.mae = metrics["mae"]
        row.rmse = metrics["rmse"]
        row.smape = metrics["smape"]
        row.job_id = job_id


def get_leaderboard_rows(db: Session, dataset_id: str) -> list[dict]:
    """Pure cache read: aggregates the most recent batch benchmark job's
    per-series scores, within one dataset, into a per-model average -- no
    live model fitting, and never mixes scores across datasets.
    """
    rows = (
        db.query(
            LeaderboardEntry.model_name,
            func.avg(LeaderboardEntry.mae).label("avg_mae"),
            func.avg(LeaderboardEntry.rmse).label("avg_rmse"),
            func.avg(LeaderboardEntry.smape).label("avg_smape"),
            func.count(LeaderboardEntry.series_id).label("n_series"),
        )
        .filter(LeaderboardEntry.dataset_id == dataset_id)
        .group_by(LeaderboardEntry.model_name)
        .order_by(func.avg(LeaderboardEntry.smape).asc())
        .all()
    )

    return [
        {
            "model_name": r.model_name,
            "avg_mae": round(r.avg_mae, 4),
            "avg_rmse": round(r.avg_rmse, 4),
            "avg_smape": round(r.avg_smape, 4),
            "n_series": r.n_series,
        }
        for r in rows
    ]
