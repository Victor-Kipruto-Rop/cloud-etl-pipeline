from typing import Dict, Iterable, Optional

import pandas as pd


class ValidationError(Exception):
    pass


def parse_required_columns(env_value: Optional[str]) -> Optional[Iterable[str]]:
    if not env_value:
        return None
    return [c.strip() for c in env_value.split(",") if c.strip()]


def validate_df(
    df: pd.DataFrame, required_columns: Optional[Iterable[str]] = None
) -> None:
    """Run lightweight validation checks against a DataFrame.

    Raises ValidationError on failure.
    """
    if required_columns:
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            raise ValidationError(f"Missing required columns: {missing}")

    # Example checks: no all-NaN columns, reasonable row count
    if df.shape[0] == 0:
        raise ValidationError("DataFrame has zero rows")

    all_nan_cols = [c for c in df.columns if df[c].isna().all()]
    if all_nan_cols:
        raise ValidationError(f"Columns contain only NaN values: {all_nan_cols}")

    # Add additional domain-specific checks here as needed
    return None
