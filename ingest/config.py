"""Ingestion configuration management."""
import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import yaml

logger = logging.getLogger(__name__)


@dataclass
class IngestConfig:
    """Configuration for data ingestion."""
    
    domain: str
    kaggle_dataset: str
    bucket_name: str
    raw_prefix: str
    aws_region: str
    retry_attempts: int = 3
    retry_delay: int = 30
    
    @classmethod
    def from_domain(cls, domain: str, config_path: str = "config/domains.yaml") -> "IngestConfig":
        """Create configuration from domain name.
        
        Args:
            domain: Domain name (ecommerce, healthcare, finance, sports, climate)
            config_path: Path to domains configuration file
            
        Returns:
            IngestConfig instance
            
        Raises:
            ValueError: If domain not found in configuration
        """
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if domain not in config['domains']:
            raise ValueError(f"Domain '{domain}' not found in configuration")
        
        domain_config = config['domains'][domain]
        global_config = config['global']
        
        return cls(
            domain=domain,
            kaggle_dataset=domain_config['kaggle_dataset'],
            bucket_name=global_config['bucket_name'],
            raw_prefix=f"raw/{domain}",
            aws_region=global_config['region'],
            retry_attempts=global_config.get('retry_attempts', 3),
            retry_delay=global_config.get('retry_delay_seconds', 30)
        )
    
    def get_s3_path(self, date_str: str) -> str:
        """Get S3 path for raw data.
        
        Args:
            date_str: Date string (YYYY-MM-DD)
            
        Returns:
            S3 path
        """
        return f"s3://{self.bucket_name}/{self.raw_prefix}/{date_str}/"
