import unittest
from pathlib import Path
import tempfile
import pandas as pd
from src.dashboard import generate_dashboard


class TestDashboardGeneration(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.processed_dir = Path(self.tempdir.name) / "processed"
        self.processed_dir.mkdir(parents=True)
        self.df = pd.DataFrame(
            {
                "year": [2020, 2021],
                "make": ["Ford", "Tesla"],
                "model": ["F-150", "Model 3"],
                "state": ["CA", "TX"],
                "condition": ["good", "excellent"],
                "mmr": [20000, 35000],
                "sellingprice": [21000, 36000],
                "seller": ["Alpha", "Beta"],
            }
        )
        self.df.to_csv(self.processed_dir / "car_prices.csv", index=False)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_generate_dashboard_creates_files(self):
        output = Path(self.tempdir.name) / "visualizations"
        result = generate_dashboard(self.processed_dir, output)
        self.assertTrue((output / "dashboard.html").exists())
        for chart in result["charts"]:
            self.assertTrue(chart.exists())
        self.assertEqual(result["summary"]["processed_rows"], 2)

    def test_generate_dashboard_missing_dir(self):
        missing_dir = Path(self.tempdir.name) / "missing"
        with self.assertRaises(FileNotFoundError):
            generate_dashboard(missing_dir, Path(self.tempdir.name) / "visualizations2")


if __name__ == "__main__":
    unittest.main()
