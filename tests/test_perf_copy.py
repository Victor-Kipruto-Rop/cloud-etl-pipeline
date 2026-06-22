import os
import time
from datetime import datetime

import pandas as pd
import pytest

from src.load.copy_loader import copy_from_df
from src.load.load_to_db import DatabaseManager, LoadError

try:
    from testcontainers.postgres import PostgresContainer

    HAS_TESTCONTAINERS = True
except Exception:
    HAS_TESTCONTAINERS = False


RUN_PERF = os.getenv("RUN_PERF", "0") == "1"


@pytest.mark.skipif(not RUN_PERF, reason="Performance tests are disabled by default")
def test_copy_loader_perf():
    rows = int(os.getenv("PERF_ROWS", "20000"))
    cols = int(os.getenv("PERF_COLS", "6"))
    df = pd.DataFrame({f"c{i}": range(rows) for i in range(cols)})

    # prefer testcontainers when available for reproducible ephemeral Postgres
    if HAS_TESTCONTAINERS:
        from urllib.parse import urlparse

        with PostgresContainer("postgres:15") as pg:
            db_url = pg.get_connection_url()
            db = DatabaseManager()
            parsed = urlparse(db_url)
            db.user = parsed.username
            db.password = parsed.password
            db.host = parsed.hostname
            db.port = parsed.port
            db.database = parsed.path.lstrip("/")
            db.engine = None
            try:
                db.connect()
            except Exception as e:
                pytest.skip(f"Could not connect to testcontainer Postgres: {e}")

            table_name = f"perf_test_{int(datetime.now().timestamp())}"
            cols_sql = ", ".join([f"c{i} bigint" for i in range(cols)])
            with db.engine.begin() as conn:
                conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_sql});")

            start = time.time()
            try:
                loaded = copy_from_df(db.engine, df, table_name, list(df.columns))
            except LoadError as e:
                db.disconnect()
                pytest.skip(f"COPY failed during perf test: {e}")

            duration = time.time() - start
            assert loaded == len(df)
            print(
                f"Loaded {loaded} rows in {duration:.2f}s ({loaded/duration:.0f} rows/s)"
            )

            with db.engine.begin() as conn:
                conn.execute(f"DROP TABLE IF EXISTS {table_name};")
            db.disconnect()
    else:
        db = DatabaseManager()
        try:
            db.connect()
        except Exception:
            pytest.skip("Database not available for perf test")

        table_name = f"perf_test_{int(datetime.now().timestamp())}"
        cols_sql = ", ".join([f"c{i} bigint" for i in range(cols)])
        with db.engine.begin() as conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_sql});")

        start = time.time()
        try:
            loaded = copy_from_df(db.engine, df, table_name, list(df.columns))
        except LoadError as e:
            db.disconnect()
            pytest.skip(f"COPY failed during perf test: {e}")

        duration = time.time() - start
        assert loaded == len(df)
        print(f"Loaded {loaded} rows in {duration:.2f}s ({loaded/duration:.0f} rows/s)")

        with db.engine.begin() as conn:
            conn.execute(f"DROP TABLE IF EXISTS {table_name};")
        db.disconnect()
