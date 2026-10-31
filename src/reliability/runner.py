"""End-to-end reliable dataset execution across medallion layers and sinks."""
from __future__ import annotations

import logging
from pathlib import Path
from time import monotonic
from typing import Callable, Optional

import pandas as pd
from sqlalchemy.engine import Engine

from src.layers import write_layer
from src.load.idempotent import upsert_dataframe
from src.reliability.metrics import (
    dataset_duration,
    dataset_rows,
    dataset_runs,
    quarantine_records,
)
from src.reliability.store import MetadataStore
from src.transform.transform_data import TransformError
from src.validation import ValidationError

logger = logging.getLogger(__name__)


def execute_dataset(
    source_dataframe: pd.DataFrame,
    silver_dataframe: Optional[pd.DataFrame] = None,
    *,
    dataset: str,
    source_uri: str,
    source_checksum: str,
    metadata_store: MetadataStore,
    layer_root: str | Path,
    validate: Optional[Callable[[pd.DataFrame], None]] = None,
    transform: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
    gold_dataframe: Optional[pd.DataFrame] = None,
    database_engine: Optional[Engine] = None,
    target_table: Optional[str] = None,
    target_schema: Optional[str] = None,
    conflict_columns: tuple[str, ...] = (),
    file_format: str = "parquet",
) -> dict:
    """Run one dataset and commit its checkpoint only after every required sink.

    A matching successful checksum is skipped. Failures are persisted in the run
    ledger and quarantine; callers can restore/replay the source explicitly.
    """
    if not source_checksum:
        raise ValueError("source_checksum is required for incremental execution")
    if not isinstance(source_dataframe, pd.DataFrame):
        raise TypeError("source_dataframe must be a pandas DataFrame")
    if silver_dataframe is None and transform is None:
        raise ValueError("Provide silver_dataframe or a transform callable")
    if silver_dataframe is not None and not isinstance(
        silver_dataframe, pd.DataFrame
    ):
        raise TypeError("silver_dataframe must be a pandas DataFrame")
    started = monotonic()
    checkpoint = metadata_store.get_checkpoint(dataset, source_uri)
    if checkpoint and checkpoint["source_checksum"] == source_checksum:
        dataset_runs.labels(status="skipped").inc()
        dataset_duration.observe(monotonic() - started)
        return {
            "status": "skipped",
            "run_id": checkpoint["committed_run_id"],
            "reason": "source checksum already committed",
        }

    run_id = metadata_store.start_run(
        dataset, source_uri=source_uri, source_checksum=source_checksum
    )
    try:
        if validate:
            validate(source_dataframe)
        if transform is not None:
            silver_dataframe = transform(source_dataframe)
        if not isinstance(silver_dataframe, pd.DataFrame):
            raise TypeError("transform must return a pandas DataFrame")

        bronze = write_layer(
            source_dataframe, root=layer_root, layer="bronze", dataset=dataset,
            run_id=run_id, source_uri=source_uri, source_checksum=source_checksum,
            file_format=file_format,
        )
        metadata_store.record_lineage(
            run_id, dataset, "bronze_published",
            parent_uri=source_uri, child_uri=bronze["artifact_path"],
            details={"rows": len(source_dataframe), "sha256": bronze["sha256"]},
        )

        silver = write_layer(
            silver_dataframe, root=layer_root, layer="silver", dataset=dataset,
            run_id=run_id, source_uri=bronze["artifact_path"],
            source_checksum=bronze["sha256"], file_format=file_format,
        )
        metadata_store.record_lineage(
            run_id, dataset, "silver_published",
            parent_uri=bronze["artifact_path"], child_uri=silver["artifact_path"],
            details={"rows": len(silver_dataframe), "sha256": silver["sha256"]},
        )

        if gold_dataframe is not None:
            gold = write_layer(
                gold_dataframe, root=layer_root, layer="gold", dataset=dataset,
                run_id=run_id, source_uri=silver["artifact_path"],
                source_checksum=silver["sha256"], file_format=file_format,
            )
            metadata_store.record_lineage(
                run_id, dataset, "gold_published",
                parent_uri=silver["artifact_path"], child_uri=gold["artifact_path"],
                details={"rows": len(gold_dataframe), "sha256": gold["sha256"]},
            )

        loaded_rows = len(silver_dataframe)
        if database_engine is not None:
            if not target_table or not conflict_columns:
                raise ValueError(
                    "target_table and conflict_columns are required when a "
                    "database sink is configured"
                )
            loaded_rows = upsert_dataframe(
                database_engine, silver_dataframe, table_name=target_table,
                conflict_columns=conflict_columns,
                schema=target_schema,
            )

        metadata_store.finish_run(
            run_id, rows_read=len(source_dataframe), rows_written=loaded_rows,
            source_uri=source_uri, source_checksum=source_checksum,
        )
        dataset_runs.labels(status="succeeded").inc()
        dataset_rows.labels(layer="bronze").inc(len(source_dataframe))
        dataset_rows.labels(layer="silver").inc(len(silver_dataframe))
        if gold_dataframe is not None:
            dataset_rows.labels(layer="gold").inc(len(gold_dataframe))
        return {
            "status": "succeeded",
            "run_id": run_id,
            "rows_read": len(source_dataframe),
            "rows_written": loaded_rows,
            "bronze": bronze["artifact_path"],
            "silver": silver["artifact_path"],
            "gold": gold["artifact_path"] if gold_dataframe is not None else None,
        }
    except (ValidationError, TransformError) as exc:
        dataset_runs.labels(status="failed").inc()
        quarantine_records.inc()
        try:
            metadata_store.quarantine_record(
                run_id,
                dataset,
                source_uri,
                "DATA_QUALITY_FAILURE",
                str(exc),
                {
                    "source_checksum": source_checksum,
                    "exception_type": type(exc).__name__,
                },
            )
        except Exception:
            logger.exception("Could not persist data-quality quarantine record")
        try:
            metadata_store.fail_run(run_id, str(exc))
        except Exception:
            logger.exception("Could not mark data-quality run as failed")
        raise
    except Exception as exc:
        dataset_runs.labels(status="failed").inc()
        try:
            metadata_store.fail_run(run_id, str(exc))
        except Exception:
            logger.exception("Could not mark failed dataset run")
        raise
    finally:
        dataset_duration.observe(monotonic() - started)
