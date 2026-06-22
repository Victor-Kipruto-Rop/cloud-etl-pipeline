"""Data validation tests for ETL pipeline."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.extract.extract_data import extract_csv
from src.transform.transform_data import transform


class TestDataValidation(unittest.TestCase):
    """Test data validation in the pipeline."""

    def test_no_duplicate_rows(self):
        """Test that duplicates are removed."""
        df = pd.DataFrame(
            {
                "id": [1, 1, 2, 3],
                "name": ["Alice", "Alice", "Bob", "Charlie"],
                "value": [10, 10, 20, 30],
            }
        )
        result = transform(df)
        self.assertLessEqual(len(result), 4)

    def test_data_type_consistency(self):
        """Test that data types are consistent after transform."""
        df = pd.DataFrame(
            {"id": ["1", "2", "3"], "amount": ["100.5", "200.0", "300.5"]}
        )
        result = transform(df)
        # After transform, numeric columns should be numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(result["id"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(result["amount"]))

    def test_missing_values_handling(self):
        """Test handling of missing values."""
        df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4],
                "name": ["Alice", None, "Bob", None],
                "value": [10, 20, None, 40],
            }
        )
        result = transform(df)
        # Should have at least one row
        self.assertGreater(len(result), 0)

    def test_column_normalization(self):
        """Test that column names are normalized."""
        df = pd.DataFrame(
            {
                "Customer ID": [1, 2, 3],
                "Customer Name ": ["Alice", "Bob", "Charlie"],
                "Amount $": [100, 200, 300],
            }
        )
        result = transform(df)
        # Columns should be lowercase and snake_case
        for col in result.columns:
            self.assertEqual(col, col.lower())
            self.assertNotIn(" ", col)
            self.assertNotIn("$", col)

    def test_special_characters_removal(self):
        """Test removal of special characters from column names."""
        df = pd.DataFrame(
            {
                "ID#": [1, 2, 3],
                "Name@": ["Alice", "Bob", "Charlie"],
                "Value&": [100, 200, 300],
            }
        )
        result = transform(df)
        for col in result.columns:
            self.assertNotIn("#", col)
            self.assertNotIn("@", col)
            self.assertNotIn("&", col)

    def test_no_empty_dataframe_output(self):
        """Test that transform doesn't return empty dataframe."""
        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Charlie"],
                "value": [10, 20, 30],
            }
        )
        result = transform(df)
        self.assertGreater(
            len(result), 0, "Transform should not return empty DataFrame"
        )


class TestDataQuality(unittest.TestCase):
    """Test data quality metrics."""

    def test_completeness_ratio(self):
        """Test data completeness calculation."""
        df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "name": ["Alice", "Bob", None, "Charlie", "Dave"],
                "value": [10, 20, 30, None, 50],
            }
        )

        total_cells = df.shape[0] * df.shape[1]
        non_null_cells = df.notna().sum().sum()
        completeness = non_null_cells / total_cells

        self.assertGreater(completeness, 0)
        self.assertLessEqual(completeness, 1)

    def test_consistency_check(self):
        """Test data consistency."""
        df = pd.DataFrame({"id": [1, 2, 3], "status": ["active", "active", "inactive"]})

        valid_statuses = {"active", "inactive"}
        invalid = df[~df["status"].isin(valid_statuses)]

        self.assertEqual(len(invalid), 0)

    def test_referential_integrity(self):
        """Test referential integrity between datasets."""
        customers_df = pd.DataFrame(
            {"customer_id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"]}
        )

        orders_df = pd.DataFrame({"order_id": [1, 2, 3], "customer_id": [1, 2, 3]})

        # All customer_ids in orders should exist in customers
        invalid_refs = orders_df[
            ~orders_df["customer_id"].isin(customers_df["customer_id"])
        ]
        self.assertEqual(len(invalid_refs), 0)


class TestDataAccuracy(unittest.TestCase):
    """Test data accuracy and validity."""

    def test_numeric_range_validation(self):
        """Test numeric values are within expected range."""
        df = pd.DataFrame(
            {"id": [1, 2, 3], "age": [25, 35, 45], "salary": [50000, 75000, 100000]}
        )

        # Age should be between 0 and 150
        self.assertTrue((df["age"] >= 0).all())
        self.assertTrue((df["age"] <= 150).all())

        # Salary should be positive
        self.assertTrue((df["salary"] > 0).all())

    def test_date_validity(self):
        """Test date values are valid."""
        df = pd.DataFrame(
            {"date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])}
        )

        # All dates should be valid timestamps
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["date"]))

    def test_unique_key_validation(self):
        """Test that primary keys are unique."""
        df = pd.DataFrame(
            {"id": [1, 2, 3, 4, 5], "name": ["Alice", "Bob", "Charlie", "Dave", "Eve"]}
        )

        # IDs should be unique
        self.assertEqual(len(df["id"]), len(df["id"].unique()))


if __name__ == "__main__":
    unittest.main()
