"""Logging configuration and validation for ETL pipeline."""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from src.config import get_config


class LogConfig:
    """Logging configuration manager."""

    LOG_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    @staticmethod
    def configure(log_dir: Optional[Path] = None, level: Optional[str] = None):
        """Configure logging for the entire application.

        Args:
            log_dir: Directory for log files
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        config = get_config()

        if log_dir is None:
            log_dir = config.pipeline.log_dir

        if level is None:
            level = config.pipeline.log_level

        log_dir.mkdir(parents=True, exist_ok=True)

        log_level = LogConfig.LOG_LEVELS.get(level.upper(), logging.INFO)

        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler with rotation
        log_file = log_dir / "pipeline.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Error file handler
        error_file = log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)

        root_logger.info(f"Logging configured: level={level}, dir={log_dir}")

        return root_logger

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance."""
        return logging.getLogger(name)


class LogValidator:
    """Validates logging configuration and functionality."""

    @staticmethod
    def validate():
        """Run all validation checks."""
        results = {
            "handlers_configured": LogValidator._check_handlers(),
            "log_level_valid": LogValidator._check_log_level(),
            "log_files_writable": LogValidator._check_log_files_writable(),
            "log_directory_exists": LogValidator._check_log_directory(),
        }

        return results

    @staticmethod
    def _check_handlers() -> bool:
        """Check if handlers are properly configured."""
        root_logger = logging.getLogger()

        handlers_found = {"console": False, "file": False}

        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                handlers_found["console"] = True
            elif isinstance(handler, logging.FileHandler):
                handlers_found["file"] = True

        return all(handlers_found.values())

    @staticmethod
    def _check_log_level() -> bool:
        """Check if log level is properly set."""
        root_logger = logging.getLogger()
        return root_logger.level > 0

    @staticmethod
    def _check_log_files_writable() -> bool:
        """Check if log files are writable."""
        config = get_config()
        log_dir = config.pipeline.log_dir

        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            test_file = log_dir / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception:
            return False

    @staticmethod
    def _check_log_directory() -> bool:
        """Check if log directory exists."""
        config = get_config()
        log_dir = config.pipeline.log_dir

        return log_dir.exists()


def test_logging():
    """Test logging configuration."""
    logger = logging.getLogger(__name__)

    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")
