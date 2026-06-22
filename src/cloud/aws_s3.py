"""AWS S3 helpers for cloud-native ETL pipelines."""

import logging
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, Optional

import boto3
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


def create_s3_client(
    region_name: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    session_token: Optional[str] = None,
):
    """Create a boto3 S3 client using optional credentials."""
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
        region_name=region_name,
    )
    return session.client("s3")


def upload_file(
    local_path: Path,
    bucket: str,
    key: str,
    region_name: Optional[str] = None,
    extra_args: Optional[Dict[str, str]] = None,
) -> str:
    """Upload a local file to S3."""
    client = create_s3_client(region_name=region_name)
    local_path = Path(local_path)
    if not local_path.exists():
        raise FileNotFoundError(f"Local file not found: {local_path}")

    try:
        client.upload_file(
            str(local_path),
            bucket,
            key,
            ExtraArgs=extra_args or {},
        )
        s3_uri = f"s3://{bucket}/{key}"
        logger.info(f"Uploaded {local_path} to {s3_uri}")
        return s3_uri
    except (BotoCoreError, ClientError) as exc:
        logger.error(f"Failed to upload {local_path} to s3://{bucket}/{key}: {exc}")
        raise


def upload_directory(
    directory: Path,
    bucket: str,
    prefix: str,
    pattern: str = "*.csv",
    region_name: Optional[str] = None,
) -> int:
    """Upload all files matching pattern in a directory to S3."""
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    files = list(directory.glob(pattern))
    count = 0
    for path in files:
        key = f"{prefix.rstrip('/')}/{path.name}"
        upload_file(path, bucket, key, region_name=region_name)
        count += 1
    logger.info(f"Uploaded {count} files from {directory} to s3://{bucket}/{prefix}")
    return count


def upload_dataframe_as_parquet(
    df: pd.DataFrame,
    bucket: str,
    key: str,
    region_name: Optional[str] = None,
    compression: str = "snappy",
    extra_args: Optional[Dict[str, str]] = None,
) -> str:
    """Upload a DataFrame as a Parquet file to S3."""
    client = create_s3_client(region_name=region_name)
    buffer = BytesIO()
    df.to_parquet(buffer, index=False, compression=compression)
    buffer.seek(0)

    try:
        client.upload_fileobj(buffer, bucket, key, ExtraArgs=extra_args or {})
        s3_uri = f"s3://{bucket}/{key}"
        logger.info(f"Uploaded DataFrame as Parquet to {s3_uri}")
        return s3_uri
    except (BotoCoreError, ClientError) as exc:
        logger.error(f"Failed to upload Parquet to s3://{bucket}/{key}: {exc}")
        raise
