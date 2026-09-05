"""Configuration management for ETL pipeline."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from src.secrets import SecretManager

logger = logging.getLogger(__name__)

_secret_manager = SecretManager()

# Load environment variables
load_dotenv()


def _read_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Read environment variable values while ignoring blank strings."""
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _read_int_env(name: str, default: int, minimum: int = 1, maximum: int = 65535) -> int:
    """Safely read integer env values and enforce a valid port/range."""
    raw_value = _read_env(name, str(default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    host: str = field(
        default_factory=lambda: _secret_manager.get_secret("POSTGRES_HOST", default="localhost") or "localhost"
    )
    port: int = field(default_factory=lambda: _read_int_env("POSTGRES_PORT", 5432))
    user: str = field(
        default_factory=lambda: _secret_manager.get_secret("POSTGRES_USER", default="postgres") or "postgres"
    )
    password: str = field(
        default_factory=lambda: _secret_manager.get_secret("POSTGRES_PASSWORD", default="postgres") or "postgres"
    )
    database: str = field(
        default_factory=lambda: _secret_manager.get_secret("POSTGRES_DB", default="etl_db") or "etl_db"
    )

    def get_connection_string(self) -> str:
        """Get SQLAlchemy connection string."""
        return (
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        )

    def validate(self) -> bool:
        """Validate configuration."""
        if not all([self.host, self.user, self.password, self.database]):
            logger.error("Missing required database configuration")
            return False
        if not 1 <= self.port <= 65535:
            logger.error("Database port is out of range")
            return False
        return True


@dataclass
class PipelineConfig:
    """Pipeline configuration settings."""

    raw_data_dir: Path = field(
        default_factory=lambda: Path(_read_env("RAW_DATA_DIR", "data/raw") or "data/raw")
    )
    processed_data_dir: Path = field(
        default_factory=lambda: Path(
            _read_env("PROCESSED_DATA_DIR", "data/processed") or "data/processed"
        )
    )
    log_dir: Path = field(default_factory=lambda: Path(_read_env("LOG_DIR", "logs") or "logs"))
    chunk_size: int = field(default_factory=lambda: _read_int_env("CHUNK_SIZE", 10000, minimum=1))
    max_retries: int = field(default_factory=lambda: _read_int_env("MAX_RETRIES", 3, minimum=1))
    log_level: str = field(default_factory=lambda: (_read_env("LOG_LEVEL", "INFO") or "INFO").upper())
    kaggle_download: bool = field(
        default_factory=lambda: (_read_env("KAGGLE_DOWNLOAD", "false") or "false").lower() == "true"
    )
    kaggle_dataset: Optional[str] = field(default_factory=lambda: _read_env("KAGGLE_DATASET"))
    kaggle_force: bool = field(
        default_factory=lambda: (_read_env("KAGGLE_FORCE_DOWNLOAD", "false") or "false").lower() == "true"
    )
    kaggle_file_pattern: str = field(
        default_factory=lambda: _read_env("KAGGLE_FILE_PATTERN", "*.csv") or "*.csv"
    )
    kaggle_quiet: bool = field(
        default_factory=lambda: (_read_env("KAGGLE_QUIET", "true") or "true").lower() == "true"
    )

    def validate(self) -> bool:
        """Validate and create required directories."""
        try:
            self.raw_data_dir.mkdir(parents=True, exist_ok=True)
            self.processed_data_dir.mkdir(parents=True, exist_ok=True)
            self.log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Pipeline directories validated: {self.raw_data_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to validate pipeline directories: {e}")
            return False


@dataclass
class Config:
    """Main configuration container."""

    database: DatabaseConfig
    pipeline: PipelineConfig

    def validate_all(self) -> bool:
        """Validate all configurations."""
        return self.database.validate() and self.pipeline.validate()


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global configuration."""
    global _config
    if _config is None:
        _config = Config(database=DatabaseConfig(), pipeline=PipelineConfig())
        if not _config.validate_all():
            logger.warning("Configuration validation failed")
    return _config


def reload_config():
    """Reload configuration (useful for testing)."""
    global _config
    load_dotenv()
    _config = None
    return get_config()
