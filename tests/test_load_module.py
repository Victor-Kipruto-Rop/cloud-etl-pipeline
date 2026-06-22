import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from src.load.load_to_db import load_df_to_postgres, DatabaseManager, LoadError


class TestLoadModule(unittest.TestCase):
    def test_invalid_inputs(self):
        with self.assertRaises(LoadError):
            load_df_to_postgres("not a df", "table")

        with self.assertRaises(LoadError):
            load_df_to_postgres(pd.DataFrame(), None)

        with self.assertRaises(LoadError):
            load_df_to_postgres(pd.DataFrame({'a': [1]}), 't', if_exists='invalid')

    def test_empty_dataframe_returns_zero(self):
        df = pd.DataFrame()
        rows = load_df_to_postgres(df, 'table')
        self.assertEqual(rows, 0)

    @patch('src.load.load_to_db.DatabaseManager')
    def test_successful_load_calls_to_sql(self, MockDBManager):
        df = pd.DataFrame({'id': [1, 2, 3]})

        # Setup mock DB manager instance
        mock_mgr = MockDBManager.return_value
        mock_mgr.connect.return_value = None
        mock_mgr.table_exists.return_value = True
        mock_mgr.get_table_info.return_value = {'columns': ['id']}
        mock_mgr.engine = MagicMock()

        # Patch DataFrame.to_sql to avoid real DB operations
        with patch.object(pd.DataFrame, 'to_sql', return_value=None) as mock_to_sql:
            rows = load_df_to_postgres(df, 'test_table', if_exists='append', chunk_size=2)

        self.assertEqual(rows, 3)
        mock_mgr.connect.assert_called_once()


if __name__ == '__main__':
    unittest.main()
