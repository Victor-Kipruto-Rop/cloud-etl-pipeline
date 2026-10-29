from dataclasses import dataclass
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


@dataclass
class DataQualityContract:
    """Declarative data-quality contract for ETL datasets."""

    required_columns: Optional[Iterable[str]] = None
    min_rows: Optional[int] = None
    max_null_ratio: Optional[Dict[str, float]] = None
    unique_columns: Optional[Iterable[str]] = None
    allow_extra_columns: bool = True
    allowed_value_sets: Optional[Dict[str, Iterable[str]]] = None

    def as_dict(self) -> Dict[str, object]:
        return {
            "required_columns": list(self.required_columns or []),
            "min_rows": self.min_rows,
            "max_null_ratio": dict(self.max_null_ratio or {}),
            "unique_columns": list(self.unique_columns or []),
            "allow_extra_columns": self.allow_extra_columns,
            "allowed_value_sets": dict(self.allowed_value_sets or {}),
        }


def parse_required_columns(env_value: Optional[str]) -> Optional[Iterable[str]]:
    if not env_value:
        return None
    return [c.strip() for c in env_value.split(",") if c.strip()]


def _validate_required_columns(
    df: pd.DataFrame, required_columns: Optional[Iterable[str]]
) -> None:
    if not required_columns:
        return
    required = list(required_columns)
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValidationError(f"Missing required columns: {missing}")

    # A required field is not usable when every value is null, blank, or the
    # string representation of a missing value. Treat these consistently for
    # object and pandas string columns, including whitespace-only values.
    empty_columns = []
    for column in required:
        values = df[column]
        missing_values = values.isna() | (
            values.astype("string").str.strip().str.lower().isin({"", "nan"})
        )
        if missing_values.all():
            empty_columns.append(column)

    if empty_columns:
        raise ValidationError(
            f"Required columns are empty or null: {empty_columns}"
        )


def validate_df(
    df: pd.DataFrame, required_columns: Optional[Iterable[str]] = None
) -> None:
    """Validate a DataFrame, consistently enforcing required-field checks.

    Prefers Pandera for schema checks when available, otherwise falls back to
    lightweight checks. Raises ValidationError on failure.
    """
    if not isinstance(df, pd.DataFrame):
        raise ValidationError(f"Expected DataFrame, got {type(df)}")

    if df.empty:
        raise ValidationError("DataFrame has zero rows")

    required = list(required_columns) if required_columns else None
    _validate_required_columns(df, required)

    if _HAS_PANDERA and required:
        schema = DataFrameSchema(
            {column: Column(None, nullable=True) for column in required}
        )
        try:
            schema.validate(df, lazy=False)
        except pa.errors.SchemaError as exc:
            raise ValidationError(str(exc)) from exc
        return None

    all_nan_columns = [column for column in df.columns if df[column].isna().all()]
    if all_nan_columns:
        raise ValidationError(
            f"Columns contain only NaN values: {all_nan_columns}"
        )

    return None


def validate_contract(df: pd.DataFrame, contract: DataQualityContract) -> None:
    """Validate a DataFrame against a declarative data-quality contract."""
    validate_df(df, required_columns=contract.required_columns)

    if contract.min_rows is not None and len(df) < contract.min_rows:
        raise ValidationError(
            f"Dataset has fewer than {contract.min_rows} rows: {len(df)}"
        )

    if contract.max_null_ratio:
        for column, max_ratio in contract.max_null_ratio.items():
            if column not in df.columns:
                raise ValidationError(
                    f"Null-ratio check references missing column: {column}"
                )
            null_ratio = float(df[column].isna().mean()) if len(df) else 0.0
            if null_ratio > max_ratio:
                raise ValidationError(
                    f"Null ratio for '{column}' exceeds threshold: "
                    f"{null_ratio:.2%} > {max_ratio:.2%}"
                )

    if contract.unique_columns:
        for column in contract.unique_columns:
            if column not in df.columns:
                raise ValidationError(
                    f"Unique-column check references missing column: {column}"
                )
            duplicates = df[column].duplicated().sum()
            if duplicates:
                raise ValidationError(
                    f"Column '{column}' contains duplicate values: "
                    f"{duplicates} duplicates"
                )

    if contract.allowed_value_sets:
        for column, allowed_values in contract.allowed_value_sets.items():
            if column not in df.columns:
                raise ValidationError(
                    f"Allowed-values check references missing column: {column}"
                )
            allowed_set = set(str(value) for value in allowed_values)
            unexpected = set(df[column].dropna().astype(str)) - allowed_set
            if unexpected:
                raise ValidationError(
                    f"Values in '{column}' are not allowed: "
                    f"{sorted(unexpected)[:10]}"
                )

    if not contract.allow_extra_columns:
        expected = set(contract.required_columns or [])
        unexpected = [column for column in df.columns if column not in expected]
        if unexpected:
            raise ValidationError(
                f"Unexpected extra columns found: {unexpected}"
            )

    return None
