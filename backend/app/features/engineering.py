import holidays as holidays_lib
import numpy as np
import pandas as pd

from app.features.schema import FeatureSpec


def _calendar_component(df: pd.DataFrame, component: str) -> pd.Series:
    ts = df["timestamp"]
    if component == "day_of_week":
        return ts.dt.dayofweek
    if component == "is_weekend":
        return (ts.dt.dayofweek >= 5).astype(int)
    if component == "month":
        return ts.dt.month
    if component == "quarter":
        return ts.dt.quarter
    if component == "hour_of_day":
        return ts.dt.hour
    if component == "time_index":
        return pd.Series(np.arange(len(df)), index=df.index)
    raise ValueError(f"Unknown calendar component: {component}")


def _rolling_stat(df: pd.DataFrame, window: int, stat: str) -> pd.Series:
    shifted = df["value"].shift(1)  # exclude the current value to avoid leakage
    if stat == "mean":
        return shifted.rolling(window).mean()
    if stat == "std":
        return shifted.rolling(window).std()
    raise ValueError(f"Unknown rolling stat: {stat}")


def _fourier_term(df: pd.DataFrame, order: int, period: int, func: str) -> pd.Series:
    t = np.arange(len(df))
    angle = 2 * np.pi * order * t / period
    values = np.sin(angle) if func == "sin" else np.cos(angle)
    return pd.Series(values, index=df.index)


def _holiday_indicator(df: pd.DataFrame, country: str) -> pd.Series:
    years = range(df["timestamp"].min().year, df["timestamp"].max().year + 1)
    calendar = holidays_lib.country_holidays(country, years=years)
    return df["timestamp"].dt.date.isin(calendar).astype(int)


def _build_column(df: pd.DataFrame, spec: FeatureSpec) -> pd.Series:
    if spec.feature_type == "calendar":
        return _calendar_component(df, spec.params["component"])
    if spec.feature_type == "lag":
        return df["value"].shift(spec.params["k"])
    if spec.feature_type == "rolling_stat":
        return _rolling_stat(df, spec.params["window"], spec.params["stat"])
    if spec.feature_type == "fourier":
        return _fourier_term(df, spec.params["order"], spec.params["period"], spec.params["func"])
    if spec.feature_type == "holiday":
        return _holiday_indicator(df, spec.params["country"])
    raise ValueError(f"Unknown feature_type: {spec.feature_type}")


def apply_features(df: pd.DataFrame, specs: list[FeatureSpec]) -> pd.DataFrame:
    out = df.copy()
    for spec in specs:
        if not spec.enabled:
            continue
        out[spec.name] = _build_column(df, spec)
    return out
