"""Controlled restoration helpers for quarantined source files."""
import shutil
from pathlib import Path

from src.reliability.store import MetadataStore


def restore_quarantined_file(
    store: MetadataStore, record_id: str, destination_dir: str | Path
) -> Path:
    """Copy a pending quarantined source back to an intake directory.

    This function intentionally does not mark the record replayed. Callers should
    mark it only after the normal ETL path and downstream commit have succeeded.
    """
    records = [
        record for record in store.list_quarantine(status="pending")
        if record["record_id"] == record_id
    ]
    if not records:
        raise KeyError(f"No pending quarantine record: {record_id}")
    source = Path(records[0]["source_uri"])
    if not source.is_file():
        raise FileNotFoundError(f"Quarantined source is unavailable: {source}")
    destination = Path(destination_dir)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / source.name
    if target.exists():
        raise FileExistsError(f"Replay destination already exists: {target}")
    shutil.copy2(source, target)
    return target
