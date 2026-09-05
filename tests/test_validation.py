import pandas as pd
import pytest

from src.validation import (
    DataQualityContract,
    ValidationError,
    parse_required_columns,
    validate_contract,
    validate_df,
)


def test_validate_df_pass():
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    validate_df(df, required_columns=["a", "b"])


def test_validate_df_missing_column():
    df = pd.DataFrame({"a": [1, 2]})
    with pytest.raises(ValidationError):
        validate_df(df, required_columns=["a", "b"])


def test_validate_contract_enforces_quality_rules():
    df = pd.DataFrame(
        {
            "customer_id": [1, 1, 3],
            "amount": [100.0, None, 50.0],
            "status": ["active", "active", "inactive"],
        }
    )

    contract = DataQualityContract(
        required_columns=["customer_id", "amount", "status"],
        max_null_ratio={"amount": 0.2},
        min_rows=3,
        unique_columns=["customer_id"],
    )

    with pytest.raises(ValidationError):
        validate_contract(df, contract)


def test_parse_required_columns():
    assert parse_required_columns("a,b,c") == ["a", "b", "c"]
    assert parse_required_columns("") is None
