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
        raw,
        silver,
        dataset="orders",
        source_uri="file://orders.csv",
        source_checksum="checksum-v1",
        metadata_store=metadata,
        layer_root=tmp_path / "lake",
        file_format="csv",
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
        dataset="items",
        source_uri="file://items.csv",
        source_checksum="same",
        metadata_store=metadata,
        layer_root=tmp_path / "lake",
        file_format="csv",
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
            raw,
            raw,
            dataset="target",
            source_uri="file://target.csv",
            source_checksum="sum",
            metadata_store=metadata,
            layer_root=tmp_path / "lake",
            database_engine=warehouse,
            target_table="missing_table",
            conflict_columns=("id",),
            file_format="csv",
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
            frame,
            frame,
            dataset="customers",
            source_uri="file://customers.csv",
            source_checksum="sum",
            metadata_store=metadata,
            layer_root=tmp_path / "lake",
            file_format="csv",
            validate=reject,
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
        frame,
        frame,
        dataset="events",
        source_uri="events.csv",
        source_checksum="checksum",
        metadata_store=metadata,
        layer_root=tmp_path / "lake",
        file_format="csv",
        s3_bucket="example-data-lake",
        s3_prefix="analytics",
        aws_region="af-south-1",
    )

    assert result["status"] == "succeeded"
    assert len(uploaded) == 4
    assert all(item[1] == "example-data-lake" for item in uploaded)
    assert all(item[3] == "af-south-1" for item in uploaded)


def test_contract_version_change_reprocesses_unchanged_source(tmp_path):
    metadata = MetadataStore(create_engine(f"sqlite:///{tmp_path / 'metadata.db'}"))
    frame = pd.DataFrame({"id": [1]})
    common = dict(
        dataset="items",
        source_uri="items.csv",
        source_checksum="same-source",
        metadata_store=metadata,
        layer_root=tmp_path / "lake",
        file_format="csv",
    )
    first = execute_dataset(frame, frame, source_version="contract-v1", **common)
    second = execute_dataset(frame, frame, source_version="contract-v2", **common)

    assert first["status"] == "succeeded"
    assert second["status"] == "succeeded"
    assert first["run_id"] != second["run_id"]
    checkpoint = metadata.get_checkpoint("items", "items.csv")
    assert checkpoint["source_version"] == "contract-v2"


def test_source_and_silver_validators_receive_their_respective_frames(tmp_path):
    metadata = MetadataStore(create_engine(f"sqlite:///{tmp_path / 'metadata.db'}"))
    raw = pd.DataFrame({"Raw Name": [" Ada "]})
    silver = pd.DataFrame({"raw_name": ["ada"]})
    seen = {"source": False, "silver": False}

    def validate_source(frame):
        assert list(frame.columns) == ["Raw Name"]
        seen["source"] = True

    def validate_silver(frame):
        assert list(frame.columns) == ["raw_name"]
        assert frame.iloc[0]["raw_name"] == "ada"
        seen["silver"] = True

    result = execute_dataset(
        raw,
        dataset="customers",
        source_uri="customers.csv",
        source_checksum="source-v1",
        metadata_store=metadata,
        layer_root=tmp_path / "lake",
        file_format="csv",
        validate_source=validate_source,
        transform=lambda _: silver,
        validate=validate_silver,
    )

    assert result["status"] == "succeeded"
    assert seen == {"source": True, "silver": True}


def test_silver_validation_failure_prevents_checkpoint_commit(tmp_path):
    from src.validation import ValidationError

    metadata = MetadataStore(create_engine(f"sqlite:///{tmp_path / 'metadata.db'}"))
    raw = pd.DataFrame({"id": [1]})
    silver = pd.DataFrame({"id": [None]})

    def reject_silver(frame):
        if frame["id"].isna().any():
            raise ValidationError("silver id cannot be null")

    with pytest.raises(ValidationError, match="silver id cannot be null"):
        execute_dataset(
            raw,
            dataset="items",
            source_uri="items.csv",
            source_checksum="source-v1",
            metadata_store=metadata,
            layer_root=tmp_path / "lake",
            file_format="csv",
            transform=lambda _: silver,
            validate=reject_silver,
        )

    assert metadata.get_checkpoint("items", "items.csv") is None
    assert len(metadata.list_quarantine(dataset="items")) == 1


def test_dataset_duration_is_observed_once_for_success_and_skip(tmp_path, monkeypatch):
    from src.reliability import runner

    class DurationSpy:
        def __init__(self):
            self.observations = []

        def observe(self, value):
            self.observations.append(value)

    duration = DurationSpy()
    monkeypatch.setattr(runner, "dataset_duration", duration)
    metadata = MetadataStore(create_engine(f"sqlite:///{tmp_path / 'metadata.db'}"))
    frame = pd.DataFrame({"id": [1]})
    args = {
        "dataset": "metrics",
        "source_uri": "metrics.csv",
        "source_checksum": "same",
        "metadata_store": metadata,
        "layer_root": tmp_path / "lake",
        "file_format": "csv",
    }

    assert execute_dataset(frame, frame, **args)["status"] == "succeeded"
    assert execute_dataset(frame, frame, **args)["status"] == "skipped"
    assert len(duration.observations) == 2
