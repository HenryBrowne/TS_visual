from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.core.paths import PROJECT_ROOT
from app.ingestion.models import Series


def write_series_table(
    db: Session,
    dataset_id: str,
    normalized: pd.DataFrame,
    out_path: Path,
    frequency_by_series: dict[str, str] | None = None,
    default_frequency: str = "Daily",
) -> None:
    """Upserts one Series row per series_id in `normalized` (columns:
    series_id, timestamp, value), pointing at a single shared parquet file.
    Shared by the M4 loader and the CSV import job.
    """
    for series_id, series_df in normalized.groupby("series_id"):
        row = db.get(Series, (dataset_id, series_id))
        if row is None:
            row = Series(dataset_id=dataset_id, series_id=series_id)
            db.add(row)
        row.frequency = (frequency_by_series or {}).get(series_id, default_frequency)
        row.n_obs = len(series_df)
        row.start_timestamp = series_df["timestamp"].min()
        row.end_timestamp = series_df["timestamp"].max()
        row.source_path = out_path.relative_to(PROJECT_ROOT).as_posix()
    db.commit()
