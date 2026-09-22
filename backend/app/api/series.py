from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.features.models import SeriesFeatureConfig
from app.ingestion.loader import load_series
from app.ingestion.models import Series
from app.models.refit import refit_series
from app.profiling.cache import get_or_compute_profile

router = APIRouter(prefix="/api/series", tags=["series"])


@router.get("")
def list_series(db: Session = Depends(get_db)):
    rows = db.query(Series).order_by(Series.series_id).all()
    return [
        {"series_id": r.series_id, "dataset": r.dataset, "frequency": r.frequency, "n_obs": r.n_obs}
        for r in rows
    ]


@router.get("/{series_id}/profile")
def get_profile(series_id: str, db: Session = Depends(get_db)):
    try:
        df, frequency = load_series(db, series_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Series not found")

    profile = get_or_compute_profile(db, df, series_id=series_id, frequency=frequency)
    return profile.model_dump()


@router.get("/{series_id}/config")
def get_config(series_id: str, db: Session = Depends(get_db)):
    row = db.get(SeriesFeatureConfig, series_id)
    return row.config if row is not None else {}


@router.post("/{series_id}/refit")
def refit(
    series_id: str,
    feature_config: dict[str, bool] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    try:
        df, frequency = load_series(db, series_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Series not found")

    profile = get_or_compute_profile(db, df, series_id=series_id, frequency=frequency)
    result = refit_series(df, series_id=series_id, frequency=frequency, toggle_state=feature_config, profile=profile)

    row = db.get(SeriesFeatureConfig, series_id)
    if row is None:
        db.add(SeriesFeatureConfig(series_id=series_id, config=result["feature_config"]))
    else:
        row.config = result["feature_config"]
    db.commit()

    return {
        "series_id": series_id,
        "metrics": result["metrics"],
        "forecast": result["forecast"],
        "feature_config": result["feature_config"],
    }
