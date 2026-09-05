"""REST API and scheduler for ETL pipeline."""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import schedule
from flask import Flask, jsonify, request
from flask_cors import CORS

from src.config import get_config
from src.health import HealthChecker
from src.orchestration import PipelineOrchestrator
from src.pipeline import run as run_pipeline
from src.deploy_info import get_deploy_info

logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
CORS(app)

pipeline_orchestrator = PipelineOrchestrator()

# Maintenance mode persisted file
_MAINTENANCE_PATH = Path("data/maintenance.json")


def _read_maintenance() -> dict:
    try:
        if _MAINTENANCE_PATH.exists():
            return json.loads(_MAINTENANCE_PATH.read_text())
    except Exception:
        logger.exception("Failed to read maintenance file")
    return {"enabled": False}


def _write_maintenance(payload: dict) -> None:
    try:
        _MAINTENANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _MAINTENANCE_PATH.write_text(json.dumps(payload))
    except Exception:
        logger.exception("Failed to write maintenance file")


def _require_admin_token():
    token = request.headers.get("X-Admin-Token")
    expected = os.environ.get("ADMIN_TOKEN")
    if not expected or token != expected:
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    return None


# Scheduler
_scheduler_running = False


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    checker = HealthChecker()
    results = checker.run_all_checks()

    status_code = 200 if results["overall_status"] == "healthy" else 503
    return jsonify(results), status_code


@app.route("/api/v1/info", methods=["GET"])
def info():
    """Return service deploy and build metadata."""
    info = get_deploy_info()
    return jsonify(info), 200


@app.route("/api/v1/maintenance", methods=["GET", "POST"])
def maintenance():
    """Get or set maintenance mode.

    POST body: {"enabled": true|false, "reason": "...", "by": "username"}
    """
    if request.method == "GET":
        return jsonify(_read_maintenance()), 200

    auth_error = _require_admin_token()
    if auth_error:
        return auth_error

    # POST - update
    try:
        payload = request.get_json() or {}
        enabled = bool(payload.get("enabled", False))
        reason = payload.get("reason")
        by = payload.get("by")
        record = {
            "enabled": enabled,
            "reason": reason,
            "by": by,
            "timestamp": datetime.now().isoformat(),
        }
        _write_maintenance(record)
        return jsonify({"status": "ok", "maintenance": record}), 200
    except Exception as e:
        logger.error(f"Failed to set maintenance: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/pipeline/run", methods=["POST"])
def trigger_pipeline():
    """Trigger pipeline execution."""
    # Prevent changes during maintenance mode unless explicitly overridden
    m = _read_maintenance()
    if m.get("enabled"):
        data = request.get_json() or {}
        if data.get("override_maintenance"):
            auth_error = _require_admin_token()
            if auth_error:
                return auth_error
        else:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Service in maintenance mode",
                        "maintenance": m,
                    }
                ),
                503,
            )
    try:
        logger.info("Pipeline run triggered via API")

        data = request.get_json() or {}
        dry_run = data.get("dry_run", False)
        async_run = data.get("async_run", False)

        if dry_run:
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Dry run mode - no changes made",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                200,
            )

        if async_run:
            job_id = pipeline_orchestrator.start_job("pipeline-run", run_pipeline)
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Pipeline execution started asynchronously",
                        "job_id": job_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                200,
            )

        result = run_pipeline()
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Pipeline executed successfully",
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@app.route("/api/v1/pipeline/jobs", methods=["GET"])
def list_jobs():
    """List orchestrated pipeline jobs."""
    return jsonify({"jobs": pipeline_orchestrator.list_jobs()}), 200


@app.route("/api/v1/pipeline/jobs/<job_id>", methods=["GET"])
def get_job(job_id: str):
    """Get the status of a specific orchestrated job."""
    try:
        return jsonify(pipeline_orchestrator.get_job_status(job_id)), 200
    except KeyError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 404


@app.route("/api/v1/pipeline/status", methods=["GET"])
def pipeline_status():
    """Get pipeline status."""
    config = get_config()

    status = {
        "status": "running",
        "log_file": str(config.pipeline.log_dir / "pipeline.log"),
        "timestamp": datetime.now().isoformat(),
        "deploy": get_deploy_info(),
    }

    return jsonify(status), 200


@app.route("/api/v1/pipeline/config", methods=["GET"])
def pipeline_config():
    """Get pipeline configuration."""
    config = get_config()

    return (
        jsonify(
            {
                "database": {
                    "host": config.database.host,
                    "port": config.database.port,
                    "database": config.database.database,
                },
                "pipeline": {
                    "raw_data_dir": str(config.pipeline.raw_data_dir),
                    "processed_data_dir": str(config.pipeline.processed_data_dir),
                    "log_dir": str(config.pipeline.log_dir),
                    "chunk_size": config.pipeline.chunk_size,
                    "max_retries": config.pipeline.max_retries,
                },
            }
        ),
        200,
    )


@app.route("/api/v1/scheduler/schedule", methods=["POST"])
def schedule_pipeline():
    """Schedule pipeline execution."""
    try:
        data = request.get_json()
        interval = data.get("interval", "daily")  # hourly, daily, weekly

        logger.info(f"Scheduling pipeline: {interval}")

        schedule_pipeline_job(interval)

        return (
            jsonify(
                {
                    "status": "scheduled",
                    "interval": interval,
                    "message": f"Pipeline scheduled to run {interval}",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Scheduling failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/scheduler/start", methods=["POST"])
def start_scheduler():
    """Start the scheduler."""
    global _scheduler_running

    if _scheduler_running:
        return (
            jsonify(
                {"status": "already_running", "message": "Scheduler is already running"}
            ),
            200,
        )

    _scheduler_running = True

    # Start scheduler in background
    import threading

    thread = threading.Thread(target=_run_scheduler)
    thread.daemon = True
    thread.start()

    logger.info("Scheduler started")

    return (
        jsonify(
            {
                "status": "started",
                "message": "Scheduler started successfully",
                "timestamp": datetime.now().isoformat(),
            }
        ),
        200,
    )


@app.route("/api/v1/scheduler/stop", methods=["POST"])
def stop_scheduler():
    """Stop the scheduler."""
    global _scheduler_running
    _scheduler_running = False

    logger.info("Scheduler stopped")

    return (
        jsonify({"status": "stopped", "message": "Scheduler stopped successfully"}),
        200,
    )


def schedule_pipeline_job(interval: str = "daily"):
    """Schedule pipeline job."""
    if interval == "hourly":
        schedule.every().hour.do(run_pipeline)
    elif interval == "daily":
        schedule.every().day.at("02:00").do(run_pipeline)
    elif interval == "weekly":
        schedule.every().monday.at("02:00").do(run_pipeline)

    logger.info(f"Pipeline job scheduled: {interval}")


def _run_scheduler():
    """Run the scheduler loop."""
    while _scheduler_running:
        schedule.run_pending()
        asyncio.sleep(60)


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


def create_app():
    """Application factory."""
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=5000, debug=False)
