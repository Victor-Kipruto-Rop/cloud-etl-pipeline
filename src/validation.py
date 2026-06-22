from typing import Dict, Iterable, Optional

import pandas as pd

try:
    import pandera as pa
    from pandera import Column, DataFrameSchema

    _HAS_PANDERA = True
except Exception:
    _HAS_PANDERA = False


class ValidationError(Exception):
    pass


def parse_required_columns(env_value: Optional[str]) -> Optional[Iterable[str]]:
    if not env_value:
        return None
    return [c.strip() for c in env_value.split(",") if c.strip()]


def validate_df(
    df: pd.DataFrame, required_columns: Optional[Iterable[str]] = None
) -> None:
    """Run validation checks against a DataFrame.

    Prefers `pandera` for schema checks when available, otherwise falls back to
    lightweight checks.

    Raises ValidationError on failure.
    """
    if _HAS_PANDERA and required_columns:
        # Use a minimal pandera schema requiring presence of columns
        schema = DataFrameSchema(
            {c: Column(object, nullable=True) for c in required_columns}
        )
        try:
            schema.validate(df, lazy=False)
        except pa.errors.SchemaError as e:
            raise ValidationError(str(e)) from e
        return None

    if required_columns:
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            raise ValidationError(f"Missing required columns: {missing}")

    if df.shape[0] == 0:
        raise ValidationError("DataFrame has zero rows")

    all_nan_cols = [c for c in df.columns if df[c].isna().all()]
    if all_nan_cols:
        raise ValidationError(f"Columns contain only NaN values: {all_nan_cols}")

    return None
