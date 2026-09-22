"""The statistical profile is a cache read in this app's architecture --
computed once and read many times, not recomputed on every request (the
STL/ADF/KPSS battery is too slow for that to stay sub-second). Ingestion
or a batch job is expected to populate this cache; get_or_compute_profile
also computes-and-stores lazily on a miss so the cache is self-healing.
"""

import pandas as pd
from sqlalchemy.orm import Session

from app.profiling.diagnostics import profile_series
from app.profiling.models import SeriesProfileCache
from app.profiling.schema import SeriesProfile


def store_profile(db: Session, profile: SeriesProfile) -> None:
    row = db.get(SeriesProfileCache, profile.series_id)
    if row is None:
        db.add(SeriesProfileCache(series_id=profile.series_id, profile=profile.model_dump(mode="json")))
    else:
        row.profile = profile.model_dump(mode="json")
    db.commit()


def get_cached_profile(db: Session, series_id: str) -> SeriesProfile | None:
    row = db.get(SeriesProfileCache, series_id)
    if row is None:
        return None
    return SeriesProfile.model_validate(row.profile)


def get_or_compute_profile(db: Session, df: pd.DataFrame, series_id: str, frequency: str) -> SeriesProfile:
    cached = get_cached_profile(db, series_id)
    if cached is not None:
        return cached

    profile = profile_series(df, series_id=series_id, frequency=frequency)
    store_profile(db, profile)
    return profile
