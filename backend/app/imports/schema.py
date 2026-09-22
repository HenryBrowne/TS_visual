from typing import Literal

from pydantic import BaseModel

ColumnRole = Literal["timestamp", "series_id", "value", "exogenous", "ignore"]
DataFormat = Literal["long", "wide"]


class DetectResponse(BaseModel):
    upload_id: str
    format: DataFormat
    column_mapping: dict[str, ColumnRole]
    wide_melt_preview: list[dict] | None
    preview_rows: list[dict]
    row_count_sampled: int


class ValidateRequest(BaseModel):
    upload_id: str
    format: DataFormat
    column_mapping: dict[str, ColumnRole]


class IngestRequest(BaseModel):
    upload_id: str
    format: DataFormat
    column_mapping: dict[str, ColumnRole]
    name: str


class ValidateResponse(BaseModel):
    row_count: int
    valid_row_count: int
    series_count: int
    detected_frequency: str | None
    errors: list[str]
    warnings: list[str]
    can_proceed: bool
    preview_rows: list[dict]
