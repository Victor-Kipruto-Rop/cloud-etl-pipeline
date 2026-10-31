import pandas as pd
import pytest

from src.layers import read_manifest, write_layer


def test_write_bronze_layer_creates_manifest_and_checksum(tmp_path):
    frame = pd.DataFrame({"id": [1, 2], "value": ["a", "b"]})
    result = write_layer(frame, root=tmp_path, layer="bronze", dataset="orders",
                         run_id="run-001", ingestion_date="2026-10-31",
                         file_format="csv", source_uri="s3://bucket/orders.csv")
    manifest = read_manifest(result["manifest_path"])
    assert manifest["row_count"] == 2
    assert manifest["sha256"] == result["sha256"]
    assert manifest["layer"] == "bronze"


def test_layer_outputs_are_immutable_per_run(tmp_path):
    frame = pd.DataFrame({"id": [1]})
    args = dict(root=tmp_path, layer="silver", dataset="orders", run_id="run-1",
                file_format="csv")
    write_layer(frame, **args)
    with pytest.raises(FileExistsError):
        write_layer(frame, **args)


def test_layer_rejects_unsafe_names(tmp_path):
    with pytest.raises(ValueError):
        write_layer(pd.DataFrame({"id": [1]}), root=tmp_path, layer="bronze",
                    dataset="../escape", run_id="run-1", file_format="csv")
