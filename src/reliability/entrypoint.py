"""Filesystem entrypoint for incremental medallion ETL execution."""
import hashlib
import json
import logging
import os
from pathlib import Path

from sqlalchemy import create_engine

from src.extract.extract_data import extract_csv
from src.reliability.runner import execute_dataset
from src.reliability.store import MetadataStore
from src.transform.transform_data import transform
from src.validation import (
    DataQualityContract,
    parse_required_columns,
    validate_contract,
    validate_df,
)

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
    metadata_url = (
        os.getenv("METADATA_DATABASE_URL")
        or database_url
        or "sqlite:///data/metadata/etl_metadata.db"
    )
    if database_url and not os.getenv("UPSERT_KEY_COLUMNS", "").strip():
        raise ValueError(
            "UPSERT_KEY_COLUMNS is required when DATABASE_URL is set in medallion mode"
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
    contract_path = os.getenv("DATA_QUALITY_CONTRACT_PATH")
    contract = None
    if contract_path:
        with Path(contract_path).open(encoding="utf-8") as contract_file:
            contract = DataQualityContract(**json.load(contract_file))

    def validate_source(dataframe):
        if contract is not None:
            validate_contract(dataframe, contract)
        else:
            validate_df(dataframe, required_columns=required_columns)

    conflict_columns = tuple(
        column.strip()
        for column in os.getenv("UPSERT_KEY_COLUMNS", "").split(",")
        if column.strip()
    )
    contract_signature = json.dumps(
        {
            "contract": contract.as_dict() if contract is not None else None,
            "required_columns": list(required_columns or []),
            "transform_version": os.getenv("TRANSFORM_VERSION", "1"),
        },
        sort_keys=True,
    )
    source_version = hashlib.sha256(contract_signature.encode("utf-8")).hexdigest()
    file_format = os.getenv("MEDALLION_FILE_FORMAT", "parquet").lower()
    successful = True

    try:
        for source in files:
            source = Path(source)
            try:
                source_df = extract_csv(source)
                result = execute_dataset(
                    source_df,
                    dataset=source.stem,
                    source_uri=str(source.resolve()),
                    source_checksum=_checksum(source),
                    source_version=source_version,
                    metadata_store=store,
                    layer_root=layer_root,
                    validate=validate_source,
                    transform=lambda frame: transform(
                        frame, normalize_cols=True, handle_missing="drop_all"
                    ),
                    database_engine=database_engine,
                    target_table=os.getenv("TARGET_TABLE") or source.stem,
                    target_schema=os.getenv("TARGET_SCHEMA") or None,
                    conflict_columns=conflict_columns,
                    s3_bucket=os.getenv("AWS_S3_BUCKET") or None,
                    s3_prefix=os.getenv("S3_DATA_PREFIX", ""),
                    aws_region=os.getenv("AWS_REGION") or None,
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
