"""Measures whether enabled features actually explain the structure they
were meant to: fits a linear regression of value on the enabled feature
columns, re-profiles the residuals with the same diagnostics battery used
on the raw series, and diffs the two profiles. A feature set that captures
the trend/seasonality should show trend/seasonality strength collapsing
toward zero in the "after" profile.
"""

import pandas as pd
from sklearn.linear_model import LinearRegression

from app.features.engineering import apply_features
from app.features.schema import DiagnosticDeltas, FeatureSpec
from app.profiling.diagnostics import profile_series
from app.profiling.schema import SeriesProfile


def compute_residuals(df: pd.DataFrame, specs: list[FeatureSpec]) -> tuple[pd.DataFrame, float]:
    enabled_specs = [s for s in specs if s.enabled]
    feature_cols = [s.name for s in enabled_specs]

    if not feature_cols:
        residual_df = df[["timestamp", "value"]].copy()
        residual_df["value"] = residual_df["value"] - residual_df["value"].mean()
        return residual_df, 0.0

    engineered = apply_features(df, enabled_specs)
    valid = engineered.dropna(subset=feature_cols + ["value"])

    X = valid[feature_cols].to_numpy(dtype=float)
    y = valid["value"].to_numpy(dtype=float)

    model = LinearRegression()
    model.fit(X, y)
    residuals = y - model.predict(X)
    r_squared = float(model.score(X, y))

    residual_df = pd.DataFrame({"timestamp": valid["timestamp"].to_numpy(), "value": residuals})
    return residual_df, r_squared


def compute_diagnostic_deltas(
    df: pd.DataFrame, specs: list[FeatureSpec], profile_before: SeriesProfile, series_id: str, frequency: str
) -> DiagnosticDeltas:
    residual_df, r_squared = compute_residuals(df, specs)
    profile_after = profile_series(residual_df, series_id=f"{series_id}__residual", frequency=frequency)

    return DiagnosticDeltas(
        r_squared=r_squared,
        trend_strength_before=profile_before.trend.strength,
        trend_strength_after=profile_after.trend.strength,
        seasonality_strength_before=profile_before.seasonality.strength,
        seasonality_strength_after=profile_after.seasonality.strength,
        stationary_before=profile_before.stationarity.stationary,
        stationary_after=profile_after.stationarity.stationary,
        outlier_count_before=profile_before.outliers.count,
        outlier_count_after=profile_after.outliers.count,
    )
