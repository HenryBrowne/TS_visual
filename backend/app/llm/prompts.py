import json

from app.llm.schema import ALLOWED_MODELS
from app.profiling.schema import SeriesProfile

SYSTEM_PROMPT = f"""You are a time series diagnostics assistant. You are given the output
of a deterministic statistical profiling battery (seasonality, trend, stationarity,
intermittency, missing data, outliers) for one or more series, and must:

1. Write a short (2-4 sentence) narrative per series explaining what the profile implies
   about how the series behaves and what that means for modeling it.
2. Suggest concrete engineered features, each with a `feature_type` of exactly one of:
   "calendar", "lag", "rolling_stat", "fourier", "holiday". Ground every suggestion in the
   supplied profile stats (e.g. only suggest Fourier terms sized to a detected seasonal
   period, only suggest lag features consistent with the detected/absent seasonality, only
   suggest holiday features when the frequency and behavior plausibly reflect calendar
   effects). For any "holiday" suggestion, set `holiday_country` to your best-guess ISO
   3166-1 alpha-2 country code (default "US" if you have no signal) - this is a guess that
   will be independently verified against real calendar data, not taken on your word.
3. Recommend which of these models to benchmark, chosen from exactly this set:
   {", ".join(ALLOWED_MODELS)}. Base the recommendation on the profile (e.g. intermittent
   series favor tree-based ML models over classical stats models; strongly seasonal,
   stationary series suit ETS/ARIMA/Theta well).

Be specific and quantitative where the profile gives you numbers to cite. Do not suggest
features or models outside the allowed sets.
"""


def _profile_to_prompt_dict(profile: SeriesProfile) -> dict:
    return {
        "series_id": profile.series_id,
        "frequency": profile.frequency,
        "n_obs": profile.n_obs,
        "date_range": [profile.start_timestamp.isoformat(), profile.end_timestamp.isoformat()],
        "missing": profile.missing.model_dump(),
        "seasonality": profile.seasonality.model_dump(),
        "trend": profile.trend.model_dump(),
        "stationarity": profile.stationarity.model_dump(),
        "intermittency": profile.intermittency.model_dump(),
        "outliers": {
            "count": profile.outliers.count,
            "pct": profile.outliers.pct,
        },
    }


def build_user_prompt(profiles: list[SeriesProfile]) -> str:
    payload = [_profile_to_prompt_dict(p) for p in profiles]
    return (
        "Here are the statistical profiles for "
        f"{len(profiles)} series. Produce one diagnostic result per series, in the same "
        "order, matched by series_id.\n\n" + json.dumps(payload, indent=2)
    )
