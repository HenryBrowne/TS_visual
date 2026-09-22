"""Orchestrates a single-series refit: split a holdout window, fit the
stats tier (univariate ARIMA/ETS/Theta) and the ML tier (LightGBM/XGBoost
on the enabled engineered feature columns), and score both against the
same holdout so they're directly comparable.
"""

import pandas as pd

from app.core.frequency import FREQ_TO_PANDAS
from app.features.catalog import build_feature_catalog
from app.features.deltas import compute_diagnostic_deltas
from app.features.engineering import apply_features
from app.features.schema import FeatureSpec
from app.models.metrics import compute_metrics
from app.models.ml import fit_and_forecast_ml
from app.models.stats import fit_and_forecast_stats
from app.profiling.schema import SeriesProfile

MIN_HORIZON = 7
MAX_HORIZON = 30
HORIZON_FRACTION = 0.1


def determine_horizon(n: int) -> int:
    return max(MIN_HORIZON, min(MAX_HORIZON, round(n * HORIZON_FRACTION)))


def apply_toggle_state(specs: list[FeatureSpec], toggle_state: dict[str, bool]) -> list[FeatureSpec]:
    return [spec.model_copy(update={"enabled": toggle_state.get(spec.name, spec.enabled)}) for spec in specs]


def refit_series(
    df: pd.DataFrame, series_id: str, frequency: str, toggle_state: dict[str, bool], profile: SeriesProfile
) -> dict:
    df = df.sort_values("timestamp").reset_index(drop=True)

    specs = apply_toggle_state(build_feature_catalog(profile), toggle_state)

    horizon = determine_horizon(len(df))
    train_df = df.iloc[:-horizon]
    test_df = df.iloc[-horizon:]
    actual = test_df["value"].to_numpy()

    sf_train = pd.DataFrame({"unique_id": series_id, "ds": train_df["timestamp"], "y": train_df["value"]})
    stats_forecasts = fit_and_forecast_stats(sf_train, horizon=horizon, freq=FREQ_TO_PANDAS[frequency])

    enabled_specs = [s for s in specs if s.enabled]
    feature_cols = [s.name for s in enabled_specs]
    ml_predictions: dict = {}
    if feature_cols:
        engineered = apply_features(df, enabled_specs)
        train_eng = engineered.iloc[:-horizon].dropna(subset=feature_cols)
        test_eng = engineered.iloc[-horizon:]
        ml_predictions = fit_and_forecast_ml(train_eng, test_eng, feature_cols)

    timestamps = test_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S").tolist()

    metrics = {}
    forecast = {}
    for name in ("ARIMA", "ETS", "Theta"):
        pred = stats_forecasts[name].to_numpy()
        metrics[name] = compute_metrics(actual, pred)
        forecast[name] = [{"timestamp": ts, "value": float(v)} for ts, v in zip(timestamps, pred)]

    for name, pred in ml_predictions.items():
        metrics[name] = compute_metrics(actual, pred)
        forecast[name] = [{"timestamp": ts, "value": float(v)} for ts, v in zip(timestamps, pred)]

    best_model = min(metrics, key=lambda name: metrics[name]["smape"])
    deltas = compute_diagnostic_deltas(df, specs, profile, series_id=series_id, frequency=frequency)

    all_timestamps = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S").tolist()
    actual_series = [{"timestamp": ts, "value": float(v)} for ts, v in zip(all_timestamps, df["value"])]

    return {
        "profile": profile,
        "metrics": metrics,
        "forecast": forecast,
        "feature_config": {s.name: s.enabled for s in specs},
        "actual": actual_series,
        "best_model": best_model,
        "deltas": deltas.model_dump(),
    }
