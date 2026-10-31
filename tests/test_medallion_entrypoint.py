from sqlalchemy import create_engine

from src.reliability.entrypoint import run_medallion_files
from src.reliability.store import MetadataStore


def test_medallion_entrypoint_runs_and_skips_unchanged_source(tmp_path, monkeypatch):
    source = tmp_path / "orders.csv"
    source.write_text("order_id,amount\n1,20\n2,30\n", encoding="utf-8")
    metadata_path = tmp_path / "metadata.db"
    monkeypatch.setenv("METADATA_DATABASE_URL", f"sqlite:///{metadata_path}")
    monkeypatch.delenv("DATABASE_URL", raising=False)
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
