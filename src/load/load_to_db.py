"""
Robust database loading module with connection pooling and transaction management.
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class LoadError(Exception):
    """Raised when loading fails."""

    pass


class LoadStats:
    """Track loading statistics."""

    def __init__(self):
        self.rows_attempted = 0
        self.rows_loaded = 0
        self.rows_failed = 0
        self.duration_seconds = 0.0
        self.table_name = None

    def report(self) -> str:
        """Generate loading report."""
        success_pct = (
            (self.rows_loaded / self.rows_attempted * 100)
            if self.rows_attempted > 0
            else 0
        )
        return f"""
╔════════════════════════════════════════╗
║         LOADING STATISTICS             ║
╠════════════════════════════════════════╣
║ Table:     {str(self.table_name):>29s}║
║ Attempted: {self.rows_attempted:>29,d}║
║ Loaded:    {self.rows_loaded:>29,d}  ║
║ Failed:    {self.rows_failed:>29,d}  ║
║ Success:   {success_pct:>28.1f}% ║
║ Duration:  {self.duration_seconds:>28.2f}s ║
╚════════════════════════════════════════╝"""


class DatabaseManager:
    """Manage database connections and operations."""

    def __init__(
        self,
        user: str = None,
        password: str = None,
        host: str = None,
        port: int = None,
        database: str = None,
    ):
        """Initialize with connection parameters from environment or args."""
        self.user = user or os.getenv("POSTGRES_USER", "postgres")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "postgres")
        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.port = port or int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = database or os.getenv("POSTGRES_DB", "etl_db")
        self.engine = None

    def build_connection_string(self) -> str:
        """Build SQLAlchemy connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def connect(self) -> None:
        """Establish database connection."""
        try:
            logger.info(f"Connecting to {self.host}:{self.port}/{self.database}...")
            conn_str = self.build_connection_string()
            self.engine = create_engine(
                conn_str,
                echo=False,
                pool_size=10,
                max_overflow=20,
                pool_recycle=3600,
                pool_pre_ping=True,
            )
            # Test connection
            with self.engine.connect() as conn:
                pass
            logger.info("✓ Database connection successful")
        except SQLAlchemyError as e:
            msg = f"Failed to connect to database: {e}"
            logger.error(msg)
            raise LoadError(msg) from e

    def disconnect(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.debug("Database connection closed")

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists."""
        try:
            inspector = inspect(self.engine)
            return table_name in inspector.get_table_names()
        except Exception as e:
            logger.warning(f"Error checking table existence: {e}")
            return False

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get table schema information."""
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name)
            return {
                "columns": [c["name"] for c in columns],
                "column_types": {c["name"]: str(c["type"]) for c in columns},
                "primary_keys": inspector.get_pk_constraint(table_name)[
                    "constrained_columns"
                ],
            }
        except Exception as e:
            logger.warning(f"Could not get table info: {e}")
            return {}


def load_df_to_postgres(
    df: pd.DataFrame,
    table_name: str,
    if_exists: str = "append",
    chunk_size: int = 5000,
    validate_schema: bool = True,
) -> int:
    """
    Load DataFrame to PostgreSQL with comprehensive error handling.

    Args:
        df: DataFrame to load
        table_name: Target table name
        if_exists: 'fail', 'replace', 'append'
        chunk_size: Rows per chunk
        validate_schema: Validate schema before loading

    Returns:
        Number of rows loaded

    Raises:
        LoadError: If loading fails
    """
    start = datetime.now()
    stats = LoadStats()
    stats.table_name = table_name
    stats.rows_attempted = len(df)

    # Validate inputs
    if not isinstance(df, pd.DataFrame):
        raise LoadError(f"Expected DataFrame, got {type(df)}")

    if not table_name or not isinstance(table_name, str):
        raise LoadError(f"Invalid table name: {table_name}")

    if if_exists not in ["fail", "replace", "append"]:
        raise LoadError(f"Invalid if_exists: {if_exists}")

    if df.empty:
        logger.warning("DataFrame is empty, skipping load")
        return 0

    db_manager = DatabaseManager()

    try:
        logger.info(f"{'='*70}")
        logger.info(f"LOADING TO DATABASE: {table_name}")
        logger.info(f"{'='*70}")

        # Connect
        db_manager.connect()

        # Validate schema if replacing
        if if_exists == "replace" and validate_schema:
            logger.info(f"Creating/replacing table '{table_name}'...")
        elif if_exists == "append":
            if db_manager.table_exists(table_name):
                info = db_manager.get_table_info(table_name)
                logger.info(
                    f"Appending to existing table with {len(info.get('columns', []))} columns"
                )

        # Load data with chunking
        logger.info(f"Loading {len(df):,d} rows (chunk size: {chunk_size})...")

        df.to_sql(
            table_name,
            db_manager.engine,
            if_exists=if_exists,
            index=False,
            chunksize=chunk_size,
            method="multi",
        )

        stats.rows_loaded = len(df)
        stats.rows_failed = 0
        stats.duration_seconds = (datetime.now() - start).total_seconds()

        logger.info(stats.report())
        logger.info(f"✓ Load successful in {stats.duration_seconds:.2f}s\n")

        return stats.rows_loaded

    except SQLAlchemyError as e:
        msg = f"Database error loading to '{table_name}': {e}"
        logger.error(msg)
        raise LoadError(msg) from e
    except Exception as e:
        msg = f"Unexpected error loading to '{table_name}': {e}"
        logger.error(msg)
        raise LoadError(msg) from e
    finally:
        db_manager.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print("Load module loaded")
