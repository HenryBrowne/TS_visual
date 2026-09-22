"""Builds a candidate feature catalog grounded in a series' statistical
profile: calendar components appropriate to its frequency, an explicit
time index when a trend was detected, autoregressive lags and rolling
stats sized to the detected seasonal period (or a frequency-based
default), Fourier terms at the detected period, and an optional holiday
indicator when a diagnostic has confirmed one.
"""

from app.features.schema import FeatureSpec
from app.profiling.schema import SeriesProfile

ROLLING_WINDOW_DEFAULTS = {
    "Daily": 7,
    "Weekly": 4,
    "Monthly": 12,
    "Quarterly": 4,
    "Yearly": None,
    "Hourly": 24,
}

CALENDAR_COMPONENTS_BY_FREQUENCY = {
    "Daily": ["day_of_week", "is_weekend"],
    "Weekly": ["month"],
    "Monthly": ["month"],
    "Quarterly": ["quarter"],
    "Hourly": ["hour_of_day", "day_of_week"],
    "Yearly": [],
}

FOURIER_ORDERS = (1, 2, 3)


def build_feature_catalog(profile: SeriesProfile, holiday_country: str | None = None) -> list[FeatureSpec]:
    specs: list[FeatureSpec] = []

    for component in CALENDAR_COMPONENTS_BY_FREQUENCY.get(profile.frequency, []):
        specs.append(
            FeatureSpec(name=f"calendar_{component}", feature_type="calendar", params={"component": component})
        )

    if profile.trend.detected:
        specs.append(FeatureSpec(name="time_index", feature_type="calendar", params={"component": "time_index"}))

    specs.append(FeatureSpec(name="lag_1", feature_type="lag", params={"k": 1}))
    if profile.seasonality.detected and profile.seasonality.period:
        period = profile.seasonality.period
        specs.append(FeatureSpec(name=f"lag_{period}", feature_type="lag", params={"k": period}))

    window = profile.seasonality.period if profile.seasonality.detected else ROLLING_WINDOW_DEFAULTS.get(profile.frequency)
    if window and window > 1:
        specs.append(
            FeatureSpec(
                name=f"rolling_mean_{window}", feature_type="rolling_stat", params={"window": window, "stat": "mean"}
            )
        )
        specs.append(
            FeatureSpec(
                name=f"rolling_std_{window}", feature_type="rolling_stat", params={"window": window, "stat": "std"}
            )
        )

    if profile.seasonality.detected and profile.seasonality.period:
        period = profile.seasonality.period
        for order in FOURIER_ORDERS:
            specs.append(
                FeatureSpec(
                    name=f"fourier_sin_{order}_p{period}",
                    feature_type="fourier",
                    params={"order": order, "period": period, "func": "sin"},
                )
            )
            specs.append(
                FeatureSpec(
                    name=f"fourier_cos_{order}_p{period}",
                    feature_type="fourier",
                    params={"order": order, "period": period, "func": "cos"},
                )
            )

    if holiday_country:
        specs.append(
            FeatureSpec(
                name=f"holiday_{holiday_country}", feature_type="holiday", params={"country": holiday_country}
            )
        )

    return specs
