from sqlalchemy import create_engine

from src.reliability.entrypoint import run_medallion_files
from src.reliability.store import MetadataStore


def test_medallion_entrypoint_runs_and_skips_unchanged_source(tmp_path, monkeypatch):
    source = tmp_path / "orders.csv"
    source.write_text("order_id,amount\n1,20\n2,30\n", encoding="utf-8")
    metadata_path = tmp_path / "metadata.db"
    monkeypatch.setenv("METADATA_DATABASE_URL", f"sqlite:///{metadata_path}")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    monkeypatch.delenv("DATA_QUALITY_CONTRACT_PATH", raising=False)
    monkeypatch.delenv("UPSERT_KEY_COLUMNS", raising=False)
    monkeypatch.setenv("MEDALLION_FILE_FORMAT", "csv")
    monkeypatch.setenv("REQUIRED_COLUMNS", "order_id,amount")

    layer_root = tmp_path / "lake"
    assert run_medallion_files([source], layer_root=layer_root) is True
    assert run_medallion_files([source], layer_root=layer_root) is True

    store = MetadataStore(create_engine(f"sqlite:///{metadata_path}"))
    checkpoint = store.get_checkpoint("orders", str(source.resolve()))
    assert checkpoint is not None
    assert checkpoint["source_checksum"]
    assert list(layer_root.glob("bronze/orders/**/data.csv"))
    assert list(layer_root.glob("silver/orders/**/data.csv"))


def test_extraction_failure_is_recorded_and_quarantined(tmp_path, monkeypatch):
    from src.reliability import entrypoint

    source = tmp_path / "broken.csv"
    source.write_text("not,a,valid,csv\n", encoding="utf-8")
    metadata_path = tmp_path / "metadata.db"
    monkeypatch.setenv("METADATA_DATABASE_URL", f"sqlite:///{metadata_path}")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    monkeypatch.delenv("DATA_QUALITY_CONTRACT_PATH", raising=False)
    def fail_extract(_):
        raise ValueError("invalid CSV source")

    monkeypatch.setattr(entrypoint, "extract_csv", fail_extract)

    assert run_medallion_files([source], layer_root=tmp_path / "lake") is False
    store = MetadataStore(create_engine(f"sqlite:///{metadata_path}"))
    records = store.list_quarantine(dataset="broken")
    assert len(records) == 1
    assert records[0]["reason_code"] == "SOURCE_EXTRACTION_FAILURE"
