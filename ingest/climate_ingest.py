"""Climate domain-specific ingestion script."""
import logging
from typing import Dict, Any
from .kaggle_ingest import KaggleIngestor
from .config import IngestConfig

logger = logging.getLogger(__name__)


class ClimateIngestor(KaggleIngestor):
    """Climate domain specific ingestor for temperature data."""
    
    def __init__(self, bucket_name: str, aws_region: str = "us-east-1"):
        """Initialize climate ingestor.
        
        Args:
            bucket_name: S3 bucket name
            aws_region: AWS region
        """
        super().__init__(
            domain="climate",
            kaggle_dataset="berkeleyearth/climate-change-earth-surface-temperature-data",
            bucket_name=bucket_name,
            raw_prefix="raw/climate",
            aws_region=aws_region
        )
    
    def validate_dataset(self, local_files: list) -> Dict[str, Any]:
        """Validate climate dataset files.
        
        Args:
            local_files: List of downloaded file paths
            
        Returns:
            Validation results
        """
        expected_files = {
            'GlobalTemperatures.csv',
            'GlobalLandTemperaturesByCity.csv',
            'GlobalLandTemperaturesByCountry.csv',
            'GlobalLandTemperaturesByState.csv'
        }
        
        file_names = {file.split('/')[-1] for file in local_files}
        missing_files = expected_files - file_names
        extra_files = file_names - expected_files
        
        validation_result = {
            'is_valid': len(missing_files) == 0,
            'expected_count': len(expected_files),
            'actual_count': len(file_names),
            'missing_files': list(missing_files),
            'extra_files': list(extra_files)
        }
        
        if not validation_result['is_valid']:
            logger.warning(f"Dataset validation failed. Missing files: {missing_files}")
        else:
            logger.info("Climate dataset validation passed")
        
        return validation_result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    config = IngestConfig.from_domain('climate')
    ingestor = ClimateIngestor(
        bucket_name=config.bucket_name,
        aws_region=config.aws_region
    )
    result = ingestor.ingest()
    print(f"Ingestion result: {result}")
