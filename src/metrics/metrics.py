"""Prometheus metrics helpers for the ETL pipeline."""

import logging
from threading import Thread

from prometheus_client import Counter, Gauge, start_http_server

logger = logging.getLogger(__name__)

files_processed = Counter("etl_files_processed_total", "Total files processed")
files_failed = Counter("etl_files_failed_total", "Total files failed")
rows_extracted = Counter("etl_rows_extracted_total", "Total rows extracted")
rows_loaded = Counter("etl_rows_loaded_total", "Total rows loaded")
current_in_progress = Gauge(
    "etl_current_in_progress", "Files currently being processed"
)


def start_metrics_server(port: int = 8000):
    try:
        t = Thread(target=start_http_server, args=(port,), daemon=True)
        t.start()
        logger.info(f"Prometheus metrics server started on :{port}")
    except Exception as e:
        logger.warning(f"Failed to start metrics server: {e}")
