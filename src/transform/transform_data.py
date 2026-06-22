"""
Robust data transformation module with comprehensive data cleaning.
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TransformError(Exception):
    """Raised when transformation fails."""

    pass


class TransformStats:
    """Track transformation statistics."""

    def __init__(self):
        self.rows_before = 0
        self.rows_after = 0
        self.columns_before = 0
        self.columns_after = 0
        self.duplicates_removed = 0
        self.rows_dropped = 0
        self.conversions = 0
        self.duration_seconds = 0.0

    def report(self) -> str:
        """Generate transformation report."""
        rows_reduced = self.rows_before - self.rows_after
        pct = (rows_reduced / self.rows_before * 100) if self.rows_before > 0 else 0

        return f"""
╔════════════════════════════════════════╗
║     TRANSFORMATION STATISTICS          ║
╠════════════════════════════════════════╣
║ Rows:      {self.rows_before:,d} → {self.rows_after:,d}   ║
║ Cols:      {self.columns_before:,d} → {self.columns_after:,d}        ║
║ Duplicates removed:     {self.duplicates_removed:>6,d}   ║
║ Rows dropped:           {self.rows_dropped:>6,d}   ║
║ Type conversions:       {self.conversions:>6,d}   ║
║ Duration:              {self.duration_seconds:>8.2f}s  ║
╚════════════════════════════════════════╝"""


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to snake_case."""
    try:
        new_columns = []
        for col in df.columns:
            new_col = str(col).strip().lower()
            new_col = new_col.replace(" ", "_").replace("-", "_")
            new_col = "".join(c if c.isalnum() or c == "_" else "" for c in new_col)
            new_col = new_col.strip("_")
            new_columns.append(new_col)

        df.columns = new_columns
        logger.info(f"✓ Normalized {len(df.columns)} column names")
        return df
    except Exception as e:
        raise TransformError(f"Column normalization failed: {e}") from e


def remove_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None) -> tuple:
    """Remove duplicate rows."""
    initial = len(df)
    try:
        df = df.drop_duplicates(subset=subset, keep="first")
        removed = initial - len(df)
        if removed > 0:
            logger.info(f"✓ Removed {removed:,d} duplicate rows")
        return df, removed
    except Exception as e:
        raise TransformError(f"Duplicate removal failed: {e}") from e


def handle_missing_values(df: pd.DataFrame, strategy: str = "drop_all") -> tuple:
    """Handle missing values."""
    initial = len(df)
    try:
        if strategy == "drop_all":
            df = df.dropna(how="all")
        elif strategy == "drop_any":
            df = df.dropna(how="any")
        elif strategy == "fill_mean":
            numeric = df.select_dtypes(include=[np.number]).columns
            df[numeric] = df[numeric].fillna(df[numeric].mean())

        removed = initial - len(df)
        if removed > 0:
            logger.info(f"✓ Handled missing values: {removed:,d} rows ({strategy})")
        return df, removed
    except Exception as e:
        raise TransformError(f"Missing value handling failed: {e}") from e


def convert_dtypes(df: pd.DataFrame) -> tuple:
    """Auto-convert column types."""
    conversions = 0
    try:
        for col in df.select_dtypes(include=["object"]).columns:
            try:
                df[col] = pd.to_numeric(df[col])
                conversions += 1
            except (ValueError, TypeError):
                pass

        if conversions > 0:
            logger.info(f"✓ Auto-converted {conversions} columns to numeric")
        return df, conversions
    except Exception as e:
        raise TransformError(f"Type conversion failed: {e}") from e


def transform(
    df: pd.DataFrame,
    normalize_cols: bool = True,
    remove_dups: bool = True,
    handle_missing: str = "drop_all",
    convert_types: bool = True,
) -> pd.DataFrame:
    """
    Transform DataFrame with comprehensive data cleaning.

    Args:
        df: Input DataFrame
        normalize_cols: Normalize column names
        remove_dups: Remove duplicate rows
        handle_missing: Strategy for missing values
        convert_types: Auto-convert data types

    Returns:
        Transformed DataFrame
    """
    start = datetime.now()
    stats = TransformStats()

    try:
        logger.info(f"{'='*70}")
        logger.info("TRANSFORMING DATA")
        logger.info(f"{'='*70}")

        if not isinstance(df, pd.DataFrame):
            raise TransformError(f"Expected DataFrame, got {type(df)}")

        stats.rows_before = len(df)
        stats.columns_before = len(df.columns)

        # Apply transformations
        if normalize_cols:
            df = normalize_columns(df)

        if handle_missing:
            df, dropped = handle_missing_values(df, handle_missing)
            stats.rows_dropped += dropped

        if remove_dups:
            df, dups = remove_duplicates(df)
            stats.duplicates_removed = dups

        if convert_types:
            df, convs = convert_dtypes(df)
            stats.conversions = convs

        stats.rows_after = len(df)
        stats.columns_after = len(df.columns)
        stats.duration_seconds = (datetime.now() - start).total_seconds()

        logger.info(stats.report())
        logger.info(f"✓ Transformation complete in {stats.duration_seconds:.2f}s\n")

        return df

    except TransformError:
        raise
    except Exception as e:
        msg = f"Unexpected transformation error: {e}"
        logger.error(msg)
        raise TransformError(msg) from e


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("Transform module loaded")
