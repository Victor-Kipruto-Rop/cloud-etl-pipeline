"""Sports domain-specific ingestion script."""
import logging
from typing import Dict, Any
from .kaggle_ingest import KaggleIngestor
from .config import IngestConfig

logger = logging.getLogger(__name__)


class SportsIngestor(KaggleIngestor):
    """Sports domain specific ingestor for soccer database."""
    
    def __init__(self, bucket_name: str, aws_region: str = "us-east-1"):
        """Initialize sports ingestor.
        
        Args:
            bucket_name: S3 bucket name
            aws_region: AWS region
        """
        super().__init__(
            domain="sports",
            kaggle_dataset="hugomathien/soccer",
            bucket_name=bucket_name,
            raw_prefix="raw/sports",
            aws_region=aws_region
        )
    
    def validate_dataset(self, local_files: list) -> Dict[str, Any]:
        """Validate sports dataset files.
        
        Args:
            local_files: List of downloaded file paths
            
        Returns:
            Validation results
        """
        expected_files = {'database.sqlite'}
        
        file_names = {file.split('/')[-1] for file in local_files}
        sqlite_files = [f for f in file_names if f.endswith('.sqlite') or f.endswith('.db')]
        
        validation_result = {
            'is_valid': len(sqlite_files) > 0,
            'expected_count': len(expected_files),
            'actual_count': len(file_names),
            'sqlite_files': sqlite_files
        }
        
        if not validation_result['is_valid']:
            logger.warning("No SQLite database file found in dataset")
        else:
            logger.info("Sports dataset validation passed")
        
        return validation_result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    config = IngestConfig.from_domain('sports')
    ingestor = SportsIngestor(
        bucket_name=config.bucket_name,
        aws_region=config.aws_region
    )
    result = ingestor.ingest()
    print(f"Ingestion result: {result}")
