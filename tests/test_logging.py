"""Tests for logging configuration and validation."""

import unittest
import logging
import tempfile
from pathlib import Path

from src.logging_config import LogConfig, LogValidator, test_logging


class TestLoggingConfiguration(unittest.TestCase):
    """Test logging configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.logger = logging.getLogger(__name__)

    def tearDown(self):
        """Clean up."""
        import shutil

        shutil.rmtree(self.test_dir)

    def test_log_config_configure(self):
        """Test LogConfig.configure initializes logging."""
        LogConfig.configure(self.test_dir, "INFO")

        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.INFO)

    def test_log_config_levels(self):
        """Test logging level constants."""
        self.assertEqual(LogConfig.LOG_LEVELS["DEBUG"], logging.DEBUG)
        self.assertEqual(LogConfig.LOG_LEVELS["INFO"], logging.INFO)
        self.assertEqual(LogConfig.LOG_LEVELS["ERROR"], logging.ERROR)

    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = LogConfig.get_logger("test_module")
        self.assertIsInstance(logger, logging.Logger)


class TestLoggingValidator(unittest.TestCase):
    """Test logging validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        LogConfig.configure(self.test_dir, "INFO")

    def tearDown(self):
        """Clean up."""
        import shutil

        shutil.rmtree(self.test_dir)

    def test_validate_all_checks(self):
        """Test validate runs all checks."""
        results = LogValidator.validate()

        self.assertIn("handlers_configured", results)
        self.assertIn("log_level_valid", results)
        self.assertIn("log_files_writable", results)
        self.assertIn("log_directory_exists", results)

    def test_handlers_configured(self):
        """Test handler configuration validation."""
        self.assertTrue(LogValidator._check_handlers())

    def test_log_level_valid(self):
        """Test log level validation."""
        self.assertTrue(LogValidator._check_log_level())

    def test_log_directory_exists(self):
        """Test log directory exists."""
        self.assertTrue(LogValidator._check_log_directory())

    def test_log_files_writable(self):
        """Test log files are writable."""
        self.assertTrue(LogValidator._check_log_files_writable())

    def test_logging_functions(self):
        """Test that logging functions work."""
        # This should not raise any exceptions
        try:
            test_logging()
        except Exception as e:
            self.fail(f"test_logging() raised {e}")


class TestLogFileCreation(unittest.TestCase):
    """Test log file creation and rotation."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        LogConfig.configure(self.test_dir, "INFO")

    def tearDown(self):
        """Clean up."""
        import shutil

        shutil.rmtree(self.test_dir)

    def test_log_files_created(self):
        """Test that log files are created."""
        logger = logging.getLogger("test")
        logger.info("Test log message")

        log_file = self.test_dir / "pipeline.log"
        self.assertTrue(log_file.exists(), f"Log file not created at {log_file}")

    def test_error_log_file_created(self):
        """Test that error log file is created."""
        logger = logging.getLogger("test")
        logger.error("Test error message")

        error_file = self.test_dir / "errors.log"
        self.assertTrue(error_file.exists(), f"Error log not created at {error_file}")


if __name__ == "__main__":
    unittest.main()
