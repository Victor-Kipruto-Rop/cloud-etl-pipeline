"""Transactional, retry-safe DataFrame upserts for PostgreSQL and SQLite."""
import re
import uuid
from typing import Sequence

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class IdempotentLoadError(RuntimeError):
    """Raised when an idempotent warehouse load cannot be completed."""


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return value


def upsert_dataframe(engine: Engine, dataframe: pd.DataFrame, *, table_name: str,
                     conflict_columns: Sequence[str], update_columns=None,
                     schema: str | None = None, chunk_size: int = 5000) -> int:
    """Upsert by business key in one transaction; duplicate input keys keep last row.

    The target table and matching unique/primary-key constraint must already exist.
    """
    table_name = _identifier(table_name)
    schema = _identifier(schema) if schema else None
    keys = [_identifier(column) for column in conflict_columns]
    if not keys:
        raise ValueError("At least one conflict column is required")
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame")
    if dataframe.empty:
        return 0
    if not set(keys).issubset(dataframe.columns):
        raise ValueError("Every conflict column must exist in the DataFrame")
    if dataframe[keys].isna().any().any():
        raise ValueError("Conflict-key columns cannot contain null values")
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")

    inspector = inspect(engine)
    if not inspector.has_table(table_name, schema=schema):
        raise IdempotentLoadError(f"Target table does not exist: {table_name}")
    target_columns = [column["name"] for column in inspector.get_columns(table_name, schema=schema)]
    unknown = set(dataframe.columns) - set(target_columns)
    if unknown:
        raise IdempotentLoadError(f"Unknown target columns: {sorted(unknown)}")
    updates = [_identifier(column) for column in (
        update_columns if update_columns is not None
        else [column for column in dataframe.columns if column not in keys]
    )]
    if not set(updates).issubset(dataframe.columns) or set(updates) & set(keys):
        raise ValueError("Update columns must be input columns and cannot be conflict keys")

    prepared = dataframe.drop_duplicates(subset=keys, keep="last")
    columns = list(prepared.columns)
    quote = engine.dialect.identifier_preparer.quote
    target = f"{quote(schema)}.{quote(table_name)}" if schema else quote(table_name)
    column_sql = ", ".join(quote(column) for column in columns)
    key_sql = ", ".join(quote(column) for column in keys)
    stage_name = f"etl_stage_{uuid.uuid4().hex}"
    stage_sql = quote(stage_name)
    action = (
        "DO UPDATE SET " + ", ".join(
            f"{quote(column)} = EXCLUDED.{quote(column)}" for column in updates
        ) if updates else "DO NOTHING"
    )
    statement = text(
        f"INSERT INTO {target} ({column_sql}) "
        f"SELECT {column_sql} FROM {stage_sql} WHERE 1=1 "
        f"ON CONFLICT ({key_sql}) {action}"
    )
    try:
        with engine.begin() as connection:
            connection.execute(text(
                f"CREATE TEMPORARY TABLE {stage_sql} AS "
                f"SELECT {column_sql} FROM {target} WHERE 1=0"
            ))
            prepared.to_sql(
                stage_name, connection, if_exists="append", index=False,
                chunksize=chunk_size, method="multi",
            )
            connection.execute(statement)
        return len(prepared)
    except Exception as exc:
        raise IdempotentLoadError(f"Idempotent load into {table_name} failed") from exc
