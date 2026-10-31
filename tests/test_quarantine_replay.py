from sqlalchemy import create_engine

from src.reliability.replay import restore_quarantined_file
from src.reliability.store import MetadataStore


def test_restore_quarantined_file_does_not_mark_it_replayed(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text("id,value\n1,-5\n", encoding="utf-8")
    store = MetadataStore(create_engine(f"sqlite:///{tmp_path / 'metadata.db'}"))
    run_id = store.start_run("dataset")
    record_id = store.quarantine_record(
        run_id, "dataset", str(source), "DATA_QUALITY_FAILURE",
        "value must be non-negative", {"source": str(source)},
    )

    restored = restore_quarantined_file(store, record_id, tmp_path / "replay")
    assert restored.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert store.list_quarantine(dataset="dataset")[0]["status"] == "pending"
