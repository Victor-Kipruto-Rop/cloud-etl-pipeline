from pathlib import Path

import pandas as pd
import pytest

from src.io_utils import DataWriteError, write_dataframe_atomic


def test_atomic_csv_write_creates_parent_and_round_trips(tmp_path: Path):
    destination = tmp_path / "nested" / "output.csv"
    frame = pd.DataFrame({"id": [1, 2], "amount": [10.5, 20.0]})

    result = write_dataframe_atomic(frame, destination)

    assert result == destination
    pd.testing.assert_frame_equal(pd.read_csv(destination), frame)


def test_atomic_parquet_write_round_trips(tmp_path: Path):
    destination = tmp_path / "output.parquet"
    frame = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})

    write_dataframe_atomic(frame, destination, compression="snappy")

    pd.testing.assert_frame_equal(pd.read_parquet(destination), frame)


def test_failed_write_preserves_previous_output(tmp_path: Path, monkeypatch):
    destination = tmp_path / "output.csv"
    destination.write_text("original\nvalue\n", encoding="utf-8")

    def fail_write(self, *args, **kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_write)
    with pytest.raises(DataWriteError):
        write_dataframe_atomic(pd.DataFrame({"new": [1]}), destination)

    assert destination.read_text(encoding="utf-8") == "original\nvalue\n"
    assert list(tmp_path.glob(".output.*.csv")) == []


def test_unsupported_format_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="Unsupported dataset format"):
        write_dataframe_atomic(pd.DataFrame({"id": [1]}), tmp_path / "output.json")
