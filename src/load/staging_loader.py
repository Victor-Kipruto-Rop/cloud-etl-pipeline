"""Safe utilities for staging-table upserts."""
import logging
import re
from typing import List

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class StagingError(Exception):
    """Raised when a staging operation fails."""


def _safe_identifier(value: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return value


def ensure_table_exists(engine: Engine, table_name: str, create_sql: str):
    """Create a table using trusted, application-owned DDL."""
    _safe_identifier(table_name)
    try:
        with engine.begin() as connection:
            connection.execute(text(create_sql))
    except Exception as exc:
        logger.exception("Failed to ensure table exists")
        raise StagingError(str(exc)) from exc


def upsert_from_staging(
    engine: Engine,
    staging_table: str,
    target_table: str,
    conflict_cols: List[str],
    update_cols: List[str],
):
    """Upsert explicit matching staging columns by a unique business key."""
    staging_table = _safe_identifier(staging_table)
    target_table = _safe_identifier(target_table)
    keys = [_safe_identifier(column) for column in conflict_cols]
    updates = [_safe_identifier(column) for column in update_cols]
    if not keys:
        raise ValueError("At least one conflict column is required")
    if set(keys) & set(updates):
        raise ValueError("Conflict columns cannot also be update columns")

    inspector = inspect(engine)
    if not inspector.has_table(staging_table):
        raise StagingError(f"Staging table does not exist: {staging_table}")
    if not inspector.has_table(target_table):
        raise StagingError(f"Target table does not exist: {target_table}")
    staging_columns = [
        column["name"] for column in inspector.get_columns(staging_table)
    ]
    target_columns = {
        column["name"] for column in inspector.get_columns(target_table)
    }
    if not set(staging_columns).issubset(target_columns):
        raise StagingError("Staging table contains columns absent from target")
    if not set(keys + updates).issubset(staging_columns):
        raise StagingError("Conflict or update columns are absent from staging")

    quote = engine.dialect.identifier_preparer.quote
    columns_sql = ", ".join(quote(column) for column in staging_columns)
    keys_sql = ", ".join(quote(column) for column in keys)
    if updates:
        action = "DO UPDATE SET " + ", ".join(
            f"{quote(column)} = EXCLUDED.{quote(column)}" for column in updates
        )
    else:
        action = "DO NOTHING"
    statement = text(
        f"INSERT INTO {quote(target_table)} ({columns_sql}) "
        f"SELECT {columns_sql} FROM {quote(staging_table)} WHERE 1=1 "
        f"ON CONFLICT ({keys_sql}) {action}"
    )
    try:
        with engine.begin() as connection:
            connection.execute(statement)
        logger.info("Upserted rows from %s into %s", staging_table, target_table)
    except Exception as exc:
        logger.exception("Staging upsert failed")
        raise StagingError(str(exc)) from exc
