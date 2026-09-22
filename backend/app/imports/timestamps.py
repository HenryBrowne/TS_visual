"""Timestamp parsing for the import wizard. Handles the common case
(real date/datetime strings, via pandas) plus one important special
case: decimal-year encoding (e.g. R's `time()` on a monthly `ts` object
-- 1949, 1949.0833, 1949.1667, ...), which pandas' default numeric-to-
datetime path misinterprets as nanoseconds since epoch, collapsing an
entire column into near-identical timestamps. Shared by the wizard's
validate step and the ingest-and-profile job so preview and commit
parse identically.
"""

import numpy as np
import pandas as pd

MIN_PLAUSIBLE_YEAR = 1500
MAX_PLAUSIBLE_YEAR = 2200
DECIMAL_YEAR_MATCH_THRESHOLD = 0.9


def _looks_like_decimal_year(raw: pd.Series) -> bool:
    if len(raw) == 0:
        return False
    numeric = pd.to_numeric(raw, errors="coerce")
    if numeric.notna().mean() < DECIMAL_YEAR_MATCH_THRESHOLD:
        return False
    in_plausible_range = numeric.between(MIN_PLAUSIBLE_YEAR, MAX_PLAUSIBLE_YEAR)
    return in_plausible_range.mean() > DECIMAL_YEAR_MATCH_THRESHOLD


def _parse_decimal_year(raw: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(raw, errors="coerce")
    valid = numeric.notna()

    year = np.floor(numeric[valid]).astype(int)
    frac = numeric[valid] - year
    # Sub-year granularity is almost always monthly for this format
    # (R's ts() with frequency=12); round the fraction to the nearest
    # month rather than assuming daily precision.
    month = (frac * 12).round().astype(int).clip(0, 11) + 1

    result = pd.Series(pd.NaT, index=raw.index, dtype="datetime64[ns]")
    result.loc[valid] = pd.to_datetime({"year": year, "month": month, "day": 1}).values
    return result


def parse_timestamps(raw: pd.Series) -> pd.Series:
    if _looks_like_decimal_year(raw):
        return _parse_decimal_year(raw)
    return pd.to_datetime(raw, errors="coerce")
