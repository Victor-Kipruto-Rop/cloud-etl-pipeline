"""Kaggle dataset download helper for the ETL pipeline."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Use a sentinel to distinguish uninitialized KaggleApi from an explicit None
# (the latter is used by tests to force a package-missing error).
_KAGGLE_API_NOT_LOADED = object()
KaggleApi = _KAGGLE_API_NOT_LOADED  # type: ignore


def _load_kaggle_api():
    global KaggleApi
    if KaggleApi is _KAGGLE_API_NOT_LOADED:
        try:
            from kaggle.api.kaggle_api_extended import KaggleApi as _KaggleApi

            KaggleApi = _KaggleApi
        except Exception as exc:
            raise KaggleDownloadError(
                "The 'kaggle' package is required for Kaggle integration. "
                "Install it with `pip install kaggle`."
            ) from exc
    return KaggleApi


class KaggleDownloadError(Exception):
    """Raised when Kaggle dataset download fails."""


def download_kaggle_dataset(
    dataset: str,
    destination: Path,
    unzip: bool = True,
    force: bool = False,
    quiet: bool = True,
    file_pattern: str = "*.csv",
) -> Path:
    """Download a Kaggle dataset into the local raw data directory.

    Args:
        dataset: Kaggle dataset slug in the form owner/dataset-name.
        destination: Directory where files are saved.
        unzip: Whether to unzip downloaded dataset files.
        force: Whether to overwrite existing downloads.
        quiet: Suppress Kaggle download output.
        file_pattern: Glob pattern used to validate downloaded files.

    Returns:
        The destination path where files were downloaded.

    Raises:
        KaggleDownloadError: If the Kaggle API is not installed or download fails.
    """
    # If the module-level KaggleApi is explicitly patched to None in tests,
    # or the package is unavailable, raise an explicit error.
    if KaggleApi is None:
        raise KaggleDownloadError(
            "The 'kaggle' package is required for Kaggle integration. "
            "Install it with `pip install kaggle`."
        )
    if KaggleApi is _KAGGLE_API_NOT_LOADED:
        _load_kaggle_api()

    if not dataset or "/" not in dataset:
        raise KaggleDownloadError(
            "KAGGLE_DATASET must be set to the Kaggle dataset slug in the form "
            "owner/dataset-name."
        )

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    try:
        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(
            dataset,
            path=str(destination),
            unzip=unzip,
            force=force,
            quiet=quiet,
        )
    except Exception as exc:
        logger.error(f"Kaggle download failed: {exc}")
        raise KaggleDownloadError(
            f"Kaggle dataset download failed for '{dataset}': {exc}"
        ) from exc

    matching_files = list(destination.glob(file_pattern))
    if not matching_files:
        raise KaggleDownloadError(
            f"Downloaded dataset did not contain files matching '{file_pattern}'. "
            "Verify KAGGLE_DATASET and KAGGLE_FILE_PATTERN."
        )

    logger.info(
        f"Downloaded Kaggle dataset '{dataset}' to {destination} ({len(matching_files)} matching files)"
    )
    return destination
