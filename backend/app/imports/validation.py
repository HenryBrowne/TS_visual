"""Validates a (possibly user-corrected) column mapping against a sample
of the uploaded CSV. Split into blocking errors (disable "Next") and
warnings (shown, but don't block) per the wizard's step 3.

All thresholds below are a starting point, not fixed -- easy to retune
once real user CSVs surface edge cases.
"""

import pandas as pd

VALIDATE_SAMPLE_ROWS = 5000
BLOCKING_NON_NUMERIC_VALUE_FRACTION = 0.20
MIN_TIMESTAMP_PARSE_FRACTION = 0.5


def melt_wide_to_long(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    ts_col = next((c for c, role in mapping.items() if role == "timestamp"), None)
    value_cols = [c for c, role in mapping.items() if role == "value"]
    # pandas' melt() raises if value_name collides with any existing column
    # name (e.g. a wide-format CSV that happens to have a column literally
    # called "value") -- melt into a name that can't collide, then rename.
    long_df = df.melt(id_vars=[ts_col], value_vars=value_cols, var_name="series_id", value_name="__melted_value__")
    long_df = long_df.rename(columns={ts_col: "timestamp", "__melted_value__": "value"})
    return long_df[["series_id", "timestamp", "value"]]


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str], fmt: str) -> pd.DataFrame:
    if fmt == "wide":
        return melt_wide_to_long(df, mapping)

    ts_col = next((c for c, role in mapping.items() if role == "timestamp"), None)
    series_col = next((c for c, role in mapping.items() if role == "series_id"), None)
    value_col = next((c for c, role in mapping.items() if role == "value"), None)

    out = pd.DataFrame(index=df.index)
    out["timestamp"] = df[ts_col] if ts_col else pd.NA
    out["series_id"] = df[series_col] if series_col else "series_1"
    out["value"] = df[value_col] if value_col else pd.NA
    return out


def validate_mapping(df: pd.DataFrame, mapping: dict[str, str], fmt: str) -> dict:
    long_df = apply_mapping(df, mapping, fmt)
    total_rows = len(long_df)

    errors: list[str] = []
    warnings: list[str] = []

    parsed_ts = pd.to_datetime(long_df["timestamp"], errors="coerce")
    ts_parse_fraction = parsed_ts.notna().mean() if total_rows else 0.0
    if ts_parse_fraction < MIN_TIMESTAMP_PARSE_FRACTION:
        errors.append(
            f"No parseable timestamp column: only {ts_parse_fraction:.0%} of rows have a valid date/time "
            f"(need at least {MIN_TIMESTAMP_PARSE_FRACTION:.0%})."
        )

    parsed_value = pd.to_numeric(long_df["value"], errors="coerce")
    value_parse_fraction = parsed_value.notna().mean() if total_rows else 0.0
    non_numeric_fraction = 1 - value_parse_fraction
    if non_numeric_fraction > BLOCKING_NON_NUMERIC_VALUE_FRACTION:
        errors.append(
            f"{non_numeric_fraction:.0%} of the value column is non-numeric "
            f"(threshold: {BLOCKING_NON_NUMERIC_VALUE_FRACTION:.0%})."
        )

    valid_mask = parsed_ts.notna() & parsed_value.notna()
    valid_rows = int(valid_mask.sum())
    if valid_rows == 0:
        errors.append("No valid rows remain after parsing timestamps and values.")

    dropped = total_rows - valid_rows
    if dropped > 0 and valid_rows > 0:
        warnings.append(f"{dropped} of {total_rows} rows ({dropped / total_rows:.1%}) will be dropped (unparseable).")

    clean = long_df[valid_mask].copy()
    clean["timestamp"] = parsed_ts[valid_mask]

    n_series = 0
    detected_frequency = None
    if valid_rows > 0:
        n_series = clean["series_id"].nunique()

        dup_mask = clean.duplicated(subset=["series_id", "timestamp"], keep=False)
        n_duplicates = int(dup_mask.sum())
        if n_duplicates > 0:
            warnings.append(
                f"{n_duplicates} duplicate (series, timestamp) rows found -- "
                "the last occurrence of each will be kept."
            )

        # Infer frequency from the first series as a representative sample
        # (validate operates on a bounded sample, not the full file).
        first_series = clean["series_id"].iloc[0]
        ts_sorted = clean.loc[clean["series_id"] == first_series, "timestamp"].sort_values().drop_duplicates()
        if len(ts_sorted) >= 3:
            # pd.infer_freq requires a perfectly regular series and returns
            # None on the first gap -- exactly the case we want to flag --
            # so use the modal gap between consecutive timestamps instead,
            # which tolerates a few missing points.
            detected_frequency = pd.infer_freq(ts_sorted)
            diffs = ts_sorted.diff().dropna()
            if not diffs.empty:
                modal_delta = diffs.mode().iloc[0]
                if modal_delta.total_seconds() > 0:
                    expected_count = int((ts_sorted.max() - ts_sorted.min()) / modal_delta) + 1
                    missing_count = expected_count - len(ts_sorted)
                    if missing_count > 0:
                        warnings.append(
                            f"Detected {missing_count} missing timestamp(s) in series '{first_series}' "
                            f"relative to its typical {modal_delta} step."
                        )

    return {
        "row_count": total_rows,
        "valid_row_count": valid_rows,
        "series_count": n_series,
        "detected_frequency": detected_frequency,
        "errors": errors,
        "warnings": warnings,
        "can_proceed": len(errors) == 0,
    }
