"""Commits a CSV import: parses the full uploaded file (not the sample
the wizard validated against), applies the confirmed column mapping,
writes normalized series, profiles every series, and runs a batched LLM
diagnostic pass -- unlike the reference-dataset path, user uploads are
profiled and diagnosed upfront here rather than lazily on first access,
since the job is already async and this is the natural place for it.
"""

import pandas as pd

from app.core.db import SessionLocal
from app.core.frequency import infer_frequency_label
from app.core.paths import DATA_PROCESSED_DIR
from app.datasets.models import Dataset, DatasetStatus
from app.ingestion.writer import write_series_table
from app.imports.storage import get_upload_path
from app.imports.validation import apply_mapping
from app.jobs.models import Job, JobStatus
from app.llm.cache import store_diagnostics_batch
from app.llm.client import run_diagnostics
from app.profiling.cache import store_profile
from app.profiling.diagnostics import profile_series

LLM_BATCH_SIZE = 20


def _clean_and_dedupe(long_df: pd.DataFrame) -> pd.DataFrame:
    df = long_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["timestamp", "value"])
    # Duplicate (series_id, timestamp): keep the last occurrence, per the
    # wizard's validate-step warning.
    df = df.sort_values(["series_id", "timestamp"])
    df = df.drop_duplicates(subset=["series_id", "timestamp"], keep="last")
    return df.reset_index(drop=True)


def _infer_frequency_by_series(df: pd.DataFrame) -> dict[str, str]:
    labels: dict[str, str] = {}
    for series_id, group in df.groupby("series_id"):
        ts_sorted = group["timestamp"].sort_values()
        inferred = pd.infer_freq(ts_sorted) if len(ts_sorted) >= 3 else None
        labels[series_id] = infer_frequency_label(inferred)
    return labels


def run_ingest_and_profile_job(
    job_id: str, dataset_id: str, upload_id: str, fmt: str, column_mapping: dict[str, str]
) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        dataset = db.get(Dataset, dataset_id)
        if job is None or dataset is None:
            return

        job.status = JobStatus.running
        job.progress_pct = 0.0
        db.commit()

        path = get_upload_path(upload_id)
        raw_df = pd.read_csv(path)
        long_df = apply_mapping(raw_df, column_mapping, fmt)
        clean_df = _clean_and_dedupe(long_df)

        if clean_df.empty:
            raise ValueError("No valid rows remained after parsing the full file")

        job.progress_pct = 5.0
        db.commit()

        frequency_by_series = _infer_frequency_by_series(clean_df)

        DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        out_path = DATA_PROCESSED_DIR / f"upload_{dataset_id}.parquet"
        clean_df.to_parquet(out_path, index=False)
        write_series_table(db, dataset_id, clean_df, out_path, frequency_by_series=frequency_by_series)

        job.progress_pct = 15.0
        db.commit()

        series_ids = sorted(clean_df["series_id"].unique())
        total = len(series_ids)
        profiles = []
        for i, series_id in enumerate(series_ids, start=1):
            series_df = clean_df[clean_df["series_id"] == series_id][["timestamp", "value"]]
            profile = profile_series(series_df, series_id=series_id, frequency=frequency_by_series[series_id])
            store_profile(db, dataset_id, profile)
            profiles.append(profile)

            job.progress_pct = round(15 + 55 * i / total, 2) if total else 70.0
            db.commit()

        for start in range(0, len(profiles), LLM_BATCH_SIZE):
            chunk = profiles[start : start + LLM_BATCH_SIZE]
            diagnostics = run_diagnostics(chunk)
            store_diagnostics_batch(db, dataset_id, diagnostics)

            job.progress_pct = round(70 + 25 * min(start + LLM_BATCH_SIZE, len(profiles)) / len(profiles), 2)
            db.commit()

        dataset.status = DatasetStatus.ready
        job.status = JobStatus.succeeded
        job.progress_pct = 100.0
        job.result_ref = dataset_id
        db.commit()
    except Exception as exc:  # noqa: BLE001 -- job failures must be recorded, not raised into the background task runner
        db.rollback()
        job = db.get(Job, job_id)
        dataset = db.get(Dataset, dataset_id)
        if job is not None:
            job.status = JobStatus.failed
            job.error = str(exc)
        if dataset is not None:
            dataset.status = DatasetStatus.failed
        db.commit()
    finally:
        db.close()
