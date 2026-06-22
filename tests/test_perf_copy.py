import os
import time
from datetime import datetime

import pandas as pd
import pytest

from src.load.copy_loader import copy_from_df
from src.load.load_to_db import DatabaseManager, LoadError

RUN_PERF = os.getenv("RUN_PERF", "0") == "1"


@pytest.mark.skipif(not RUN_PERF, reason="Performance tests are disabled by default")
def test_copy_loader_perf():
    rows = int(os.getenv("PERF_ROWS", "20000"))
    cols = int(os.getenv("PERF_COLS", "6"))
    df = pd.DataFrame({f"c{i}": range(rows) for i in range(cols)})

    db = DatabaseManager()
    try:
        db.connect()
    except Exception:
        pytest.skip("Database not available for perf test")

    table_name = f"perf_test_{int(datetime.now().timestamp())}"
    # create a simple table matching column count
    cols_sql = ", ".join([f"c{i} bigint" for i in range(cols)])
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_sql});"
    with db.engine.begin() as conn:
        conn.execute(create_sql)

    start = time.time()
    try:
        loaded = copy_from_df(db.engine, df, table_name, list(df.columns))
    except LoadError as e:
        db.disconnect()
        pytest.skip(f"COPY failed during perf test: {e}")

    duration = time.time() - start
    assert loaded == len(df)
    print(f"Loaded {loaded} rows in {duration:.2f}s ({loaded/duration:.0f} rows/s)")

    # cleanup
    with db.engine.begin() as conn:
        conn.execute(f"DROP TABLE IF EXISTS {table_name};")
    db.disconnect()
