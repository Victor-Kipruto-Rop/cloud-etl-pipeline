"""Kaggle data ingestion package."""
from .kaggle_ingest import KaggleIngestor
from .config import IngestConfig

__all__ = ["KaggleIngestor", "IngestConfig"]
