import json
from datetime import datetime

from app.llm.holiday_check import cross_check_features, cross_check_holiday_feature
from app.llm.prompts import build_user_prompt
from app.llm.schema import FeatureSuggestion
from app.profiling.diagnostics import profile_series
from app.profiling.schema import SeriesProfile

import numpy as np
import pandas as pd


def make_holiday_feature(country: str | None) -> FeatureSuggestion:
    return FeatureSuggestion(
        name="us_holiday_indicator",
        feature_type="holiday",
        description="Binary indicator for US federal holidays",
        rationale="Daily series may show demand shifts around holidays",
        confidence=0.7,
        holiday_country=country,
    )


def test_real_us_holiday_in_range_is_confirmed():
    feature = make_holiday_feature("US")
    start = datetime(2020, 1, 1)
    end = datetime(2020, 12, 31)

    confirmed = cross_check_holiday_feature(feature, start, end)

    assert confirmed.holiday_confirmed is True
    assert confirmed.holiday_match_count is not None
    assert confirmed.holiday_match_count > 0
    assert confirmed.holiday_country == "US"


def test_invalid_country_code_is_not_confirmed():
    feature = make_holiday_feature("ZZ")
    start = datetime(2020, 1, 1)
    end = datetime(2020, 12, 31)

    confirmed = cross_check_holiday_feature(feature, start, end)

    assert confirmed.holiday_confirmed is False
    assert confirmed.holiday_match_count == 0


def test_missing_country_defaults_to_us():
    feature = make_holiday_feature(None)
    start = datetime(2020, 1, 1)
    end = datetime(2020, 12, 31)

    confirmed = cross_check_holiday_feature(feature, start, end)

    assert confirmed.holiday_country == "US"
    assert confirmed.holiday_confirmed is True


def test_non_holiday_feature_is_passed_through_unchecked():
    feature = FeatureSuggestion(
        name="lag_7",
        feature_type="lag",
        description="Value 7 steps ago",
        rationale="Weekly seasonality detected",
        confidence=0.9,
    )
    confirmed = cross_check_holiday_feature(feature, datetime(2020, 1, 1), datetime(2020, 12, 31))

    assert confirmed.holiday_confirmed is None
    assert confirmed.holiday_match_count is None


def test_cross_check_features_preserves_order_and_count():
    features = [
        make_holiday_feature("US"),
        FeatureSuggestion(
            name="rolling_mean_7",
            feature_type="rolling_stat",
            description="7-day rolling mean",
            rationale="Smooths daily noise",
            confidence=0.6,
        ),
    ]
    confirmed = cross_check_features(features, datetime(2020, 1, 1), datetime(2020, 12, 31))

    assert len(confirmed) == 2
    assert confirmed[0].name == "us_holiday_indicator"
    assert confirmed[1].name == "rolling_mean_7"


def test_build_user_prompt_includes_series_id_and_is_valid_json_payload():
    rng = np.random.default_rng(0)
    values = rng.normal(size=100)
    timestamps = pd.date_range("2020-01-01", periods=100, freq="D")
    df = pd.DataFrame({"timestamp": timestamps, "value": values})
    profile = profile_series(df, series_id="test_series", frequency="Daily")

    prompt = build_user_prompt([profile])

    assert "test_series" in prompt
    json_start = prompt.index("[")
    payload = json.loads(prompt[json_start:])
    assert payload[0]["series_id"] == "test_series"
    assert payload[0]["frequency"] == "Daily"
