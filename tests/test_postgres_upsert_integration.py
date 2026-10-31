import os

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from src.load.idempotent import upsert_dataframe


def test_postgres_business_key_upsert_is_transactional_and_repeatable():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = create_engine(database_url, pool_pre_ping=True)
    table_name = "test_etl_idempotent_upsert"
    try:
        with engine.begin() as connection:
            connection.execute(text(
                f"CREATE TABLE IF NOT EXISTS {table_name} "
                "(id BIGINT PRIMARY KEY, value TEXT NOT NULL)"
            ))
            connection.execute(text(f"TRUNCATE TABLE {table_name}"))
            connection.execute(
                text(f"INSERT INTO {table_name} (id, value) VALUES (1, 'old')")
            )

        frame = pd.DataFrame(
            [
                {"id": 1, "value": "updated"},
                {"id": 2, "value": "new"},
            ]
        )
        assert upsert_dataframe(
            engine,
            frame,
            table_name=table_name,
            conflict_columns=["id"],
        ) == 2
        assert upsert_dataframe(
            engine,
            frame,
            table_name=table_name,
            conflict_columns=["id"],
        ) == 2

        with engine.connect() as connection:
            rows = connection.execute(
                text(f"SELECT id, value FROM {table_name} ORDER BY id")
            ).all()
        assert rows == [(1, "updated"), (2, "new")]
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        engine.dispose()
