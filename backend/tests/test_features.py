import numpy as np
import pandas as pd
import pytest

from app.features.catalog import build_feature_catalog
from app.features.deltas import compute_diagnostic_deltas
from app.features.engineering import apply_features
from app.features.schema import FeatureSpec
from app.profiling.diagnostics import profile_series


def make_df(values: np.ndarray, start: str = "2020-01-01", freq: str = "D") -> pd.DataFrame:
    timestamps = pd.date_range(start=start, periods=len(values), freq=freq)
    return pd.DataFrame({"timestamp": timestamps, "value": values})


def test_calendar_day_of_week_and_weekend():
    df = make_df(np.arange(14, dtype=float))  # 2020-01-01 is a Wednesday
    spec = FeatureSpec(name="calendar_day_of_week", feature_type="calendar", params={"component": "day_of_week"})
    weekend_spec = FeatureSpec(name="calendar_is_weekend", feature_type="calendar", params={"component": "is_weekend"})

    out = apply_features(df, [spec, weekend_spec])

    assert out["calendar_day_of_week"].iloc[0] == 2  # Wednesday == 2
    assert out.loc[out["calendar_day_of_week"].isin([5, 6]), "calendar_is_weekend"].eq(1).all()
    assert out.loc[~out["calendar_day_of_week"].isin([5, 6]), "calendar_is_weekend"].eq(0).all()


def test_time_index_is_ordinal():
    df = make_df(np.arange(10, dtype=float))
    spec = FeatureSpec(name="time_index", feature_type="calendar", params={"component": "time_index"})

    out = apply_features(df, [spec])

    assert list(out["time_index"]) == list(range(10))


def test_lag_feature_shifts_correctly():
    df = make_df(np.arange(10, dtype=float))
    spec = FeatureSpec(name="lag_1", feature_type="lag", params={"k": 1})

    out = apply_features(df, [spec])

    assert pd.isna(out["lag_1"].iloc[0])
    assert list(out["lag_1"].iloc[1:]) == list(range(9))


def test_rolling_mean_excludes_current_value():
    df = make_df(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    spec = FeatureSpec(name="rolling_mean_2", feature_type="rolling_stat", params={"window": 2, "stat": "mean"})

    out = apply_features(df, [spec])

    # rolling_mean_2 at index 2 should average values at index 0,1 (=1.5), not include index 2
    assert out["rolling_mean_2"].iloc[2] == pytest.approx(1.5)
    assert pd.isna(out["rolling_mean_2"].iloc[0])
    assert pd.isna(out["rolling_mean_2"].iloc[1])


def test_fourier_term_matches_known_angle():
    df = make_df(np.zeros(8))
    spec = FeatureSpec(
        name="fourier_sin_1_p4", feature_type="fourier", params={"order": 1, "period": 4, "func": "sin"}
    )

    out = apply_features(df, [spec])

    # t=0 -> sin(0)=0, t=1 -> sin(pi/2)=1, t=2 -> sin(pi)=0, t=3 -> sin(3pi/2)=-1
    expected = [0.0, 1.0, 0.0, -1.0, 0.0, 1.0, 0.0, -1.0]
    np.testing.assert_allclose(out["fourier_sin_1_p4"].to_numpy(), expected, atol=1e-9)


def test_holiday_indicator_flags_known_us_holiday():
    df = make_df(np.zeros(10), start="2019-12-30")  # spans New Year's Day 2020-01-01
    spec = FeatureSpec(name="holiday_US", feature_type="holiday", params={"country": "US"})

    out = apply_features(df, [spec])

    new_years = out[out["timestamp"] == "2020-01-01"]["holiday_US"].iloc[0]
    non_holiday = out[out["timestamp"] == "2019-12-31"]["holiday_US"].iloc[0]
    assert new_years == 1
    assert non_holiday == 0


def test_disabled_feature_is_not_applied():
    df = make_df(np.arange(10, dtype=float))
    spec = FeatureSpec(name="lag_1", feature_type="lag", params={"k": 1}, enabled=False)

    out = apply_features(df, [spec])

    assert "lag_1" not in out.columns


def test_catalog_includes_time_index_when_trend_detected(rng=np.random.default_rng(1)):
    values = 0.5 * np.arange(200) + rng.normal(scale=1.0, size=200)
    df = make_df(values)
    profile = profile_series(df, series_id="trend_series", frequency="Daily")

    catalog = build_feature_catalog(profile)

    names = [s.name for s in catalog]
    assert "time_index" in names
    assert "lag_1" in names


def test_catalog_includes_seasonal_terms_when_seasonality_detected(rng=np.random.default_rng(2)):
    t = np.arange(200)
    values = 10 * np.sin(2 * np.pi * t / 7) + rng.normal(scale=0.5, size=200)
    df = make_df(values)
    profile = profile_series(df, series_id="seasonal_series", frequency="Daily")

    catalog = build_feature_catalog(profile)

    names = [s.name for s in catalog]
    assert "lag_7" in names
    assert "fourier_sin_1_p7" in names
    assert "rolling_mean_7" in names


def test_diagnostic_deltas_show_trend_strength_dropping_after_features(rng=np.random.default_rng(3)):
    values = 0.5 * np.arange(200) + rng.normal(scale=1.0, size=200)
    df = make_df(values)
    profile_before = profile_series(df, series_id="trend_series", frequency="Daily")

    specs = build_feature_catalog(profile_before)
    deltas = compute_diagnostic_deltas(df, specs, profile_before, series_id="trend_series", frequency="Daily")

    assert deltas.trend_strength_before > 0.9
    assert deltas.trend_strength_after < deltas.trend_strength_before
    assert deltas.r_squared > 0.9


def test_diagnostic_deltas_with_no_enabled_features_still_returns_profile():
    df = make_df(np.random.default_rng(4).normal(size=100))
    profile_before = profile_series(df, series_id="noise_series", frequency="Daily")

    deltas = compute_diagnostic_deltas(df, [], profile_before, series_id="noise_series", frequency="Daily")

    assert deltas.r_squared == 0.0
