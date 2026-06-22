"""Configuration management for ETL pipeline."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    host: str = field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("POSTGRES_PORT", 5432)))
    user: str = field(default_factory=lambda: os.getenv("POSTGRES_USER", "postgres"))
    password: str = field(
        default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "postgres")
    )
    database: str = field(default_factory=lambda: os.getenv("POSTGRES_DB", "etl_db"))

    def get_connection_string(self) -> str:
        """Get SQLAlchemy connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def validate(self) -> bool:
        """Validate configuration."""
        if not all([self.host, self.user, self.password, self.database]):
            logger.error("Missing required database configuration")
            return False
        return True


@dataclass
class PipelineConfig:
    """Pipeline configuration settings."""

    raw_data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("RAW_DATA_DIR", "data/raw"))
    )
    processed_data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))
    )
    log_dir: Path = field(default_factory=lambda: Path(os.getenv("LOG_DIR", "logs")))
    chunk_size: int = field(default_factory=lambda: int(os.getenv("CHUNK_SIZE", 10000)))
    max_retries: int = field(default_factory=lambda: int(os.getenv("MAX_RETRIES", 3)))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    kaggle_download: bool = field(
        default_factory=lambda: os.getenv("KAGGLE_DOWNLOAD", "false").lower() == "true"
    )
    kaggle_dataset: Optional[str] = field(
        default_factory=lambda: os.getenv("KAGGLE_DATASET")
    )
    kaggle_force: bool = field(
        default_factory=lambda: os.getenv("KAGGLE_FORCE_DOWNLOAD", "false").lower() == "true"
    )
    kaggle_file_pattern: str = field(
        default_factory=lambda: os.getenv("KAGGLE_FILE_PATTERN", "*.csv")
    )
    kaggle_quiet: bool = field(
        default_factory=lambda: os.getenv("KAGGLE_QUIET", "true").lower() == "true"
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
