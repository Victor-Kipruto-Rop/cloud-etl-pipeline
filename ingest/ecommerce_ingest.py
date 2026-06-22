"""E-commerce domain-specific ingestion script."""
import logging
from typing import Dict, Any
from .kaggle_ingest import KaggleIngestor
from .config import IngestConfig

logger = logging.getLogger(__name__)


class EcommerceIngestor(KaggleIngestor):
    """E-commerce domain specific ingestor for Brazilian e-commerce dataset."""
    
    def __init__(self, bucket_name: str, aws_region: str = "us-east-1"):
        """Initialize e-commerce ingestor.
        
        Args:
            bucket_name: S3 bucket name
            aws_region: AWS region
        """
        super().__init__(
            domain="ecommerce",
            kaggle_dataset="olistbr/brazilian-ecommerce",
            bucket_name=bucket_name,
            raw_prefix="raw/ecommerce",
            aws_region=aws_region
        )
    
    def validate_dataset(self, local_files: list) -> Dict[str, Any]:
        """Validate e-commerce dataset files.
        
        Args:
            local_files: List of downloaded file paths
            
        Returns:
            Validation results
        """
        expected_files = {
            'olist_customers_dataset.csv',
            'olist_orders_dataset.csv',
            'olist_order_items_dataset.csv',
            'olist_products_dataset.csv',
            'olist_sellers_dataset.csv',
            'olist_order_payments_dataset.csv',
            'olist_order_reviews_dataset.csv',
            'product_category_name_translation.csv'
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
            logger.info("E-commerce dataset validation passed")
        
        return validation_result


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    
    config = IngestConfig.from_domain('ecommerce')
    ingestor = EcommerceIngestor(
        bucket_name=config.bucket_name,
        aws_region=config.aws_region
    )
    result = ingestor.ingest()
    print(f"Ingestion result: {result}")
