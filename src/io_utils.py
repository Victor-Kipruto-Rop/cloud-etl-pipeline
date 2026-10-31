"""Safe local file-output helpers for ETL stages."""

import os
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd


class DataWriteError(RuntimeError):
    """Raised when a transformed dataset cannot be written safely."""


def write_dataframe_atomic(
    dataframe: pd.DataFrame,
    destination: str | Path,
    **writer_options: Any,
) -> Path:
    """Write a DataFrame and atomically replace its destination.

    The temporary file is created in the destination directory so os.replace
    stays on the same filesystem. A failed write leaves any previous output intact.
    Supported formats are CSV and Parquet, selected by the destination suffix.
    """
    path = Path(destination)
    suffix = path.suffix.lower()
    if suffix not in {".csv", ".parquet", ".pq"}:
        raise ValueError(f"Unsupported dataset format: {suffix or '<no extension>'}")
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame")

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}.", suffix=suffix, dir=str(path.parent)
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)

    try:
        if suffix == ".csv":
            dataframe.to_csv(temporary_path, index=False, **writer_options)
        else:
            dataframe.to_parquet(temporary_path, index=False, **writer_options)

        with temporary_path.open("rb") as output_file:
            os.fsync(output_file.fileno())
        os.replace(temporary_path, path)
        return path
    except Exception as exc:
        temporary_path.unlink(missing_ok=True)
        raise DataWriteError(f"Failed to write dataset to {path}") from exc
