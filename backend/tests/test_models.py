import numpy as np
import pandas as pd
import pytest

from app.features.schema import FeatureSpec
from app.models.metrics import compute_metrics
from app.models.refit import apply_toggle_state, determine_horizon, refit_series
from app.profiling.diagnostics import profile_series


def test_compute_metrics_known_values():
    actual = np.array([10.0, 20.0, 30.0])
    predicted = np.array([12.0, 18.0, 33.0])

    metrics = compute_metrics(actual, predicted)

    assert metrics["mae"] == pytest.approx((2 + 2 + 3) / 3)
    assert metrics["rmse"] == pytest.approx(np.sqrt((4 + 4 + 9) / 3))
    assert metrics["smape"] > 0


def test_compute_metrics_handles_zero_actual_and_predicted():
    actual = np.array([0.0, 5.0])
    predicted = np.array([0.0, 5.0])

    metrics = compute_metrics(actual, predicted)

    assert metrics["mae"] == 0.0
    assert metrics["smape"] == 0.0


@pytest.mark.parametrize(
    "n,expected",
    [
        (50, 7),  # 10% of 50 = 5, clamped up to MIN_HORIZON=7
        (100, 10),
        (500, 30),  # 10% of 500 = 50, clamped down to MAX_HORIZON=30
    ],
)
def test_determine_horizon_clamps_correctly(n, expected):
    assert determine_horizon(n) == expected


def test_apply_toggle_state_overrides_matching_names_only():
    specs = [
        FeatureSpec(name="lag_1", feature_type="lag", params={"k": 1}, enabled=True),
        FeatureSpec(name="lag_7", feature_type="lag", params={"k": 7}, enabled=True),
    ]

    updated = apply_toggle_state(specs, {"lag_1": False})

    by_name = {s.name: s.enabled for s in updated}
    assert by_name["lag_1"] is False
    assert by_name["lag_7"] is True


def test_refit_series_end_to_end_on_synthetic_trend(rng=np.random.default_rng(7)):
    values = 0.5 * np.arange(150) + rng.normal(scale=1.0, size=150)
    timestamps = pd.date_range("2020-01-01", periods=150, freq="D")
    df = pd.DataFrame({"timestamp": timestamps, "value": values})
    profile = profile_series(df, series_id="synthetic_trend", frequency="Daily")

    result = refit_series(df, series_id="synthetic_trend", frequency="Daily", toggle_state={}, profile=profile)

    horizon = determine_horizon(150)
    for model_name in ("ARIMA", "ETS", "Theta", "LightGBM", "XGBoost"):
        assert model_name in result["metrics"]
        assert result["metrics"][model_name]["mae"] >= 0
        assert len(result["forecast"][model_name]) == horizon

    assert result["feature_config"]["lag_1"] is True


def test_refit_series_respects_disabled_features(rng=np.random.default_rng(8)):
    values = 0.5 * np.arange(150) + rng.normal(scale=1.0, size=150)
    timestamps = pd.date_range("2020-01-01", periods=150, freq="D")
    df = pd.DataFrame({"timestamp": timestamps, "value": values})
    profile = profile_series(df, series_id="synthetic_trend2", frequency="Daily")

    result = refit_series(
        df, series_id="synthetic_trend2", frequency="Daily", toggle_state={"lag_1": False}, profile=profile
    )

    assert result["feature_config"]["lag_1"] is False
