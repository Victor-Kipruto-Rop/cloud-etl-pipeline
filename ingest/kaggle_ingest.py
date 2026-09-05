"""Main Kaggle data ingestion orchestrator with AWS integration."""
import os
import logging
import json
import boto3
import zipfile
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import time
from botocore.exceptions import ClientError

from src.secrets import SecretManager

logger = logging.getLogger(__name__)

_secret_manager = SecretManager()


class KaggleIngestor:
    """Orchestrates Kaggle dataset ingestion to S3.
    
    Handles authentication, download, versioning, and S3 upload with
    error handling, retries, and comprehensive logging.
    """
    
    def __init__(
        self,
        domain: str,
        kaggle_dataset: str,
        bucket_name: str,
        raw_prefix: str,
        aws_region: str = "us-east-1",
        retry_attempts: int = 3,
        retry_delay: int = 30
    ):
        """Initialize Kaggle ingestor.
        
        Args:
            domain: Domain name (ecommerce, healthcare, etc.)
            kaggle_dataset: Kaggle dataset identifier (owner/dataset-name)
            bucket_name: S3 bucket name
            raw_prefix: S3 prefix for raw data
            aws_region: AWS region
            retry_attempts: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.domain = domain
        self.kaggle_dataset = kaggle_dataset
        self.bucket_name = bucket_name
        self.raw_prefix = raw_prefix
        self.aws_region = aws_region
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=aws_region)
        self.secrets_client = boto3.client('secretsmanager', region_name=aws_region)
        
        # Set up Kaggle credentials
        self._setup_kaggle_credentials()
        
        logger.info(f"Initialized KaggleIngestor for domain: {domain}, dataset: {kaggle_dataset}")
    
    def _setup_kaggle_credentials(self) -> None:
        """Set up Kaggle API credentials from AWS Secrets Manager.
        
        Fetches credentials from Secrets Manager and configures Kaggle API.
        Falls back to environment variables if Secrets Manager unavailable.
        """
        try:
            secret_name = os.getenv('KAGGLE_SECRET_NAME', 'etl/kaggle/api-credentials')
            secret = _secret_manager.get_secret('KAGGLE_USERNAME', secret_id=secret_name)
            if isinstance(secret, dict):
                username = secret.get('username') or secret.get('KAGGLE_USERNAME')
                api_key = secret.get('key') or secret.get('KAGGLE_KEY')
                if username and api_key:
                    os.environ['KAGGLE_USERNAME'] = username
                    os.environ['KAGGLE_KEY'] = api_key
                    logger.info("Kaggle credentials loaded from secret manager")
                    return

            username = _secret_manager.get_secret('KAGGLE_USERNAME', default=None)
            api_key = _secret_manager.get_secret('KAGGLE_KEY', default=None)
            if username and api_key:
                os.environ['KAGGLE_USERNAME'] = str(username)
                os.environ['KAGGLE_KEY'] = str(api_key)
                logger.info("Kaggle credentials loaded from configured secrets")
                return

            raise ValueError("Kaggle secret values are not configured")

        except Exception as e:
            logger.warning(f"Could not load credentials from Secrets Manager: {e}")
            logger.info("Falling back to environment variables or kaggle.json")

            if not os.getenv('KAGGLE_USERNAME') or not os.getenv('KAGGLE_KEY'):
                logger.warning("KAGGLE_USERNAME and KAGGLE_KEY not set in environment")
    
    def download_dataset(self, download_path: str) -> List[str]:
        """Download Kaggle dataset to local directory.
        
        Args:
            download_path: Local directory to download files
            
        Returns:
            List of downloaded file paths
            
        Raises:
            Exception: If download fails after retries
        """
        from kaggle.api.kaggle_api_extended import KaggleApi
        
        api = KaggleApi()
        api.authenticate()
        
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Downloading dataset {self.kaggle_dataset} (attempt {attempt + 1}/{self.retry_attempts})")
                
                # Download dataset
                api.dataset_download_files(
                    self.kaggle_dataset,
                    path=download_path,
                    unzip=True
                )
                
                # Get list of downloaded files
                downloaded_files = list(Path(download_path).glob('*'))
                logger.info(f"Successfully downloaded {len(downloaded_files)} files")
                
                return [str(f) for f in downloaded_files if f.is_file()]
                
            except Exception as e:
                logger.error(f"Download attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    raise
    
    def upload_to_s3(
        self,
        local_files: List[str],
        s3_prefix: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """Upload files to S3 with versioning and metadata.
        
        Args:
            local_files: List of local file paths
            s3_prefix: S3 prefix (without bucket name)
            metadata: Optional metadata to attach to S3 objects
            
        Returns:
            List of S3 URIs
            
        Raises:
            Exception: If upload fails after retries
        """
        uploaded_files = []
        default_metadata = {
            'domain': self.domain,
            'kaggle_dataset': self.kaggle_dataset,
            'ingestion_timestamp': datetime.utcnow().isoformat()
        }
        
        if metadata:
            default_metadata.update(metadata)
        
        for local_file in local_files:
            filename = os.path.basename(local_file)
            s3_key = f"{s3_prefix}/{filename}"
            
            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"Uploading {filename} to s3://{self.bucket_name}/{s3_key}")
                    
                    self.s3_client.upload_file(
                        local_file,
                        self.bucket_name,
                        s3_key,
                        ExtraArgs={
                            'Metadata': default_metadata,
                            'ServerSideEncryption': 'AES256'
                        }
                    )
                    
                    s3_uri = f"s3://{self.bucket_name}/{s3_key}"
                    uploaded_files.append(s3_uri)
                    logger.info(f"Successfully uploaded to {s3_uri}")
                    break
                    
                except ClientError as e:
                    logger.error(f"Upload attempt {attempt + 1} failed for {filename}: {e}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)
                    else:
                        raise
        
        return uploaded_files
    
    def ingest(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Execute full ingestion pipeline.
        
        Downloads dataset from Kaggle and uploads to S3 with versioning.
        
        Args:
            date_str: Date string for versioning (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with ingestion results and metadata
            
        Raises:
            Exception: If ingestion fails
        """
        if date_str is None:
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
        
        start_time = datetime.utcnow()
        logger.info(f"Starting ingestion for {self.domain} domain on {date_str}")
        
        temp_dir = None
        try:
            # Create temporary directory for downloads
            temp_dir = tempfile.mkdtemp(prefix=f"kaggle_{self.domain}_")
            logger.info(f"Created temporary directory: {temp_dir}")
            
            # Download dataset
            local_files = self.download_dataset(temp_dir)
            logger.info(f"Downloaded {len(local_files)} files")
            
            # Calculate total size
            total_size = sum(os.path.getsize(f) for f in local_files)
            logger.info(f"Total download size: {total_size / (1024**2):.2f} MB")
            
            # Upload to S3
            s3_prefix = f"{self.raw_prefix}/{date_str}"
            uploaded_files = self.upload_to_s3(
                local_files,
                s3_prefix,
                metadata={'ingestion_date': date_str}
            )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                'status': 'success',
                'domain': self.domain,
                'kaggle_dataset': self.kaggle_dataset,
                'ingestion_date': date_str,
                'file_count': len(uploaded_files),
                'total_size_mb': total_size / (1024**2),
                'uploaded_files': uploaded_files,
                'duration_seconds': duration,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
            
            logger.info(f"Ingestion completed successfully in {duration:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            raise
            
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
    
    def verify_s3_upload(self, s3_prefix: str) -> Dict[str, Any]:
        """Verify files were uploaded to S3 successfully.
        
        Args:
            s3_prefix: S3 prefix to check
            
        Returns:
            Dictionary with verification results
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=s3_prefix
            )
            
            if 'Contents' not in response:
                return {
                    'verified': False,
                    'file_count': 0,
                    'message': 'No files found in S3'
                }
            
            files = response['Contents']
            total_size = sum(obj['Size'] for obj in files)
            
            return {
                'verified': True,
                'file_count': len(files),
                'total_size_mb': total_size / (1024**2),
                'files': [obj['Key'] for obj in files]
            }
            
        except ClientError as e:
            logger.error(f"S3 verification failed: {e}")
            return {
                'verified': False,
                'error': str(e)
            }


def main():
    """Command-line entry point for ingestion."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest Kaggle dataset to S3')
    parser.add_argument('--domain', required=True, 
                       choices=['ecommerce', 'healthcare', 'finance', 'sports', 'climate'],
                       help='Domain name')
    parser.add_argument('--date', help='Ingestion date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--config', default='config/domains.yaml', help='Configuration file path')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    from .config import IngestConfig
    config = IngestConfig.from_domain(args.domain, args.config)
    
    # Create ingestor
    ingestor = KaggleIngestor(
        domain=config.domain,
        kaggle_dataset=config.kaggle_dataset,
        bucket_name=config.bucket_name,
        raw_prefix=config.raw_prefix,
        aws_region=config.aws_region,
        retry_attempts=config.retry_attempts,
        retry_delay=config.retry_delay
    )
    
    # Run ingestion
    result = ingestor.ingest(args.date)
    
    # Print results
    print(json.dumps(result, indent=2))
    
    # Verify upload
    date_str = args.date or datetime.utcnow().strftime('%Y-%m-%d')
    s3_prefix = f"{config.raw_prefix}/{date_str}"
    verification = ingestor.verify_s3_upload(s3_prefix)
    print("\nVerification:")
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    main()
