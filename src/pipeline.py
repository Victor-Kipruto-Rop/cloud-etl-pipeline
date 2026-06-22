import os
from pathlib import Path
import logging
import sys
from datetime import datetime
import traceback
from dotenv import load_dotenv

from src.extract.extract_data import extract_csv, ExtractionError
from src.transform.transform_data import transform, TransformError
from src.load.load_to_db import load_df_to_postgres, LoadError
from src.dashboard import generate_dashboard

# Load environment variables from .env file
load_dotenv()

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "pipeline.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


class PipelineStats:
    """Track pipeline execution statistics."""

    def __init__(self):
        self.files_processed = 0
        self.files_failed = 0
        self.rows_extracted = 0
        self.rows_transformed = 0
        self.rows_loaded = 0
        self.errors = []

    def log_stats(self):
        """Log final statistics."""
        logger.info("=" * 80)
        logger.info("PIPELINE EXECUTION STATISTICS")
        logger.info(f"Files processed: {self.files_processed}")
        logger.info(f"Files failed: {self.files_failed}")
        logger.info(f"Total rows extracted: {self.rows_extracted}")
        logger.info(f"Total rows transformed: {self.rows_transformed}")
        logger.info(f"Total rows loaded: {self.rows_loaded}")

        if self.errors:
            logger.warning(f"\nEncountered {len(self.errors)} errors:")
            for error in self.errors:
                logger.warning(f"  - {error}")

        logger.info("=" * 80)


def process_file(csv_file: Path, stats: PipelineStats, max_retries: int = 3) -> bool:
    """
    Process a single CSV file through the ETL pipeline with retry logic.

    Args:
        csv_file: Path to CSV file
        stats: Pipeline statistics tracker
        max_retries: Number of retry attempts

    Returns:
        bool: True if successful, False if failed
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {csv_file.name}")
    logger.info(f"{'='*60}")

    for attempt in range(1, max_retries + 1):
        try:
            # Extract
            logger.info(f"[Attempt {attempt}/{max_retries}] Extracting...")
            df = extract_csv(csv_file)
            stats.rows_extracted += len(df)

            # Transform
            logger.info("Transforming...")
            df_transformed = transform(
                df, normalize_cols=True, handle_missing="drop_all"
            )
            stats.rows_transformed += len(df_transformed)

            # Save processed file
            out_file = PROCESSED_DIR / csv_file.name
            logger.info(f"Saving to {out_file}...")
            df_transformed.to_csv(out_file, index=False)
            logger.info(f"Saved {len(df_transformed)} rows")

            # Load to database (optional, skip if DB not available)
            if os.getenv("POSTGRES_HOST"):
                try:
                    logger.info("Loading to database...")
                    loaded = load_df_to_postgres(df_transformed, csv_file.stem)
                    stats.rows_loaded += loaded
                except LoadError as e:
                    logger.warning(f"Database load skipped: {e}")
            else:
                logger.debug("POSTGRES_HOST not set, skipping database load")

            logger.info(f"✓ {csv_file.name} processed successfully")
            stats.files_processed += 1
            return True

        except (ExtractionError, TransformError, LoadError) as e:
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt} failed: {e}. Retrying...")
                continue
            else:
                error_msg = f"{csv_file.name}: {e}"
                logger.error(f"✗ {error_msg}")
                stats.errors.append(error_msg)
                stats.files_failed += 1
                return False
        except Exception as e:
            error_msg = f"{csv_file.name}: Unexpected error: {e}"
            logger.error(f"✗ {error_msg}")
            logger.debug(traceback.format_exc())
            stats.errors.append(error_msg)
            stats.files_failed += 1
            return False

    return False


def run():
    """Execute the ETL pipeline."""
    start_time = datetime.now()
    logger.info("\n" + "=" * 80)
    logger.info(f"ETL PIPELINE STARTED: {start_time.isoformat()}")
    logger.info("=" * 80 + "\n")

    stats = PipelineStats()

    # Validate directories
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_DIR.exists():
        logger.error(f"Raw data directory not found: {RAW_DIR}")
        return False

    # Find all CSV files
    csv_files = sorted(RAW_DIR.glob("*.csv"))
    if not csv_files:
        logger.warning(f"No CSV files found in {RAW_DIR}")
        return True

    logger.info(f"Found {len(csv_files)} CSV file(s) to process:")
    for f in csv_files:
        logger.info(f"  - {f.name}")

    # Process each file
    for csv_file in csv_files:
        process_file(csv_file, stats)

    # Log final statistics
    stats.log_stats()

    try:
        dashboard_result = generate_dashboard(PROCESSED_DIR)
        logger.info(f"Dashboard generated at: {dashboard_result['dashboard_path']}")
    except Exception as e:
        logger.warning(f"Dashboard generation skipped or failed: {e}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"ETL PIPELINE COMPLETED in {duration:.1f}s")
    logger.info("=" * 80 + "\n")

    # Return success if no critical failures
    return stats.files_failed == 0


if __name__ == "__main__":
    try:
        success = run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.error("Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Pipeline crashed: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)
