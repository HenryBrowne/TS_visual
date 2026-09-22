from pydantic import BaseModel, Field

from app.llm.schema import FeatureType


class FeatureSpec(BaseModel):
    name: str
    feature_type: FeatureType
    params: dict = Field(default_factory=dict)
    enabled: bool = True


class DiagnosticDeltas(BaseModel):
    r_squared: float
    trend_strength_before: float
    trend_strength_after: float
    seasonality_strength_before: float
    seasonality_strength_after: float
    stationary_before: bool
    stationary_after: bool
    outlier_count_before: int
    outlier_count_after: int
