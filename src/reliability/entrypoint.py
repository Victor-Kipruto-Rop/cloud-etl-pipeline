"""Filesystem entrypoint for incremental medallion ETL execution."""
import hashlib
import logging
import os
from pathlib import Path

from sqlalchemy import create_engine

from src.extract.extract_data import extract_csv
from src.reliability.runner import execute_dataset
from src.reliability.store import MetadataStore
from src.transform.transform_data import transform
from src.validation import parse_required_columns, validate_df

logger = logging.getLogger(__name__)


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_medallion_files(files, *, layer_root="data/lake") -> bool:
    """Execute CSV sources through bronze/silver, metadata and optional DB upsert.

    Set DATABASE_URL and UPSERT_KEY_COLUMNS together to enable a transactional
    database sink. METADATA_DATABASE_URL can point to a separate metadata database;
    otherwise DATABASE_URL is reused, or a local SQLite ledger is created.
    """
    database_url = os.getenv("DATABASE_URL")
    metadata_url = os.getenv(
        "METADATA_DATABASE_URL",
        database_url or "sqlite:///data/metadata/etl_metadata.db",
    )
    if database_url and not os.getenv("UPSERT_KEY_COLUMNS", "").strip():
        raise ValueError(
            "UPSERT_KEY_COLUMNS is required when DATABASE_URL is set in medallion mode"
        )
    if os.getenv("POSTGRES_HOST") and not database_url:
        raise ValueError(
            "Medallion mode requires DATABASE_URL for transactional idempotent loading"
        )

    if metadata_url.startswith("sqlite:///"):
        sqlite_path = Path(metadata_url.removeprefix("sqlite:///"))
        if str(sqlite_path) != ":memory:":
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    metadata_engine = create_engine(metadata_url, pool_pre_ping=True)
    database_engine = (
        create_engine(database_url, pool_pre_ping=True) if database_url else None
    )
    store = MetadataStore(metadata_engine)
    required_columns = parse_required_columns(os.getenv("REQUIRED_COLUMNS"))
    conflict_columns = tuple(
        column.strip()
        for column in os.getenv("UPSERT_KEY_COLUMNS", "").split(",")
        if column.strip()
    )
    file_format = os.getenv("MEDALLION_FILE_FORMAT", "parquet").lower()
    successful = True

    try:
        for source in files:
            source = Path(source)
            try:
                source_df = extract_csv(source)
                validate_df(source_df, required_columns=required_columns)
                silver_df = transform(
                    source_df, normalize_cols=True, handle_missing="drop_all"
                )
                result = execute_dataset(
                    source_df,
                    silver_df,
                    dataset=source.stem,
                    source_uri=source.resolve().as_uri(),
                    source_checksum=_checksum(source),
                    metadata_store=store,
                    layer_root=layer_root,
                    database_engine=database_engine,
                    target_table=os.getenv("TARGET_TABLE", source.stem),
                    conflict_columns=conflict_columns,
                    file_format=file_format,
                )
                logger.info("Medallion dataset result: %s", result)
            except Exception:
                successful = False
                logger.exception("Medallion processing failed for %s", source.name)
    finally:
        metadata_engine.dispose()
        if database_engine is not None and database_engine is not metadata_engine:
            database_engine.dispose()
    return successful
