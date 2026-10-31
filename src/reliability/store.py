"""Portable durable metadata store for checkpoints, runs, lineage and quarantine.

The store uses SQLAlchemy Core so the same implementation can run against SQLite
for local development/tests and PostgreSQL in shared environments.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
    update,
)
from sqlalchemy.engine import Engine


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MetadataStore:
    """Persist ETL run state and only advance checkpoints after successful commits."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.metadata = MetaData()
        self.runs = Table(
            "etl_runs",
            self.metadata,
            Column("run_id", String(36), primary_key=True),
            Column("dataset", String(255), nullable=False, index=True),
            Column("status", String(32), nullable=False),
            Column("started_at", String(40), nullable=False),
            Column("finished_at", String(40)),
            Column("source_uri", Text),
            Column("source_checksum", String(64)),
            Column("rows_read", Integer, nullable=False, default=0),
            Column("rows_written", Integer, nullable=False, default=0),
            Column("error_message", Text),
            Column("metadata_json", Text, nullable=False, default="{}"),
        )
        self.checkpoints = Table(
            "etl_checkpoints",
            self.metadata,
            Column("dataset", String(255), primary_key=True),
            Column("source_uri", Text, primary_key=True),
            Column("source_checksum", String(64), nullable=False),
            Column("source_version", String(255)),
            Column("committed_run_id", String(36), nullable=False),
            Column("committed_at", String(40), nullable=False),
        )
        self.lineage = Table(
            "etl_lineage",
            self.metadata,
            Column("event_id", String(36), primary_key=True),
            Column("run_id", String(36), nullable=False, index=True),
            Column("dataset", String(255), nullable=False),
            Column("event_type", String(80), nullable=False),
            Column("parent_uri", Text),
            Column("child_uri", Text),
            Column("details_json", Text, nullable=False, default="{}"),
            Column("created_at", String(40), nullable=False),
        )
        self.quarantine = Table(
            "etl_quarantine",
            self.metadata,
            Column("record_id", String(36), primary_key=True),
            Column("run_id", String(36), nullable=False, index=True),
            Column("dataset", String(255), nullable=False),
            Column("source_uri", Text, nullable=False),
            Column("reason_code", String(100), nullable=False),
            Column("reason_message", Text, nullable=False),
            Column("payload_json", Text, nullable=False),
            Column("status", String(32), nullable=False, default="pending"),
            Column("created_at", String(40), nullable=False),
            Column("replayed_at", String(40)),
        )
        self.metadata.create_all(self.engine)

    @staticmethod
    def _json(value: Optional[Mapping[str, Any]]) -> str:
        return json.dumps(dict(value or {}), default=str, sort_keys=True)

    def start_run(
        self,
        dataset: str,
        source_uri: Optional[str] = None,
        source_checksum: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> str:
        if not dataset or not dataset.strip():
            raise ValueError("dataset is required")
        run_id = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(
                self.runs.insert().values(
                    run_id=run_id,
                    dataset=dataset,
                    status="running",
                    started_at=utc_now(),
                    source_uri=source_uri,
                    source_checksum=source_checksum,
                    rows_read=0,
                    rows_written=0,
                    metadata_json=self._json(metadata),
                )
            )
        return run_id

    def finish_run(
        self,
        run_id: str,
        *,
        rows_read: int,
        rows_written: int,
        source_uri: Optional[str] = None,
        source_checksum: Optional[str] = None,
        source_version: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Complete a run and atomically advance its dataset/source checkpoint."""
        if rows_read < 0 or rows_written < 0:
            raise ValueError("row counts cannot be negative")
        now = utc_now()
        with self.engine.begin() as conn:
            run = (
                conn.execute(
                    select(self.runs).where(self.runs.c.run_id == run_id)
                )
                .mappings()
                .first()
            )
            if run is None:
                raise KeyError(f"Unknown run_id: {run_id}")
            if run["status"] != "running":
                raise ValueError(f"Cannot complete run in state {run['status']!r}")
            final_source = source_uri or run["source_uri"]
            final_checksum = source_checksum or run["source_checksum"]
            run_metadata = json.loads(run["metadata_json"] or "{}")
            run_metadata.update(dict(metadata or {}))
            conn.execute(
                update(self.runs)
                .where(self.runs.c.run_id == run_id)
                .values(
                    status="succeeded",
                    finished_at=now,
                    rows_read=rows_read,
                    rows_written=rows_written,
                    source_uri=final_source,
                    source_checksum=final_checksum,
                    metadata_json=self._json(run_metadata),
                )
            )
            if final_source and final_checksum:
                existing = (
                    conn.execute(
                        select(self.checkpoints).where(
                            self.checkpoints.c.dataset == run["dataset"],
                            self.checkpoints.c.source_uri == final_source,
                        )
                    )
                    .mappings()
                    .first()
                )
                values = {
                    "source_checksum": final_checksum,
                    "source_version": source_version,
                    "committed_run_id": run_id,
                    "committed_at": now,
                }
                if existing:
                    conn.execute(
                        update(self.checkpoints)
                        .where(
                            self.checkpoints.c.dataset == run["dataset"],
                            self.checkpoints.c.source_uri == final_source,
                        )
                        .values(**values)
                    )
                else:
                    conn.execute(
                        self.checkpoints.insert().values(
                            dataset=run["dataset"],
                            source_uri=final_source,
                            **values,
                        )
                    )

    def fail_run(self, run_id: str, error: str) -> None:
        with self.engine.begin() as conn:
            result = conn.execute(
                update(self.runs)
                .where(
                    self.runs.c.run_id == run_id,
                    self.runs.c.status == "running",
                )
                .values(
                    status="failed",
                    finished_at=utc_now(),
                    error_message=str(error),
                )
            )
            if result.rowcount != 1:
                raise KeyError(f"Unknown or non-running run_id: {run_id}")

    def get_checkpoint(self, dataset: str, source_uri: str) -> Optional[dict[str, Any]]:
        with self.engine.connect() as conn:
            row = (
                conn.execute(
                    select(self.checkpoints).where(
                        self.checkpoints.c.dataset == dataset,
                        self.checkpoints.c.source_uri == source_uri,
                    )
                )
                .mappings()
                .first()
            )
            return dict(row) if row else None

    def record_lineage(
        self,
        run_id: str,
        dataset: str,
        event_type: str,
        *,
        parent_uri: Optional[str] = None,
        child_uri: Optional[str] = None,
        details: Optional[Mapping[str, Any]] = None,
    ) -> str:
        event_id = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(
                self.lineage.insert().values(
                    event_id=event_id,
                    run_id=run_id,
                    dataset=dataset,
                    event_type=event_type,
                    parent_uri=parent_uri,
                    child_uri=child_uri,
                    details_json=self._json(details),
                    created_at=utc_now(),
                )
            )
        return event_id

    def quarantine_record(
        self,
        run_id: str,
        dataset: str,
        source_uri: str,
        reason_code: str,
        reason_message: str,
        payload: Any,
    ) -> str:
        if not reason_code:
            raise ValueError("reason_code is required")
        record_id = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(
                self.quarantine.insert().values(
                    record_id=record_id,
                    run_id=run_id,
                    dataset=dataset,
                    source_uri=source_uri,
                    reason_code=reason_code,
                    reason_message=reason_message,
                    payload_json=json.dumps(payload, default=str),
                    status="pending",
                    created_at=utc_now(),
                )
            )
        return record_id

    def list_quarantine(
        self, *, dataset: Optional[str] = None, status: str = "pending"
    ) -> list[dict[str, Any]]:
        query = select(self.quarantine).where(self.quarantine.c.status == status)
        if dataset:
            query = query.where(self.quarantine.c.dataset == dataset)
        with self.engine.connect() as conn:
            rows = conn.execute(
                query.order_by(self.quarantine.c.created_at)
            ).mappings()
            return [dict(row) for row in rows]

    def mark_replayed(self, record_id: str, replay_run_id: str) -> None:
        """Mark quarantine resolved only after a successful run for the same dataset."""
        with self.engine.begin() as conn:
            record = (
                conn.execute(
                    select(self.quarantine).where(
                        self.quarantine.c.record_id == record_id,
                        self.quarantine.c.status == "pending",
                    )
                )
                .mappings()
                .first()
            )
            if record is None:
                raise KeyError(f"Unknown or already replayed record: {record_id}")
            replay_run = (
                conn.execute(
                    select(self.runs).where(self.runs.c.run_id == replay_run_id)
                )
                .mappings()
                .first()
            )
            if (
                replay_run is None
                or replay_run["status"] != "succeeded"
                or replay_run["dataset"] != record["dataset"]
            ):
                raise ValueError(
                    "Replay record can be resolved only by a successful run "
                    "for the same dataset"
                )
            conn.execute(
                update(self.quarantine)
                .where(
                    self.quarantine.c.record_id == record_id,
                    self.quarantine.c.status == "pending",
                )
                .values(status="replayed", replayed_at=utc_now())
            )

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        with self.engine.connect() as conn:
            row = (
                conn.execute(
                    select(self.runs).where(self.runs.c.run_id == run_id)
                )
                .mappings()
                .first()
            )
            if not row:
                return None
            result = dict(row)
            result["metadata"] = json.loads(result.pop("metadata_json"))
            return result


def create_metadata_store(database_url: str) -> MetadataStore:
    """Create a metadata store from a SQLAlchemy database URL."""
    if not database_url:
        raise ValueError("database_url is required")
    return MetadataStore(create_engine(database_url, pool_pre_ping=True))
