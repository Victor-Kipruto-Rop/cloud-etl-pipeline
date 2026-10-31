"""Prometheus metrics for the incremental dataset execution path."""
from prometheus_client import Counter, Histogram

dataset_runs = Counter(
    "etl_dataset_runs_total",
    "Dataset execution outcomes",
    ["status"],
)
dataset_rows = Counter(
    "etl_dataset_rows_total",
    "Rows materialized by medallion layer",
    ["layer"],
)
quarantine_records = Counter(
    "etl_quarantine_records_total",
    "Records or dataset envelopes placed in quarantine",
)
dataset_duration = Histogram(
    "etl_dataset_duration_seconds",
    "Time spent executing a dataset through configured sinks",
)
