"""Cross-checks LLM-suggested holiday features against the `holidays` package
before they are surfaced as confirmed, per the project's requirement that
holiday suggestions aren't just taken on the LLM's word.
"""

from datetime import datetime

import holidays as holidays_lib

from app.llm.schema import ConfirmedFeatureSuggestion, FeatureSuggestion

DEFAULT_HOLIDAY_COUNTRY = "US"


def cross_check_holiday_feature(
    feature: FeatureSuggestion, start: datetime, end: datetime
) -> ConfirmedFeatureSuggestion:
    if feature.feature_type != "holiday":
        return ConfirmedFeatureSuggestion(
            **feature.model_dump(), holiday_confirmed=None, holiday_match_count=None
        )

    country = feature.holiday_country or DEFAULT_HOLIDAY_COUNTRY
    try:
        calendar = holidays_lib.country_holidays(country, years=range(start.year, end.year + 1))
        match_count = sum(1 for d in calendar if start.date() <= d <= end.date())
        confirmed = match_count > 0
    except NotImplementedError:
        match_count = 0
        confirmed = False

    return ConfirmedFeatureSuggestion(
        **feature.model_dump(exclude={"holiday_country"}),
        holiday_country=country,
        holiday_confirmed=confirmed,
        holiday_match_count=match_count,
    )


def cross_check_features(
    features: list[FeatureSuggestion], start: datetime, end: datetime
) -> list[ConfirmedFeatureSuggestion]:
    return [cross_check_holiday_feature(f, start, end) for f in features]
