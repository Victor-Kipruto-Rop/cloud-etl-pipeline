import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from src.reliability.runner import execute_dataset
from src.reliability.store import MetadataStore


def test_execute_dataset_publishes_layers_and_commits_checkpoint(tmp_path):
    metadata = MetadataStore(create_engine(f"sqlite:///{tmp_path / 'metadata.db'}"))
    raw = pd.DataFrame({"order_id": [1, 2], "amount": [10, 20]})
    silver = raw.copy()
    result = execute_dataset(
        raw, silver, dataset="orders", source_uri="file://orders.csv",
        source_checksum="checksum-v1", metadata_store=metadata,
        layer_root=tmp_path / "lake", file_format="csv",
        gold_dataframe=pd.DataFrame({"order_count": [2]}),
    )
    assert result["status"] == "succeeded"
    assert result["gold"] is not None
    checkpoint = metadata.get_checkpoint("orders", "file://orders.csv")
    assert checkpoint["source_checksum"] == "checksum-v1"


def test_execute_dataset_skips_an_already_committed_source(tmp_path):
    metadata = MetadataStore(create_engine(f"sqlite:///{tmp_path / 'metadata.db'}"))
    raw = pd.DataFrame({"id": [1]})
    args = dict(
        dataset="items", source_uri="file://items.csv", source_checksum="same",
        metadata_store=metadata, layer_root=tmp_path / "lake", file_format="csv",
    )
    first = execute_dataset(raw, raw, **args)
    second = execute_dataset(raw, raw, **args)
    assert first["status"] == "succeeded"
    assert second["status"] == "skipped"


def test_database_sink_failure_does_not_advance_checkpoint(tmp_path):
    metadata = MetadataStore(create_engine(f"sqlite:///{tmp_path / 'metadata.db'}"))
    warehouse = create_engine(f"sqlite:///{tmp_path / 'warehouse.db'}")
    with warehouse.begin() as conn:
        conn.execute(text("CREATE TABLE target (id INTEGER PRIMARY KEY, value TEXT)"))
    raw = pd.DataFrame({"id": [1], "value": ["ok"]})
    with pytest.raises(Exception):
        execute_dataset(
            raw, raw, dataset="target", source_uri="file://target.csv",
            source_checksum="sum", metadata_store=metadata,
            layer_root=tmp_path / "lake", database_engine=warehouse,
            target_table="missing_table", conflict_columns=("id",), file_format="csv",
        )
    assert metadata.get_checkpoint("target", "file://target.csv") is None
    assert len(metadata.list_quarantine(dataset="target")) == 1
