"""Finance domain-specific ingestion script."""
import logging
from typing import Dict, Any
from .kaggle_ingest import KaggleIngestor
from .config import IngestConfig

logger = logging.getLogger(__name__)


class FinanceIngestor(KaggleIngestor):
    """Finance domain specific ingestor for stock market data."""
    
    def __init__(self, bucket_name: str, aws_region: str = "us-east-1"):
        """Initialize finance ingestor.
        
        Args:
            bucket_name: S3 bucket name
            aws_region: AWS region
        """
        super().__init__(
            domain="finance",
            kaggle_dataset="borismarjanovic/price-volume-data-for-all-us-stocks-etfs",
            bucket_name=bucket_name,
            raw_prefix="raw/finance",
            aws_region=aws_region
        )
    
    def validate_dataset(self, local_files: list) -> Dict[str, Any]:
        """Validate finance dataset files.
        
        Args:
            local_files: List of downloaded file paths
            
        Returns:
            Validation results
        """
        # Finance dataset has many stock/ETF files
        file_names = {file.split('/')[-1] for file in local_files}
        
        # Check for expected directories or file patterns
        txt_files = [f for f in file_names if f.endswith('.txt')]
        
        validation_result = {
            'is_valid': len(txt_files) > 0,
            'total_files': len(file_names),
            'txt_files': len(txt_files),
            'sample_files': list(txt_files)[:10]
        }
        
        if not validation_result['is_valid']:
            logger.warning("No .txt stock files found in dataset")
        else:
            logger.info(f"Finance dataset validation passed: {len(txt_files)} stock files found")
        
        return validation_result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    config = IngestConfig.from_domain('finance')
    ingestor = FinanceIngestor(
        bucket_name=config.bucket_name,
        aws_region=config.aws_region
    )
    result = ingestor.ingest()
    print(f"Ingestion result: {result}")
