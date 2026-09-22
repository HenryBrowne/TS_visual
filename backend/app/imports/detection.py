"""Heuristic column-role and format detection for the CSV import wizard's
step 1. Operates on a bounded sample (DETECT_SAMPLE_ROWS), not the full
file, so the wizard feels instant -- the full file is only read once, in
the async ingest-and-profile job.
"""

import re

import pandas as pd

DETECT_SAMPLE_ROWS = 500

TIMESTAMP_NAME_PATTERN = re.compile(r"^(date|timestamp|ts|time|ds)$", re.IGNORECASE)
SERIES_ID_NAME_PATTERN = re.compile(
    # Exact-name matches, or anything ending in "_id"/"id" (store_id,
    # product_id, city_id, ...), which is by far the most common shape.
    r"^(series[_ ]?id|series|item|product|sku|name|.*[_ ]?id)$",
    re.IGNORECASE,
)

# A column is treated as a plausible timestamp/value column when at least
# this fraction of its sampled values parse as such. Easy to retune once
# real user CSVs surface edge cases.
MIN_TIMESTAMP_PARSE_FRACTION = 0.8
MIN_VALUE_NUMERIC_FRACTION = 0.5


def _numeric_fraction(series: pd.Series) -> float:
    if len(series) == 0:
        return 0.0
    return pd.to_numeric(series, errors="coerce").notna().mean()


def _timestamp_fraction(series: pd.Series) -> float:
    if len(series) == 0:
        return 0.0
    return pd.to_datetime(series, errors="coerce").notna().mean()


def detect_timestamp_column(df: pd.DataFrame) -> str | None:
    name_matches = [c for c in df.columns if TIMESTAMP_NAME_PATTERN.match(c.strip())]
    if name_matches:
        return name_matches[0]

    scores = {c: _timestamp_fraction(df[c]) for c in df.columns}
    if not scores:
        return None
    best_col, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_col if best_score >= MIN_TIMESTAMP_PARSE_FRACTION else None


def detect_series_id_column(df: pd.DataFrame, exclude: set[str]) -> str | None:
    candidates = [c for c in df.columns if c not in exclude]
    name_matches = [c for c in candidates if SERIES_ID_NAME_PATTERN.match(c.strip())]
    return name_matches[0] if name_matches else None


def detect_value_column(df: pd.DataFrame, exclude: set[str]) -> str | None:
    candidates = [c for c in df.columns if c not in exclude]
    if not candidates:
        return None
    scores = {c: _numeric_fraction(df[c]) for c in candidates}
    best_col, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_col if best_score >= MIN_VALUE_NUMERIC_FRACTION else None


def detect_format_and_mapping(df: pd.DataFrame) -> dict:
    """Returns {format, column_mapping, wide_melt_preview}. column_mapping
    maps every column in df to one of: timestamp, series_id, value, ignore.
    """
    ts_col = detect_timestamp_column(df)
    excluded = {ts_col} if ts_col else set()

    series_id_col = detect_series_id_column(df, excluded)

    if series_id_col:
        value_col = detect_value_column(df, excluded | {series_id_col})
        mapping = {c: "ignore" for c in df.columns}
        if ts_col:
            mapping[ts_col] = "timestamp"
        mapping[series_id_col] = "series_id"
        if value_col:
            mapping[value_col] = "value"
        return {"format": "long", "column_mapping": mapping, "wide_melt_preview": None}

    numeric_candidates = [c for c in df.columns if c not in excluded and _numeric_fraction(df[c]) >= MIN_VALUE_NUMERIC_FRACTION]
    if ts_col and len(numeric_candidates) >= 2:
        mapping = {c: "ignore" for c in df.columns}
        mapping[ts_col] = "timestamp"
        for c in numeric_candidates:
            mapping[c] = "value"
        return {
            "format": "wide",
            "column_mapping": mapping,
            "wide_melt_preview": [{"column": c, "becomes_series": c} for c in numeric_candidates],
        }

    # No series-id column and not enough numeric columns for wide format:
    # treat as long with a single implied series.
    value_col = detect_value_column(df, excluded)
    mapping = {c: "ignore" for c in df.columns}
    if ts_col:
        mapping[ts_col] = "timestamp"
    if value_col:
        mapping[value_col] = "value"
    return {"format": "long", "column_mapping": mapping, "wide_melt_preview": None}
