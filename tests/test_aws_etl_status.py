import pandas as pd

from src.cloud import aws_etl


def _configure_local_paths(monkeypatch, tmp_path):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    (raw_dir / "sample.csv").write_text("id\n1\n", encoding="utf-8")
    monkeypatch.setenv("RAW_DATA_DIR", str(raw_dir))
    monkeypatch.setenv("PROCESSED_DATA_DIR", str(processed_dir))
    monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("KAGGLE_DOWNLOAD", "false")
    monkeypatch.setenv("REDSHIFT_HOST", "")
    monkeypatch.setenv("REDSHIFT_DB", "")
    monkeypatch.setattr(aws_etl, "upload_directory", lambda *args, **kwargs: 1)
    return raw_dir


def test_aws_etl_returns_failure_when_a_dataset_fails(monkeypatch, tmp_path):
    _configure_local_paths(monkeypatch, tmp_path)

    def fail_extract(_):
        raise aws_etl.ExtractionError("invalid source file")

    monkeypatch.setattr(aws_etl, "extract_csv", fail_extract)

    assert aws_etl.run_aws_etl() is False


def test_aws_etl_returns_success_after_all_sinks_complete(monkeypatch, tmp_path):
    _configure_local_paths(monkeypatch, tmp_path)
    frame = pd.DataFrame({"id": [1]})
    monkeypatch.setattr(aws_etl, "extract_csv", lambda _: frame)
    monkeypatch.setattr(aws_etl, "transform", lambda data, **kwargs: data)
    monkeypatch.setattr(aws_etl, "write_dataframe_atomic", lambda *args, **kwargs: None)
    monkeypatch.setattr(aws_etl, "upload_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        aws_etl, "upload_dataframe_as_parquet", lambda *args, **kwargs: None
    )

    assert aws_etl.run_aws_etl() is True
