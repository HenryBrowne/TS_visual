"""Normalize a subset of an M4 frequency group into the common
`series_id | timestamp | value` schema, write it to a local parquet file,
and index it in the Postgres `series` table under a given dataset.

M4 does not release real calendar dates, so timestamps are synthesized by
anchoring every series to a fixed start date and stepping by the group's
frequency. This keeps the schema real-datetime-typed for downstream
calendar/holiday feature work, at the cost of the dates being arbitrary.
"""

import argparse
from pathlib import Path

import pandas as pd
from datasetsforecast.m4 import M4
from sqlalchemy.orm import Session

from app.core.db import Base, SessionLocal, engine
from app.core.frequency import FREQ_TO_PANDAS
from app.core.paths import DATA_PROCESSED_DIR, DATA_RAW_DIR
from app.datasets.models import DatasetFormat, DatasetStatus
from app.datasets.service import get_or_create_reference_dataset
from app.ingestion.writer import write_series_table

ANCHOR_DATE = pd.Timestamp("2013-01-01")


def normalize(y_df: pd.DataFrame, group: str, limit: int) -> pd.DataFrame:
    ids = sorted(y_df["unique_id"].unique())[:limit]
    subset = y_df[y_df["unique_id"].isin(ids)].copy()

    subset["ds"] = subset["ds"].astype(int)
    subset = subset.sort_values(["unique_id", "ds"])

    # `ds` is a 1-indexed step counter shared across all series in the group
    # (M4 releases no real dates), so timestamps only depend on the step, not
    # on which series it belongs to.
    freq = FREQ_TO_PANDAS[group]
    step_range = pd.date_range(start=ANCHOR_DATE, periods=subset["ds"].max(), freq=freq)
    subset["timestamp"] = step_range[subset["ds"].to_numpy() - 1]

    out = subset.rename(columns={"unique_id": "series_id", "y": "value"})[
        ["series_id", "timestamp", "value"]
    ].reset_index(drop=True)
    return out


def ingest(db: Session, dataset_id: str, group: str, limit: int) -> Path:
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    y_df, _, _ = M4.load(directory=str(DATA_RAW_DIR), group=group)
    normalized = normalize(y_df, group, limit)

    out_path = DATA_PROCESSED_DIR / f"m4_{group.lower()}_{dataset_id}.parquet"
    normalized.to_parquet(out_path, index=False)

    write_series_table(db, dataset_id, normalized, out_path, default_frequency=group)

    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest an M4 frequency group subset as a reference dataset")
    parser.add_argument("--group", default="Daily", choices=list(FREQ_TO_PANDAS))
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        dataset = get_or_create_reference_dataset(db, name=f"M4 ({args.group})", format=DatasetFormat.long)
        out_path = ingest(db, dataset.id, args.group, args.limit)
        dataset.status = DatasetStatus.ready
        db.commit()
    finally:
        db.close()

    print(f"Wrote normalized subset to {out_path} (dataset_id={dataset.id})")


if __name__ == "__main__":
    main()
