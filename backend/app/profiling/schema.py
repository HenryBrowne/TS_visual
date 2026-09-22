from datetime import datetime

from pydantic import BaseModel


class MissingProfile(BaseModel):
    expected_n: int
    missing_count: int
    missing_pct: float


class SeasonalityProfile(BaseModel):
    detected: bool
    period: int | None
    strength: float


class TrendProfile(BaseModel):
    detected: bool
    slope: float
    strength: float


class StationarityProfile(BaseModel):
    adf_statistic: float
    adf_pvalue: float
    adf_stationary: bool
    kpss_statistic: float
    kpss_pvalue: float
    kpss_stationary: bool
    stationary: bool


class IntermittencyProfile(BaseModel):
    zero_pct: float
    adi: float
    cv2: float
    category: str
    is_intermittent: bool


class OutlierProfile(BaseModel):
    count: int
    pct: float
    timestamps: list[datetime]


class SeriesProfile(BaseModel):
    series_id: str
    frequency: str
    n_obs: int
    start_timestamp: datetime
    end_timestamp: datetime
    missing: MissingProfile
    seasonality: SeasonalityProfile
    trend: TrendProfile
    stationarity: StationarityProfile
    intermittency: IntermittencyProfile
    outliers: OutlierProfile
