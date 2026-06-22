import logging
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from sqlalchemy import create_engine

from src.dashboard import generate_dashboard
from src.extract.extract_data import ExtractionError, extract_csv
from src.load.copy_loader import copy_from_df
from src.load.load_to_db import LoadError, load_df_to_postgres
from src.load.staging_loader import upsert_from_staging
from src.metrics.metrics import (
    files_failed,
    files_processed,
)
from src.metrics.metrics import rows_extracted as metric_rows_extracted
from src.metrics.metrics import rows_loaded as metric_rows_loaded
from src.metrics.metrics import (
    start_metrics_server,
)
from src.transform.transform_data import TransformError, transform
from src.validation import ValidationError, parse_required_columns, validate_df

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
    """Track pipeline execution statistics with thread-safety."""

    def __init__(self):
        self.files_processed = 0
        self.files_failed = 0
        self.rows_extracted = 0
        self.rows_transformed = 0
        self.rows_loaded = 0
        self.errors = []
        self._lock = Lock()

    def incr(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, getattr(self, k) + v)

    def add_error(self, msg: str):
        with self._lock:
            self.errors.append(msg)

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
            stats.incr(rows_extracted=len(df))

            # Validate
            required = parse_required_columns(os.getenv("REQUIRED_COLUMNS"))
            try:
                validate_df(df, required_columns=required)
            except ValidationError as e:
                raise TransformError(f"Validation failed: {e}")

            # Transform
            logger.info("Transforming...")
            df_transformed = transform(
                df, normalize_cols=True, handle_missing="drop_all"
            )
            stats.incr(rows_transformed=len(df_transformed))

            # Save processed file
            out_file = PROCESSED_DIR / csv_file.name
            logger.info(f"Saving to {out_file}...")
            df_transformed.to_csv(out_file, index=False)
            logger.info(f"Saved {len(df_transformed)} rows")

            # Load to database (optional, prefer COPY via engine if available)
            if os.getenv("POSTGRES_HOST") or engine is not None:
                try:
                    logger.info("Loading to database...")
                    table_name = os.getenv("TARGET_TABLE", csv_file.stem)
                    if engine is not None:
                        cols = list(df_transformed.columns)
                        loaded = copy_from_df(engine, df_transformed, table_name, cols)
                        # metrics
                        try:
                            metric_rows_extracted.inc(len(df))
                            metric_rows_loaded.inc(loaded)
                        except Exception:
                            pass
                    else:
                        loaded = load_df_to_postgres(df_transformed, csv_file.stem)
                    stats.incr(rows_loaded=loaded)
                except LoadError as e:
                    logger.warning(f"Database load skipped: {e}")
            else:
                logger.debug(
                    "POSTGRES_HOST not set and no DATABASE_URL, skipping database load"
                )

            logger.info(f"✓ {csv_file.name} processed successfully")
            stats.incr(files_processed=1)
            return True

        except (ExtractionError, TransformError, LoadError) as e:
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt} failed: {e}. Retrying...")
                continue
            else:
                error_msg = f"{csv_file.name}: {e}"
                logger.error(f"✗ {error_msg}")
                stats.add_error(error_msg)
                stats.incr(files_failed=1)
                # move offending file to quarantine
                quarantine = RAW_DIR / "quarantine"
                quarantine.mkdir(parents=True, exist_ok=True)
                target = (
                    quarantine
                    / f"{csv_file.stem}_{int(datetime.now().timestamp())}{csv_file.suffix}"
                )
                try:
                    csv_file.replace(target)
                    logger.info(f"Moved failed file to quarantine: {target}")
                except Exception:
                    logger.warning(f"Failed to move {csv_file} to quarantine")
                return False
        except Exception as e:
            error_msg = f"{csv_file.name}: Unexpected error: {e}"
            logger.error(f"✗ {error_msg}")
            logger.debug(traceback.format_exc())
            stats.add_error(error_msg)
            stats.incr(files_failed=1)
            try:
                quarantine = RAW_DIR / "quarantine"
                quarantine.mkdir(parents=True, exist_ok=True)
                target = (
                    quarantine
                    / f"{csv_file.stem}_{int(datetime.now().timestamp())}{csv_file.suffix}"
                )
                csv_file.replace(target)
                logger.info(f"Moved unexpected-failure file to quarantine: {target}")
            except Exception:
                logger.warning(f"Failed to move {csv_file} to quarantine")
            return False

    return False


def run():
    """Execute the ETL pipeline."""
    start_time = datetime.now()
    logger.info("\n" + "=" * 80)
    logger.info(f"ETL PIPELINE STARTED: {start_time.isoformat()}")
    logger.info("=" * 80 + "\n")

    stats = PipelineStats()

    # Start metrics server if requested
    metrics_port = os.getenv("METRICS_PORT")
    if metrics_port:
        try:
            start_metrics_server(int(metrics_port))
        except Exception:
            logger.warning("Could not start metrics server")

    # Create DB engine if DATABASE_URL is provided (used by COPY loader)
    database_url = os.getenv("DATABASE_URL")
    engine = None
    if database_url:
        try:
            pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
            max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
            engine = create_engine(
                database_url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,
            )
            logger.info("Database engine created for COPY loader")
        except Exception as e:
            logger.warning(f"Failed to create DB engine: {e}")

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

    # Batch processing
    batch_size = int(os.getenv("BATCH_SIZE", "10"))
    parallel_workers = int(os.getenv("PARALLEL_WORKERS", "1"))

    for i in range(0, len(csv_files), batch_size):
        batch = csv_files[i : i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} file(s)")

        if parallel_workers > 1:
            with ThreadPoolExecutor(max_workers=parallel_workers) as exc:
                futures = {exc.submit(process_file, f, stats): f for f in batch}
                for fut in as_completed(futures):
                    f = futures[fut]
                    try:
                        fut.result()
                    except Exception as e:
                        logger.error(f"Error processing {f}: {e}")
        else:
            for csv_file in batch:
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
