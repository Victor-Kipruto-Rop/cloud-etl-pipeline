"""Immutable bronze, silver and gold file-layer writer."""
import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from src.io_utils import write_dataframe_atomic

_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _safe(value, label):
    if not isinstance(value, str) or not _SAFE.fullmatch(value) or value in {".", ".."}:
        raise ValueError(f"Invalid {label}")
    return value


def _write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".manifest.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True, default=str)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def write_layer(
    dataframe: pd.DataFrame,
    *,
    root,
    layer: str,
    dataset: str,
    run_id: str,
    ingestion_date=None,
    file_format: str = "parquet",
    source_uri: str | None = None,
    source_checksum: str | None = None,
    schema_version: str = "1",
) -> dict:
    """Write an immutable run-scoped artifact and a checksum manifest."""
    layer = _safe(layer.lower(), "layer")
    if layer not in {"bronze", "silver", "gold"}:
        raise ValueError("layer must be bronze, silver or gold")
    dataset, run_id = _safe(dataset, "dataset"), _safe(run_id, "run_id")
    if file_format not in {"csv", "parquet"}:
        raise ValueError("file_format must be csv or parquet")
    day = ingestion_date or datetime.now(timezone.utc).date()
    if isinstance(day, str):
        day = date.fromisoformat(day)
    partition = (
        Path(root)
        / layer
        / dataset
        / f"ingestion_date={day.isoformat()}"
        / f"run_id={run_id}"
    )
    artifact = partition / f"data.{file_format}"
    if artifact.exists() or (partition / "manifest.json").exists():
        raise FileExistsError(f"Run output already exists: {partition}")
    if file_format == "parquet":
        write_dataframe_atomic(dataframe, artifact, compression="snappy")
    else:
        write_dataframe_atomic(dataframe, artifact)
    checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = {
        "layer": layer,
        "dataset": dataset,
        "run_id": run_id,
        "ingestion_date": day.isoformat(),
        "artifact": artifact.name,
        "format": file_format,
        "row_count": int(len(dataframe)),
        "column_names": [str(column) for column in dataframe.columns],
        "sha256": checksum,
        "source_uri": source_uri,
        "source_checksum": source_checksum,
        "schema_version": schema_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_manifest(partition / "manifest.json", manifest)
    return {
        "artifact_path": str(artifact),
        "manifest_path": str(partition / "manifest.json"),
        **manifest,
    }


def read_manifest(path) -> dict:
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)
