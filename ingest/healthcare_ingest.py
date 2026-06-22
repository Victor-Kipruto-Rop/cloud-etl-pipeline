"""Healthcare domain-specific ingestion script."""
import logging
from typing import Dict, Any
from .kaggle_ingest import KaggleIngestor
from .config import IngestConfig

logger = logging.getLogger(__name__)


class HealthcareIngestor(KaggleIngestor):
    """Healthcare domain specific ingestor for heart disease dataset."""
    
    def __init__(self, bucket_name: str, aws_region: str = "us-east-1"):
        """Initialize healthcare ingestor.
        
        Args:
            bucket_name: S3 bucket name
            aws_region: AWS region
        """
        super().__init__(
            domain="healthcare",
            kaggle_dataset="uciml/heart-disease-uci",
            bucket_name=bucket_name,
            raw_prefix="raw/healthcare",
            aws_region=aws_region
        )
    
    def validate_dataset(self, local_files: list) -> Dict[str, Any]:
        """Validate healthcare dataset files.
        
        Args:
            local_files: List of downloaded file paths
            
        Returns:
            Validation results
        """
        expected_files = {'heart.csv'}
        
        file_names = {file.split('/')[-1] for file in local_files}
        missing_files = expected_files - file_names
        
        validation_result = {
            'is_valid': len(missing_files) == 0,
            'expected_count': len(expected_files),
            'actual_count': len(file_names),
            'missing_files': list(missing_files)
        }
        
        if not validation_result['is_valid']:
            logger.warning(f"Dataset validation failed. Missing files: {missing_files}")
        else:
            logger.info("Healthcare dataset validation passed")
        
        return validation_result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    config = IngestConfig.from_domain('healthcare')
    ingestor = HealthcareIngestor(
        bucket_name=config.bucket_name,
        aws_region=config.aws_region
    )
    result = ingestor.ingest()
    print(f"Ingestion result: {result}")
