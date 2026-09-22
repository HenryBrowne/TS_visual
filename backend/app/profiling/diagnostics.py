"""Deterministic statistical profiling battery: seasonality (STL strength),
trend (linear regression), stationarity (ADF/KPSS), intermittency
(Syntetos-Boylan classification), missing values, and outliers (robust
z-score on MAD).
"""

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import adfuller, kpss

from app.core.frequency import FREQ_TO_PANDAS
from app.profiling.schema import (
    IntermittencyProfile,
    MissingProfile,
    OutlierProfile,
    SeasonalityProfile,
    SeriesProfile,
    StationarityProfile,
    TrendProfile,
)

CANDIDATE_PERIODS = {
    "Yearly": [],
    "Quarterly": [4],
    "Monthly": [12],
    "Weekly": [52],
    "Daily": [7, 30, 365],
    "Hourly": [24, 168],
}

SEASONALITY_STRENGTH_THRESHOLD = 0.3
MIN_CYCLES_FOR_SEASONALITY = 4
OUTLIER_Z_THRESHOLD = 3.5
INTERMITTENCY_ADI_THRESHOLD = 1.32
INTERMITTENCY_CV2_THRESHOLD = 0.49


def profile_missing(df: pd.DataFrame, frequency: str) -> MissingProfile:
    freq = FREQ_TO_PANDAS[frequency]
    indexed = df.set_index("timestamp")["value"]
    full_index = pd.date_range(indexed.index.min(), indexed.index.max(), freq=freq)
    reindexed = indexed.reindex(full_index)

    expected_n = len(full_index)
    missing_count = int(reindexed.isna().sum())
    return MissingProfile(
        expected_n=expected_n,
        missing_count=missing_count,
        missing_pct=missing_count / expected_n if expected_n else 0.0,
    )


def _stl_strengths(clean_values: np.ndarray, period: int):
    result = STL(clean_values, period=period, robust=True).fit()
    resid_var = np.var(result.resid)

    seasonal_total_var = np.var(result.resid + result.seasonal)
    seasonal_strength = max(0.0, 1 - resid_var / seasonal_total_var) if seasonal_total_var > 0 else 0.0

    trend_total_var = np.var(result.resid + result.trend)
    trend_strength = max(0.0, 1 - resid_var / trend_total_var) if trend_total_var > 0 else 0.0

    return seasonal_strength, trend_strength, result


def profile_seasonality_and_trend(values: np.ndarray, frequency: str):
    clean_values = values[~np.isnan(values)]

    candidates = CANDIDATE_PERIODS.get(frequency, [])
    best = None  # (period, seasonal_strength, trend_strength, stl_result)
    for period in candidates:
        # STL's seasonal strength is unreliable (prone to overfitting noise)
        # without several full cycles of data to estimate it from.
        if len(clean_values) < MIN_CYCLES_FOR_SEASONALITY * period:
            continue
        seasonal_strength, trend_strength, result = _stl_strengths(clean_values, period)
        if best is None or seasonal_strength > best[1]:
            best = (period, seasonal_strength, trend_strength, result)

    resid = None
    if best is not None and best[1] >= SEASONALITY_STRENGTH_THRESHOLD:
        period, seasonal_strength, _, result = best
        seasonality = SeasonalityProfile(detected=True, period=period, strength=round(seasonal_strength, 4))
        resid = result.resid
    else:
        seasonality = SeasonalityProfile(
            detected=False, period=None, strength=round(best[1], 4) if best else 0.0
        )

    x = np.arange(len(clean_values))
    if len(clean_values) >= 2:
        slope, _intercept, r_value, p_value, _std_err = stats.linregress(x, clean_values)
        trend = TrendProfile(detected=bool(p_value < 0.05), slope=float(slope), strength=float(r_value**2))
    else:
        trend = TrendProfile(detected=False, slope=0.0, strength=0.0)

    return seasonality, trend, resid


def profile_stationarity(values: np.ndarray) -> StationarityProfile:
    clean_values = values[~np.isnan(values)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        adf_stat, adf_pvalue, *_ = adfuller(clean_values, autolag="AIC")
        kpss_stat, kpss_pvalue, *_ = kpss(clean_values, regression="c", nlags="auto")

    adf_stationary = adf_pvalue < 0.05
    kpss_stationary = kpss_pvalue >= 0.05
    return StationarityProfile(
        adf_statistic=float(adf_stat),
        adf_pvalue=float(adf_pvalue),
        adf_stationary=bool(adf_stationary),
        kpss_statistic=float(kpss_stat),
        kpss_pvalue=float(kpss_pvalue),
        kpss_stationary=bool(kpss_stationary),
        stationary=bool(adf_stationary and kpss_stationary),
    )


def profile_intermittency(values: np.ndarray) -> IntermittencyProfile:
    clean_values = values[~np.isnan(values)]
    zero_pct = float(np.mean(clean_values == 0)) if len(clean_values) else 0.0

    nonzero = clean_values[clean_values != 0]
    if len(nonzero) == 0:
        adi = float("inf")
        cv2 = 0.0
    else:
        adi = len(clean_values) / len(nonzero)
        mean_demand = np.mean(nonzero)
        cv2 = float((np.std(nonzero) / mean_demand) ** 2) if mean_demand != 0 else 0.0

    if adi < INTERMITTENCY_ADI_THRESHOLD and cv2 < INTERMITTENCY_CV2_THRESHOLD:
        category = "smooth"
    elif adi >= INTERMITTENCY_ADI_THRESHOLD and cv2 < INTERMITTENCY_CV2_THRESHOLD:
        category = "intermittent"
    elif adi < INTERMITTENCY_ADI_THRESHOLD and cv2 >= INTERMITTENCY_CV2_THRESHOLD:
        category = "erratic"
    else:
        category = "lumpy"

    return IntermittencyProfile(
        zero_pct=zero_pct,
        adi=float(adi),
        cv2=cv2,
        category=category,
        is_intermittent=category in ("intermittent", "lumpy"),
    )


def profile_outliers(values: np.ndarray, timestamps: pd.Series, resid: np.ndarray | None) -> OutlierProfile:
    if resid is not None:
        signal = np.full(len(values), np.nan)
        signal[~np.isnan(values)] = resid
    else:
        signal = values

    clean_mask = ~np.isnan(signal)
    if not clean_mask.any():
        return OutlierProfile(count=0, pct=0.0, timestamps=[])

    median = np.median(signal[clean_mask])
    mad = np.median(np.abs(signal[clean_mask] - median))

    z = np.zeros_like(signal)
    if mad > 0:
        z[clean_mask] = 0.6745 * (signal[clean_mask] - median) / mad

    outlier_mask = clean_mask & (np.abs(z) > OUTLIER_Z_THRESHOLD)
    count = int(outlier_mask.sum())
    return OutlierProfile(
        count=count,
        pct=float(count / len(values)) if len(values) else 0.0,
        timestamps=list(pd.to_datetime(pd.Series(timestamps)[outlier_mask])),
    )


def profile_series(df: pd.DataFrame, series_id: str, frequency: str) -> SeriesProfile:
    df = df.sort_values("timestamp").reset_index(drop=True)
    values = df["value"].to_numpy(dtype=float)

    missing = profile_missing(df, frequency)
    seasonality, trend, resid = profile_seasonality_and_trend(values, frequency)
    stationarity = profile_stationarity(values)
    intermittency = profile_intermittency(values)
    outliers = profile_outliers(values, df["timestamp"], resid)

    return SeriesProfile(
        series_id=series_id,
        frequency=frequency,
        n_obs=len(df),
        start_timestamp=df["timestamp"].min(),
        end_timestamp=df["timestamp"].max(),
        missing=missing,
        seasonality=seasonality,
        trend=trend,
        stationarity=stationarity,
        intermittency=intermittency,
        outliers=outliers,
    )
