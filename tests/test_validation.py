import pandas as pd
import pytest

from src.validation import ValidationError, parse_required_columns, validate_df


def test_validate_df_pass():
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    validate_df(df, required_columns=["a", "b"])


def test_validate_df_missing_column():
    df = pd.DataFrame({"a": [1, 2]})
    with pytest.raises(ValidationError):
        validate_df(df, required_columns=["a", "b"])


def test_parse_required_columns():
    assert parse_required_columns("a,b,c") == ["a", "b", "c"]
    assert parse_required_columns("") is None
