"""Utilities to load into a staging table and perform upsert into target table."""

import logging
from typing import List

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class StagingError(Exception):
    pass


def ensure_table_exists(engine: Engine, table_name: str, create_sql: str):
    """Create the table if it does not exist using provided DDL."""
    try:
        with engine.begin() as conn:
            conn.execute(text(create_sql))
    except Exception as e:
        logger.exception("Failed to ensure table exists")
        raise StagingError(str(e)) from e


def upsert_from_staging(
    engine: Engine,
    staging_table: str,
    target_table: str,
    conflict_cols: List[str],
    update_cols: List[str],
):
    """Perform an upsert from staging_table into target_table using ON CONFLICT.

    conflict_cols: columns to use in ON CONFLICT (must be unique/primary key)
    update_cols: columns to update on conflict
    """
    try:
        set_clause = ", ".join([f"{col}=EXCLUDED.{col}" for col in update_cols])
        conflict_clause = ", ".join(conflict_cols)
        sql = f"INSERT INTO {target_table} SELECT * FROM {staging_table} ON CONFLICT ({conflict_clause}) DO UPDATE SET {set_clause};"
        with engine.begin() as conn:
            conn.execute(text(sql))
        logger.info(f"Upserted data from {staging_table} into {target_table}")
    except Exception as e:
        logger.exception("Upsert failed")
        raise StagingError(str(e)) from e
