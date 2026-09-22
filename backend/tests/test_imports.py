import pandas as pd
import pytest

from app.imports.detection import detect_format_and_mapping
from app.imports.validation import apply_mapping, melt_wide_to_long, validate_mapping


def test_detect_long_format_with_named_columns():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=10).astype(str),
            "series_id": ["A"] * 10,
            "value": range(10),
        }
    )
    result = detect_format_and_mapping(df)

    assert result["format"] == "long"
    assert result["column_mapping"]["date"] == "timestamp"
    assert result["column_mapping"]["series_id"] == "series_id"
    assert result["column_mapping"]["value"] == "value"
    assert result["wide_melt_preview"] is None


def test_detect_wide_format_with_multiple_numeric_columns():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=5).astype(str),
            "store_1": [1.0, 2.0, 3.0, 4.0, 5.0],
            "store_2": [10.0, 20.0, 30.0, 40.0, 50.0],
            "store_3": [100.0, 200.0, 300.0, 400.0, 500.0],
        }
    )
    result = detect_format_and_mapping(df)

    assert result["format"] == "wide"
    assert result["column_mapping"]["date"] == "timestamp"
    assert result["column_mapping"]["store_1"] == "value"
    assert result["column_mapping"]["store_2"] == "value"
    assert result["column_mapping"]["store_3"] == "value"
    assert len(result["wide_melt_preview"]) == 3


def test_detect_recognizes_suffixed_id_columns():
    # Real CSVs commonly use store_id/product_id/etc. rather than the bare
    # "id" or "series_id" -- these must be recognized as series_id too.
    df = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=5).astype(str),
            "store_id": ["A"] * 5,
            "units_sold": range(5),
        }
    )
    result = detect_format_and_mapping(df)

    assert result["format"] == "long"
    assert result["column_mapping"]["store_id"] == "series_id"


def test_detect_timestamp_falls_back_to_parse_rate_when_no_name_match():
    df = pd.DataFrame(
        {
            "when": pd.date_range("2020-01-01", periods=10).astype(str),
            "id": ["A"] * 10,
            "amount": range(10),
        }
    )
    result = detect_format_and_mapping(df)

    assert result["column_mapping"]["when"] == "timestamp"


def test_melt_wide_to_long_produces_one_series_per_value_column():
    df = pd.DataFrame({"date": ["2020-01-01", "2020-01-02"], "a": [1, 2], "b": [3, 4]})
    mapping = {"date": "timestamp", "a": "value", "b": "value"}

    long_df = melt_wide_to_long(df, mapping)

    assert set(long_df["series_id"]) == {"a", "b"}
    assert len(long_df) == 4


def test_melt_wide_to_long_handles_source_column_literally_named_value():
    # pandas' melt() raises if value_name collides with an existing column
    # -- a wide CSV whose own value column is literally named "value" (very
    # common) must not crash. Regression test for a live bug found on the
    # classic AirPassengers.csv export (columns: "", "time", "value").
    df = pd.DataFrame({"time": ["2020-01-01", "2020-01-02"], "value": [1, 2]})
    mapping = {"time": "timestamp", "value": "value"}

    long_df = melt_wide_to_long(df, mapping)

    assert list(long_df["series_id"]) == ["value", "value"]
    assert list(long_df["value"]) == [1, 2]


def test_validate_clean_data_has_no_errors_or_warnings():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2020-01-01", periods=20).astype(str),
            "series_id": ["A"] * 20,
            "value": range(20),
        }
    )
    mapping = {"timestamp": "timestamp", "series_id": "series_id", "value": "value"}

    result = validate_mapping(df, mapping, "long")

    assert result["can_proceed"] is True
    assert result["errors"] == []
    assert result["detected_frequency"] is not None
    assert result["valid_row_count"] == 20


def test_validate_blocks_when_no_parseable_timestamp():
    df = pd.DataFrame({"timestamp": ["not", "a", "date"] * 5, "series_id": ["A"] * 15, "value": range(15)})
    mapping = {"timestamp": "timestamp", "series_id": "series_id", "value": "value"}

    result = validate_mapping(df, mapping, "long")

    assert result["can_proceed"] is False
    assert any("timestamp" in e.lower() for e in result["errors"])


def test_validate_blocks_when_value_column_mostly_non_numeric():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2020-01-01", periods=10).astype(str),
            "series_id": ["A"] * 10,
            "value": ["not_a_number"] * 8 + [1, 2],
        }
    )
    mapping = {"timestamp": "timestamp", "series_id": "series_id", "value": "value"}

    result = validate_mapping(df, mapping, "long")

    assert result["can_proceed"] is False
    assert any("non-numeric" in e for e in result["errors"])


def test_validate_warns_on_duplicate_timestamps_but_does_not_block():
    df = pd.DataFrame(
        {
            "timestamp": ["2020-01-01", "2020-01-01", "2020-01-02", "2020-01-03"],
            "series_id": ["A", "A", "A", "A"],
            "value": [1, 2, 3, 4],
        }
    )
    mapping = {"timestamp": "timestamp", "series_id": "series_id", "value": "value"}

    result = validate_mapping(df, mapping, "long")

    assert result["can_proceed"] is True
    assert any("duplicate" in w.lower() for w in result["warnings"])


def test_validate_warns_on_missing_timestamp_gaps():
    dates = pd.date_range("2020-01-01", periods=10).tolist()
    del dates[5]  # remove one day to create a gap
    df = pd.DataFrame({"timestamp": [d.strftime("%Y-%m-%d") for d in dates], "series_id": ["A"] * 9, "value": range(9)})
    mapping = {"timestamp": "timestamp", "series_id": "series_id", "value": "value"}

    result = validate_mapping(df, mapping, "long")

    assert any("missing" in w.lower() for w in result["warnings"])


def test_apply_mapping_long_defaults_series_id_when_unmapped():
    df = pd.DataFrame({"timestamp": ["2020-01-01", "2020-01-02"], "value": [1, 2]})
    mapping = {"timestamp": "timestamp", "value": "value"}

    out = apply_mapping(df, mapping, "long")

    assert (out["series_id"] == "series_1").all()
