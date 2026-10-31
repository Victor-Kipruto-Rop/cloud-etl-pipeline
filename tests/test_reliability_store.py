import json

import pytest
from sqlalchemy import create_engine

from src.reliability.store import MetadataStore


def test_checkpoint_advances_only_after_success(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'metadata.db'}")
    store = MetadataStore(engine)
    run_id = store.start_run("orders", "s3://bucket/orders.csv", "abc123")
    assert store.get_checkpoint("orders", "s3://bucket/orders.csv") is None
    store.finish_run(run_id, rows_read=12, rows_written=12)
    checkpoint = store.get_checkpoint("orders", "s3://bucket/orders.csv")
    assert checkpoint["source_checksum"] == "abc123"
    assert checkpoint["committed_run_id"] == run_id
    assert store.get_run(run_id)["status"] == "succeeded"


def test_failed_run_does_not_advance_checkpoint(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'metadata.db'}")
    store = MetadataStore(engine)
    run_id = store.start_run("orders", "file.csv", "checksum")
    store.fail_run(run_id, "database unavailable")
    assert store.get_checkpoint("orders", "file.csv") is None
    assert store.get_run(run_id)["status"] == "failed"


def test_quarantine_and_lineage_are_persisted(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'metadata.db'}")
    store = MetadataStore(engine)
    run_id = store.start_run("orders", "file.csv", "checksum")
    record_id = store.quarantine_record(
        run_id, "orders", "file.csv", "INVALID_AMOUNT",
        "amount must be positive", {"order_id": 7, "amount": -2},
    )
    event_id = store.record_lineage(
        run_id, "orders", "artifact_created",
        parent_uri="file.csv", child_uri="bronze/orders/data.parquet",
        details={"rows": 1},
    )
    assert event_id
    pending = store.list_quarantine(dataset="orders")
    assert len(pending) == 1
    assert json.loads(pending[0]["payload_json"])["order_id"] == 7
    replay_run = store.start_run("orders", "replayed-file.csv", "new-checksum")
    store.finish_run(replay_run, rows_read=1, rows_written=1)
    store.mark_replayed(record_id, replay_run)
    assert store.list_quarantine(dataset="orders") == []


def test_run_state_cannot_be_completed_twice(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'metadata.db'}")
    store = MetadataStore(engine)
    run_id = store.start_run("orders")
    store.finish_run(run_id, rows_read=1, rows_written=1)
    with pytest.raises(ValueError):
        store.finish_run(run_id, rows_read=1, rows_written=1)
