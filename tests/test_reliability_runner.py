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
    assert metadata.list_quarantine(dataset="target") == []


def test_data_quality_failure_is_quarantined(tmp_path):
    from src.validation import ValidationError

    metadata = MetadataStore(create_engine(f"sqlite:///{tmp_path / 'metadata.db'}"))
    frame = pd.DataFrame({"id": [1]})

    def reject(_):
        raise ValidationError("missing required customer key")

    with pytest.raises(ValidationError):
        execute_dataset(
            frame, frame, dataset="customers", source_uri="file://customers.csv",
            source_checksum="sum", metadata_store=metadata,
            layer_root=tmp_path / "lake", file_format="csv", validate=reject,
        )

    assert metadata.get_checkpoint("customers", "file://customers.csv") is None
    assert len(metadata.list_quarantine(dataset="customers")) == 1


def test_s3_layer_uploads_are_part_of_successful_run(tmp_path, monkeypatch):
    from src.reliability import runner

    metadata = MetadataStore(create_engine(f"sqlite:///{tmp_path / 'metadata.db'}"))
    frame = pd.DataFrame({"id": [1]})
    uploaded = []

    def fake_upload(path, bucket, key, region_name=None):
        uploaded.append((str(path), bucket, key, region_name))
        return f"s3://{bucket}/{key}"

    monkeypatch.setattr(runner, "upload_file", fake_upload)
    result = execute_dataset(
        frame, frame, dataset="events", source_uri="events.csv",
        source_checksum="checksum", metadata_store=metadata,
        layer_root=tmp_path / "lake", file_format="csv",
        s3_bucket="example-data-lake", s3_prefix="analytics",
        aws_region="af-south-1",
    )

    assert result["status"] == "succeeded"
    assert len(uploaded) == 4
    assert all(item[1] == "example-data-lake" for item in uploaded)
    assert all(item[3] == "af-south-1" for item in uploaded)
