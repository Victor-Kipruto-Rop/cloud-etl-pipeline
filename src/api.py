"""REST API and scheduler for ETL pipeline."""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import schedule
from flask import Flask, jsonify, request
from flask_cors import CORS

from src.config import get_config
from src.health import HealthChecker
from src.pipeline import run as run_pipeline

logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
CORS(app)

# Scheduler
_scheduler_running = False


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    checker = HealthChecker()
    results = checker.run_all_checks()

    status_code = 200 if results["overall_status"] == "healthy" else 503
    return jsonify(results), status_code


@app.route("/api/v1/pipeline/run", methods=["POST"])
def trigger_pipeline():
    """Trigger pipeline execution."""
    try:
        logger.info("Pipeline run triggered via API")

        # Optional: get parameters from request
        data = request.get_json() or {}
        dry_run = data.get("dry_run", False)

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

        # Run pipeline
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


@app.route("/api/v1/pipeline/status", methods=["GET"])
def pipeline_status():
    """Get pipeline status."""
    config = get_config()

    status = {
        "status": "running",
        "log_file": str(config.pipeline.log_dir / "pipeline.log"),
        "timestamp": datetime.now().isoformat(),
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
