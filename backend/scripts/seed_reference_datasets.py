"""Seeds M4 as a reference dataset (source_type='reference',
has_benchmark_scores=True). Reference datasets are large and
well-specified in format, so they're loaded directly here rather than
through the interactive CSV import wizard's column-mapping flow.

M5 is not implemented yet -- this project has only ever built an M4
loader (app/ingestion/m4.py). Add an equivalent loader there and a
second seed call here when M5 support lands.

Usage: python -m scripts.seed_reference_datasets [--group Daily] [--limit 50]
"""

import argparse

from app.core.db import Base, SessionLocal, engine
from app.core.frequency import FREQ_TO_PANDAS
from app.datasets.models import DatasetFormat, DatasetStatus
from app.datasets.service import get_or_create_reference_dataset
from app.ingestion.m4 import ingest


def seed_m4(group: str, limit: int) -> str:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        dataset = get_or_create_reference_dataset(db, name=f"M4 ({group})", format=DatasetFormat.long)
        try:
            ingest(db, dataset.id, group, limit)
        except Exception:
            dataset.status = DatasetStatus.failed
            db.commit()
            raise

        dataset.status = DatasetStatus.ready
        db.commit()
        return dataset.id
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed M4 as a reference dataset")
    parser.add_argument("--group", default="Daily", choices=list(FREQ_TO_PANDAS))
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    dataset_id = seed_m4(args.group, args.limit)
    print(f"Seeded M4 ({args.group}) as dataset_id={dataset_id}")


if __name__ == "__main__":
    main()
