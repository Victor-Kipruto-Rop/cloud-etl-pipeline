"""High-performance Postgres COPY loader utilities."""

import io
import logging
from typing import List

from sqlalchemy import create_engine

logger = logging.getLogger(__name__)


class LoadError(Exception):
    pass


def copy_from_df(engine_url: str, df, table_name: str, columns: List[str]) -> int:
    """Load a pandas DataFrame into Postgres using COPY for high throughput.

    Args:
        engine_url: SQLAlchemy engine URL/DSN
        df: pandas DataFrame
        table_name: destination table name
        columns: list of column names in the target table matching df columns order

    Returns:
        int: number of rows loaded
    """
    buf = io.StringIO()
    # write CSV without header; COPY expects columns order provided separately
    df.to_csv(buf, index=False, header=False)
    buf.seek(0)

    try:
        engine = create_engine(engine_url)
        # Use raw connection for COPY
        with engine.raw_connection() as conn:
            cur = conn.cursor()
            sql = (
                f"COPY {table_name} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv)"
            )
            cur.copy_expert(sql=sql, file=buf)
            conn.commit()
        logger.info(f"COPY loaded {len(df)} rows into {table_name}")
        return len(df)
    except Exception as e:
        logger.exception("COPY load failed")
        raise LoadError(str(e)) from e
