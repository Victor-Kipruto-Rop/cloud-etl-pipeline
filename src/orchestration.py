"""Production-grade orchestration for ETL jobs."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional


class PipelineOrchestrator:
    """Track ETL job lifecycle with thread-safe status reporting."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pipeline-job")
        self._job_sequence = 0

    def _next_job_id(self) -> str:
        with self._lock:
            self._job_sequence += 1
            return f"job-{self._job_sequence:06d}"

    def start_job(
        self,
        name: str,
        func: Callable[..., Any],
        *args,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> str:
        """Queue a job and return a unique job identifier."""
        job_id = self._next_job_id()
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "name": name,
                "status": "queued",
                "started_at": now,
                "updated_at": now,
                "timeout_seconds": timeout,
                "result": None,
                "error": None,
                "finished_at": None,
                "future": None,
            }

        # cooperative cancellation event passed to the job
        cancel_event = threading.Event()

        def _run_job() -> Any:
            with self._lock:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

            try:
                # inject cancel_event into kwargs so long-running jobs can honor cancellation
                kwargs_with_event = dict(kwargs)
                kwargs_with_event.setdefault("cancel_event", cancel_event)
                result = func(*args, **kwargs_with_event)
                with self._lock:
                    self._jobs[job_id]["status"] = "completed"
                    self._jobs[job_id]["result"] = result
                    self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
                return result
            except Exception as exc:  # pragma: no cover - exercised by actual runtime usage
                with self._lock:
                    self._jobs[job_id]["status"] = "failed"
                    self._jobs[job_id]["error"] = str(exc)
                    self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
                raise

        future = self._executor.submit(_run_job)
        with self._lock:
            self._jobs[job_id]["future"] = future
            # store the cancel event for external cancellation
            self._jobs[job_id]["cancel_event"] = cancel_event

        return job_id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Return the current status snapshot for a job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown job id: {job_id}")

            status = dict(job)
            future = job.get("future")
            if future is not None and future.done() and job["status"] not in {"completed", "failed"}:
                try:
                    future.result()
                except Exception:
                    pass

            if job.get("timeout_seconds") and job.get("status") == "running":
                started = datetime.fromisoformat(job["started_at"])
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                if elapsed > float(job["timeout_seconds"]):
                    status["status"] = "timed_out"
                    status["updated_at"] = datetime.now(timezone.utc).isoformat()
                    status["finished_at"] = datetime.now(timezone.utc).isoformat()

            return status

    def list_jobs(self) -> Dict[str, Dict[str, Any]]:
        """List all known jobs."""
        with self._lock:
            return {job_id: dict(job) for job_id, job in self._jobs.items()}

    def get_job_result(self, job_id: str) -> Any:
        """Return the completed job result."""
        status = self.get_job_status(job_id)
        if status["status"] not in {"completed", "failed"}:
            return None
        if status["status"] == "failed":
            raise RuntimeError(status.get("error") or "Job failed")
        return status.get("result")

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the executor."""
        self._executor.shutdown(wait=wait)

    def cancel_job(self, job_id: str) -> bool:
        """Attempt to cancel a queued/running job.

        Returns True if the job was cancelled, False otherwise.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(f"Unknown job id: {job_id}")

            future = job.get("future")
            cancel_event = job.get("cancel_event")
            if future is None:
                # Job is queued but not yet submitted to the executor.
                # Set the cancel event so it is honored as soon as the job starts.
                if cancel_event is not None:
                    cancel_event.set()
                    job["status"] = "cancelled"
                    job["updated_at"] = datetime.now(timezone.utc).isoformat()
                    job["finished_at"] = job["updated_at"]
                return False

            # First, if the job is running, signal cooperative cancel
            if cancel_event is not None and not future.done():
                cancel_event.set()

            cancelled = future.cancel()
            if cancelled:
                job["status"] = "cancelled"
                job["updated_at"] = datetime.now(timezone.utc).isoformat()
                job["finished_at"] = job["updated_at"]
            return cancelled


def create_orchestrator(max_workers: int = 4) -> PipelineOrchestrator:
    """Factory helper for production orchestration."""
    return PipelineOrchestrator(max_workers=max_workers)
