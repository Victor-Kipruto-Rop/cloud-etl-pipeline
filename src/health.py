"""Health checks and monitoring for ETL pipeline."""

import logging
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import create_engine, text

from src.config import get_config

logger = logging.getLogger(__name__)


class HealthChecker:
    """Performs health checks on pipeline components."""

    def __init__(self):
        self.checks = {}
        self.timestamp = datetime.now()

    def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and status."""
        config = get_config()
        check_result = {"status": "unknown", "message": "", "response_time_ms": 0}

        try:
            start = datetime.now()
            engine = create_engine(config.database.get_connection_string())

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            response_time = (datetime.now() - start).total_seconds() * 1000
            check_result["status"] = "healthy"
            check_result["response_time_ms"] = response_time
            logger.info(f"Database health check passed: {response_time:.2f}ms")
        except Exception as e:
            check_result["status"] = "unhealthy"
            check_result["message"] = str(e)
            logger.error(f"Database health check failed: {e}")

        self.checks["database"] = check_result
        return check_result

    def check_file_system(self) -> Dict[str, Any]:
        """Check required directories exist and are writable."""
        config = get_config()
        check_result = {"status": "healthy", "message": "", "directories": {}}

        try:
            for dir_name, dir_path in [
                ("raw_data", config.pipeline.raw_data_dir),
                ("processed_data", config.pipeline.processed_data_dir),
                ("logs", config.pipeline.log_dir),
            ]:
                dir_exists = dir_path.exists()
                check_result["directories"][dir_name] = {
                    "exists": dir_exists,
                    "path": str(dir_path),
                }

                if not dir_exists:
                    check_result["status"] = "warning"
                    check_result["message"] = "Some directories missing"

            logger.info("File system health check completed")
        except Exception as e:
            check_result["status"] = "unhealthy"
            check_result["message"] = str(e)
            logger.error(f"File system health check failed: {e}")

        self.checks["file_system"] = check_result
        return check_result

    def check_dependencies(self) -> Dict[str, Any]:
        """Check if required dependencies are installed."""
        check_result = {"status": "healthy", "dependencies": {}}

        required = ["pandas", "sqlalchemy", "psycopg2", "dotenv"]

        for dep in required:
            try:
                __import__(dep)
                check_result["dependencies"][dep] = "installed"
            except ImportError:
                check_result["dependencies"][dep] = "missing"
                check_result["status"] = "unhealthy"

        logger.info(f"Dependencies check: {check_result['status']}")
        self.checks["dependencies"] = check_result
        return check_result

    def run_all_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run all health checks."""
        logger.info("Starting health checks")
        self.timestamp = datetime.now()

        self.check_database()
        self.check_file_system()
        self.check_dependencies()

        overall_status = "healthy"
        if any(c.get("status") == "unhealthy" for c in self.checks.values()):
            overall_status = "unhealthy"
        elif any(c.get("status") == "warning" for c in self.checks.values()):
            overall_status = "warning"

        return {
            "overall_status": overall_status,
            "timestamp": self.timestamp.isoformat(),
            "checks": self.checks,
            "deploy": self._get_deploy_info(),
        }

    def _get_deploy_info(self) -> Dict[str, Any]:
        try:
            from src.deploy_info import get_deploy_info

            return get_deploy_info()
        except Exception:
            logger.debug("Failed to read deploy info for health output")
            return {"version": "unknown"}

    def get_status_report(self) -> str:
        """Get a formatted status report."""
        report = f"Health Check Report - {self.timestamp.isoformat()}\n"
        report += "=" * 60 + "\n"

        for check_name, result in self.checks.items():
            status = result.get("status", "unknown").upper()
            report += f"{check_name.upper()}: {status}\n"

            if result.get("message"):
                report += f"  Message: {result['message']}\n"

            if result.get("response_time_ms"):
                report += f"  Response Time: {result['response_time_ms']:.2f}ms\n"

        return report
