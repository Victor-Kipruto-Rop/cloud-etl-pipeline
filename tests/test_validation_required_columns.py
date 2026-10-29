import pandas as pd
import pytest

from src.validation import (
    DataQualityContract,
    ValidationError,
    validate_contract,
    validate_df,
)


@pytest.mark.parametrize(
    "values",
    [
        [None, None],
        ["", "   "],
        ["nan", " NaN "],
        [None, "   "],
    ],
)
def test_required_column_rejects_values_that_are_all_missing_or_blank(values):
    frame = pd.DataFrame({"customer_id": values})

    with pytest.raises(ValidationError, match="Required columns are empty or null"):
        validate_df(frame, required_columns=["customer_id"])


def test_required_column_accepts_a_non_blank_value_with_missing_rows():
    frame = pd.DataFrame({"customer_id": ["C-100", "  "]})

    validate_df(frame, required_columns=["customer_id"])


def test_required_column_still_reports_missing_column():
    frame = pd.DataFrame({"amount": [10, 20]})

    with pytest.raises(ValidationError, match="Missing required columns"):
        validate_df(frame, required_columns=["customer_id"])


def test_contract_applies_required_column_blank_check():
    frame = pd.DataFrame({"customer_id": [" ", None]})
    contract = DataQualityContract(required_columns=["customer_id"])

    with pytest.raises(ValidationError, match="Required columns are empty or null"):
        validate_contract(frame, contract)
