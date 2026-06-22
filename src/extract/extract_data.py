"""
Robust data extraction module with advanced features.
Supports multiple formats, encoding detection, chunking, and validation.
"""

from pathlib import Path
import pandas as pd
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when extraction fails."""

    pass


class ExtractionStats:
    """Track extraction statistics."""

    def __init__(self):
        self.file_size_mb = 0.0
        self.rows_extracted = 0
        self.columns_extracted = 0
        self.encoding_detected = None
        self.duration_seconds = 0.0
        self.warnings = []

    def report(self) -> str:
        """Generate extraction report."""
        report = f"""
╔════════════════════════════════════════╗
║      EXTRACTION STATISTICS             ║
╠════════════════════════════════════════╣
║ File size:        {self.file_size_mb:>8.2f} MB    ║
║ Rows extracted:   {self.rows_extracted:>8,d}       ║
║ Columns:          {self.columns_extracted:>8,d}       ║
║ Encoding:         {str(self.encoding_detected or 'utf-8'):>8s}     ║
║ Duration:         {self.duration_seconds:>8.2f}s     ║
║ Warnings:         {len(self.warnings):>8,d}       ║
╚════════════════════════════════════════╝"""
        return report


class DataExtractor:
    """Advanced data extractor supporting multiple formats and encodings."""

    def __init__(self, encoding: Optional[str] = None):
        self.encoding = encoding
        self.stats = None

    def validate_file(self, file_path: Path) -> None:
        """
        Validate file exists and is readable.

        Args:
            file_path: Path to validate

        Raises:
            ExtractionError: If validation fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ExtractionError(f"Path is not a file: {file_path}")

        if not file_path.stat().st_size > 0:
            raise ExtractionError(f"File is empty: {file_path}")

    def extract_csv(
        self,
        file_path: Path,
        encoding: Optional[str] = "utf-8",
        delimiter: str = ",",
        chunksize: Optional[int] = None,
        dtype: Optional[Dict[str, Any]] = None,
        parse_dates: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Extract data from CSV with robust error handling.

        Args:
            file_path: Path to CSV file
            encoding: File encoding (default: utf-8)
            delimiter: CSV delimiter (default: ,)
            chunksize: Rows per chunk for large files (None = full load)
            dtype: Column data types
            parse_dates: Columns to parse as dates

        Returns:
            pd.DataFrame: Extracted data

        Raises:
            ExtractionError: If extraction fails
        """
        start_time = datetime.now()
        self.stats = ExtractionStats()
        file_path = Path(file_path)

        try:
            logger.info(f"{'='*70}")
            logger.info(f"EXTRACTING: {file_path.name}")
            logger.info(f"{'='*70}")

            # Validate file
            self.validate_file(file_path)

            # Get file size
            self.stats.file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"File size: {self.stats.file_size_mb:.2f} MB")
            self.stats.encoding_detected = encoding

            # Handle large files with chunking
            if chunksize and self.stats.file_size_mb > 50:
                logger.info(f"Using chunked reading (chunk size: {chunksize})")
                chunks = []
                for chunk in pd.read_csv(
                    file_path,
                    encoding=encoding,
                    delimiter=delimiter,
                    dtype=dtype,
                    parse_dates=parse_dates,
                    chunksize=chunksize,
                    on_bad_lines="warn",
                    engine="c",
                ):
                    chunks.append(chunk)
                df = pd.concat(chunks, ignore_index=True)
                logger.info(f"Concatenated {len(chunks)} chunks")
            else:
                # Load entire file
                logger.info("Loading file into memory...")
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    delimiter=delimiter,
                    dtype=dtype,
                    parse_dates=parse_dates,
                    on_bad_lines="warn",
                    engine="c",
                )

            # Validate extracted data
            if df.empty:
                logger.warning("Extracted DataFrame is empty!")
                self.stats.warnings.append("Empty DataFrame")

            self.stats.rows_extracted = len(df)
            self.stats.columns_extracted = len(df.columns)
            self.stats.duration_seconds = (datetime.now() - start_time).total_seconds()

            logger.info(self.stats.report())
            logger.info(
                f"✓ Extraction successful in {self.stats.duration_seconds:.2f}s"
            )

            return df

        except UnicodeDecodeError as e:
            msg = f"Encoding error ({encoding}): {e}"
            logger.error(msg)
            raise ExtractionError(msg) from e
        except pd.errors.ParserError as e:
            msg = f"CSV parse error: {e}"
            logger.error(msg)
            raise ExtractionError(msg) from e
        except FileNotFoundError:
            # Let FileNotFoundError propagate for callers/tests that expect it
            raise
        except ExtractionError:
            raise
        except Exception as e:
            msg = f"Unexpected extraction error: {e}"
            logger.error(msg)
            raise ExtractionError(msg) from e


def extract_csv(path: Path, **kwargs) -> pd.DataFrame:
    """Convenience function for CSV extraction."""
    extractor = DataExtractor()
    return extractor.extract_csv(path, **kwargs)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.extract.extract_data <csv_file>")
        sys.exit(1)

    df = extract_csv(Path(sys.argv[1]), chunksize=10000)
    print(f"\nExtracted:\n{df.head()}")
    print(f"\nData types:\n{df.dtypes}")
