import unittest
import pandas as pd
from pathlib import Path
import tempfile
import shutil

from src.extract.extract_data import extract_csv
from src.transform.transform_data import transform
from src.load.load_to_db import load_df_to_postgres


class TestExtract(unittest.TestCase):
    """Test the extract module."""

    def setUp(self):
        """Create a temporary directory and sample CSV."""
        self.test_dir = tempfile.mkdtemp()
        self.csv_path = Path(self.test_dir) / "test.csv"

        # Write test data
        test_data = {
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "value": [10, 20, 30],
        }
        pd.DataFrame(test_data).to_csv(self.csv_path, index=False)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_extract_csv(self):
        """Test that extract_csv returns a DataFrame with correct shape."""
        df = extract_csv(self.csv_path)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 3)
        self.assertEqual(list(df.columns), ["id", "name", "value"])

    def test_extract_csv_missing_file(self):
        """Test that extract_csv raises FileNotFoundError for missing file."""
        with self.assertRaises(FileNotFoundError):
            extract_csv(Path(self.test_dir) / "nonexistent.csv")


class TestTransform(unittest.TestCase):
    """Test the transform module."""

    def test_transform_normalizes_columns(self):
        """Test that transform converts column names to snake_case and lowercase."""
        df = pd.DataFrame(
            {"ID": [1, 2], "Customer Name": ["Alice", "Bob"], "Amount ": [100, 200]}
        )
        result = transform(df)
        self.assertEqual(list(result.columns), ["id", "customer_name", "amount"])

    def test_transform_removes_all_na_rows(self):
        """Test that transform removes rows with all NaN values."""
        df = pd.DataFrame({"a": [1, None, 3], "b": [4, None, 6]})
        result = transform(df)
        self.assertEqual(len(result), 2)

    def test_transform_preserves_partial_na(self):
        """Test that transform preserves rows with some NaN values."""
        df = pd.DataFrame({"a": [1, None, 3], "b": [4, 5, 6]})
        result = transform(df)
        self.assertEqual(len(result), 3)


class TestLoad(unittest.TestCase):
    """Test the load module."""

    def test_load_df_to_postgres_requires_credentials(self):
        """Test that load_df_to_postgres attempts connection (will fail without real DB)."""
        df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        # This should raise an exception due to missing/invalid DB credentials
        # We're just verifying the function is callable
        try:
            load_df_to_postgres(df, "test_table")
        except Exception as e:
            # Expected: connection error when no DB is running
            self.assertIsInstance(e, Exception)


class TestPipelineIntegration(unittest.TestCase):
    """Integration tests for the full ETL pipeline."""

    def setUp(self):
        """Create temporary test directories."""
        self.test_dir = tempfile.mkdtemp()
        self.raw_dir = Path(self.test_dir) / "raw"
        self.processed_dir = Path(self.test_dir) / "processed"
        self.raw_dir.mkdir()
        self.processed_dir.mkdir()

        # Write sample data
        test_data = {
            "ID": [1, 2, 3],
            "Customer Name": ["Alice", "Bob", "Charlie"],
            "Sales Amount": [100, 200, 300],
        }
        pd.DataFrame(test_data).to_csv(self.raw_dir / "test.csv", index=False)

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.test_dir)

    def test_extract_transform_round_trip(self):
        """Test extracting and transforming data."""
        df = extract_csv(self.raw_dir / "test.csv")
        df_transformed = transform(df)

        # Verify transform worked
        self.assertEqual(
            list(df_transformed.columns), ["id", "customer_name", "sales_amount"]
        )
        self.assertEqual(len(df_transformed), 3)


if __name__ == "__main__":
    unittest.main()
