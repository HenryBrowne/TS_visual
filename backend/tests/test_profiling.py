import numpy as np
import pandas as pd
import pytest

from app.profiling.diagnostics import (
    profile_intermittency,
    profile_missing,
    profile_outliers,
    profile_series,
    profile_stationarity,
)


def make_df(values: np.ndarray, start: str = "2020-01-01", freq: str = "D") -> pd.DataFrame:
    timestamps = pd.date_range(start=start, periods=len(values), freq=freq)
    return pd.DataFrame({"timestamp": timestamps, "value": values})


@pytest.fixture
def rng():
    return np.random.default_rng(42)


def test_white_noise_has_no_seasonality_or_trend_and_is_stationary(rng):
    values = rng.normal(loc=0.0, scale=1.0, size=800)
    df = make_df(values)

    profile = profile_series(df, series_id="white_noise", frequency="Daily")

    assert profile.seasonality.detected is False
    assert profile.trend.detected is False
    assert profile.stationarity.stationary is True


def test_weekly_seasonality_is_detected_with_correct_period(rng):
    t = np.arange(200)
    values = 10 * np.sin(2 * np.pi * t / 7) + rng.normal(scale=0.5, size=200)
    df = make_df(values)

    profile = profile_series(df, series_id="weekly_seasonal", frequency="Daily")

    assert profile.seasonality.detected is True
    assert profile.seasonality.period == 7
    assert profile.seasonality.strength > 0.3


def test_linear_trend_is_detected(rng):
    t = np.arange(200)
    values = 0.5 * t + rng.normal(scale=1.0, size=200)
    df = make_df(values)

    profile = profile_series(df, series_id="trending", frequency="Daily")

    assert profile.trend.detected is True
    assert profile.trend.slope > 0
    assert profile.stationarity.stationary is False


def test_intermittent_series_is_classified_correctly():
    values = np.zeros(200)
    values[::10] = 5.0  # constant-size demand every 10 steps -> low CV2, high ADI

    profile = profile_intermittency(values)

    assert profile.zero_pct == pytest.approx(0.9)
    assert profile.adi == pytest.approx(10.0)
    assert profile.is_intermittent is True
    assert profile.category in ("intermittent", "lumpy")


def test_smooth_series_is_not_intermittent(rng):
    values = rng.normal(loc=50, scale=2.0, size=200)  # always nonzero, low variance

    profile = profile_intermittency(values)

    assert profile.zero_pct == 0.0
    assert profile.is_intermittent is False
    assert profile.category == "smooth"


def test_missing_timestamps_are_counted():
    full_index = pd.date_range("2020-01-01", periods=100, freq="D")
    values = np.arange(100, dtype=float)

    # Drop every other day except the first and last, so the observed
    # min/max timestamps still span the full 100-day range.
    keep = np.ones(100, dtype=bool)
    keep[1:-1:2] = False
    df = pd.DataFrame({"timestamp": full_index[keep], "value": values[keep]})

    profile = profile_missing(df, frequency="Daily")

    assert profile.expected_n == 100
    assert profile.missing_count == 49
    assert profile.missing_pct == pytest.approx(0.49)


def test_outliers_are_detected_via_robust_zscore(rng):
    values = rng.normal(loc=0.0, scale=1.0, size=300)
    outlier_indices = [50, 150, 250]
    values[outlier_indices] += 50.0
    timestamps = pd.Series(pd.date_range("2020-01-01", periods=300, freq="D"))

    profile = profile_outliers(values, timestamps, resid=None)

    assert profile.count >= len(outlier_indices)
    detected_timestamps = set(profile.timestamps)
    for idx in outlier_indices:
        assert timestamps.iloc[idx] in detected_timestamps


def test_stationarity_flags_are_booleans(rng):
    values = rng.normal(size=200)
    profile = profile_stationarity(values)

    assert isinstance(profile.adf_stationary, bool)
    assert isinstance(profile.kpss_stationary, bool)
    assert isinstance(profile.stationary, bool)
