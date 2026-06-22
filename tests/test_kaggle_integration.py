import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.extract.kaggle_data import KaggleDownloadError, download_kaggle_dataset


class TestKaggleIntegration(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.destination = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    @patch("src.extract.kaggle_data.KaggleApi")
    def test_download_kaggle_dataset_success(self, MockKaggleApi):
        api_instance = MagicMock()
        MockKaggleApi.return_value = api_instance

        def fake_download_files(dataset, path, unzip, force, quiet):
            target = Path(path) / "sample.csv"
            target.write_text("id,name\n1,Alice\n")

        api_instance.authenticate.return_value = None
        api_instance.dataset_download_files.side_effect = fake_download_files

        result = download_kaggle_dataset(
            dataset="owner/dataset-name",
            destination=self.destination,
            unzip=True,
            force=False,
            quiet=True,
            file_pattern="*.csv",
        )

        self.assertEqual(result, self.destination)
        self.assertTrue((self.destination / "sample.csv").exists())
        api_instance.authenticate.assert_called_once()
        api_instance.dataset_download_files.assert_called_once()

    @patch("src.extract.kaggle_data.KaggleApi", None)
    def test_download_kaggle_dataset_requires_package(self):
        with self.assertRaises(KaggleDownloadError):
            download_kaggle_dataset(
                dataset="owner/dataset-name",
                destination=self.destination,
            )

    @patch("src.extract.kaggle_data.KaggleApi")
    def test_download_kaggle_dataset_invalid_slug(self, MockKaggleApi):
        api_instance = MagicMock()
        MockKaggleApi.return_value = api_instance
        api_instance.authenticate.return_value = None
        api_instance.dataset_download_files.return_value = None

        with self.assertRaises(KaggleDownloadError):
            download_kaggle_dataset(dataset="invalidslug", destination=self.destination)


if __name__ == "__main__":
    unittest.main()
