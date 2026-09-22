from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.features.catalog import build_feature_catalog
from app.features.models import SeriesFeatureConfig
from app.ingestion.loader import load_series
from app.ingestion.models import Series
from app.llm.cache import get_or_compute_diagnostic
from app.models.refit import apply_toggle_state, refit_series
from app.profiling.cache import get_cached_profile, get_or_compute_profile

router = APIRouter(prefix="/api/series", tags=["series"])


@router.get("")
def list_series(db: Session = Depends(get_db)):
    rows = db.query(Series).order_by(Series.series_id).all()
    result = []
    for r in rows:
        profile = get_cached_profile(db, r.series_id)
        result.append(
            {
                "series_id": r.series_id,
                "dataset": r.dataset,
                "frequency": r.frequency,
                "n_obs": r.n_obs,
                "profile_summary": None
                if profile is None
                else {
                    "trend_detected": profile.trend.detected,
                    "seasonality_detected": profile.seasonality.detected,
                    "seasonality_period": profile.seasonality.period,
                    "stationary": profile.stationarity.stationary,
                    "intermittency_category": profile.intermittency.category,
                },
            }
        )
    return result


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


@router.get("/{series_id}/features")
def get_features(series_id: str, db: Session = Depends(get_db)):
    """Everything the Workbench needs to render a series' feature-toggle
    panel: the mechanical catalog (with persisted or default enabled
    state) plus the LLM's narrative and its own suggested features/models
    as read-only diagnostic notes alongside it.
    """
    try:
        df, frequency = load_series(db, series_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Series not found")

    profile = get_or_compute_profile(db, df, series_id=series_id, frequency=frequency)

    config_row = db.get(SeriesFeatureConfig, series_id)
    toggle_state = config_row.config if config_row is not None else {}
    catalog = apply_toggle_state(build_feature_catalog(profile), toggle_state)

    diagnostic = get_or_compute_diagnostic(db, profile)

    return {
        "series_id": series_id,
        "catalog": [spec.model_dump() for spec in catalog],
        "narrative": diagnostic.narrative,
        "llm_suggested_features": [f.model_dump() for f in diagnostic.suggested_features],
        "llm_suggested_models": [m.model_dump() for m in diagnostic.suggested_models],
    }


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
        "actual": result["actual"],
        "best_model": result["best_model"],
        "deltas": result["deltas"],
    }
