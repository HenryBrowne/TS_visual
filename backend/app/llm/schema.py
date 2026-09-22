from typing import Literal

from pydantic import BaseModel, Field

FeatureType = Literal["calendar", "lag", "rolling_stat", "fourier", "holiday"]

ALLOWED_MODELS = ["ARIMA", "ETS", "Theta", "LightGBM", "XGBoost"]


class FeatureSuggestion(BaseModel):
    name: str
    feature_type: FeatureType
    description: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    holiday_country: str | None = None  # ISO 3166-1 alpha-2; only set when feature_type == "holiday"


class ModelRecommendation(BaseModel):
    name: str
    rationale: str


class SeriesDiagnostic(BaseModel):
    series_id: str
    narrative: str
    suggested_features: list[FeatureSuggestion]
    suggested_models: list[ModelRecommendation]


class BatchDiagnosticOutput(BaseModel):
    results: list[SeriesDiagnostic]


class ConfirmedFeatureSuggestion(FeatureSuggestion):
    holiday_confirmed: bool | None = None
    holiday_match_count: int | None = None


class ConfirmedSeriesDiagnostic(BaseModel):
    series_id: str
    narrative: str
    suggested_features: list[ConfirmedFeatureSuggestion]
    suggested_models: list[ModelRecommendation]
