from functools import lru_cache

import pandas as pd
from sqlalchemy.orm import Session

from app.core.paths import PROJECT_ROOT
from app.ingestion.models import Series


@lru_cache(maxsize=8)
def _read_parquet_cached(source_path: str) -> pd.DataFrame:
    return pd.read_parquet(PROJECT_ROOT / source_path)


def load_series(db: Session, dataset_id: str, series_id: str) -> tuple[pd.DataFrame, str]:
    """Returns (timestamp/value DataFrame, frequency) for a series, or
    raises KeyError if the series is not indexed in Postgres.
    """
    row = db.get(Series, (dataset_id, series_id))
    if row is None:
        raise KeyError(f"Unknown series_id {series_id!r} in dataset {dataset_id!r}")

    full = _read_parquet_cached(row.source_path)
    df = full[full["series_id"] == series_id][["timestamp", "value"]].reset_index(drop=True)
    return df, row.frequency
