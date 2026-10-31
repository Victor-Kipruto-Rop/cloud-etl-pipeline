import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from src.load.idempotent import IdempotentLoadError, upsert_dataframe


def test_upsert_is_idempotent_and_updates_existing_rows(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'warehouse.db'}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE customers ("
                "customer_id INTEGER PRIMARY KEY, name TEXT, city TEXT)"
            )
        )
        conn.execute(text("INSERT INTO customers VALUES (1, 'Old', 'Nairobi')"))
    frame = pd.DataFrame(
        [
            {"customer_id": 1, "name": "Updated", "city": "Mombasa"},
            {"customer_id": 2, "name": "New", "city": "Kisumu"},
            {"customer_id": 2, "name": "Newest", "city": "Nakuru"},
        ]
    )
    assert (
        upsert_dataframe(
            engine, frame, table_name="customers", conflict_columns=["customer_id"]
        )
        == 2
    )
    assert (
        upsert_dataframe(
            engine, frame, table_name="customers", conflict_columns=["customer_id"]
        )
        == 2
    )
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT customer_id, name, city FROM customers ORDER BY customer_id")
        ).all()
    assert rows == [(1, "Updated", "Mombasa"), (2, "Newest", "Nakuru")]


def test_upsert_rejects_unsafe_identifiers_and_unknown_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'warehouse.db'}")
    with engine.begin() as conn:
        conn.execute(
            text("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT)")
        )
    with pytest.raises(ValueError):
        upsert_dataframe(
            engine,
            pd.DataFrame({"customer_id": [1]}),
            table_name="customers;drop",
            conflict_columns=["customer_id"],
        )
    with pytest.raises(IdempotentLoadError):
        upsert_dataframe(
            engine,
            pd.DataFrame({"customer_id": [1], "secret": ["x"]}),
            table_name="customers",
            conflict_columns=["customer_id"],
        )
