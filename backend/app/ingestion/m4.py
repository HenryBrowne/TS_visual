"""Normalize a subset of an M4 frequency group into the common
`series_id | timestamp | value` schema, write it to a local parquet file,
and index it in the Postgres `series` table.

M4 does not release real calendar dates, so timestamps are synthesized by
anchoring every series to a fixed start date and stepping by the group's
frequency. This keeps the schema real-datetime-typed for downstream
calendar/holiday feature work, at the cost of the dates being arbitrary.
"""

import argparse
from pathlib import Path

import pandas as pd
from datasetsforecast.m4 import M4

from app.core.db import Base, SessionLocal, engine
from app.core.frequency import FREQ_TO_PANDAS
from app.ingestion.models import Series

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

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


def ingest(dataset: str, group: str, limit: int) -> Path:
    if dataset != "M4":
        raise ValueError("Only the M4 dataset is supported in v1")

    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    y_df, _, _ = M4.load(directory=str(DATA_RAW_DIR), group=group)
    normalized = normalize(y_df, group, limit)

    out_path = DATA_PROCESSED_DIR / f"m4_{group.lower()}_sample.parquet"
    normalized.to_parquet(out_path, index=False)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for series_id, series_df in normalized.groupby("series_id"):
            row = db.get(Series, series_id)
            if row is None:
                row = Series(series_id=series_id)
                db.add(row)
            row.dataset = dataset
            row.frequency = group
            row.n_obs = len(series_df)
            row.start_timestamp = series_df["timestamp"].min()
            row.end_timestamp = series_df["timestamp"].max()
            row.source_path = out_path.relative_to(PROJECT_ROOT).as_posix()
        db.commit()
    finally:
        db.close()

    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest an M4 frequency group subset")
    parser.add_argument("--dataset", default="M4")
    parser.add_argument("--group", default="Daily", choices=list(FREQ_TO_PANDAS))
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    out_path = ingest(args.dataset, args.group, args.limit)
    print(f"Wrote normalized subset to {out_path}")


if __name__ == "__main__":
    main()
