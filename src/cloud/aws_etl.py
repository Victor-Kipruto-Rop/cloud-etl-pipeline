"""AWS ETL orchestration script for Kaggle datasets."""

import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

from dotenv import load_dotenv
import pandas as pd

from src.cloud.aws_redshift import load_dataframe_to_redshift
from src.cloud.aws_s3 import upload_directory, upload_file, upload_dataframe_as_parquet
from src.extract.kaggle_data import download_kaggle_dataset
from src.extract.extract_data import ExtractionError, extract_csv
from src.transform.transform_data import TransformError, transform
from src.validation import ValidationError, parse_required_columns, validate_df

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s:%(message)s")


def _get_env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() == "true"


def _parse_list(env_var: str) -> List[str]:
    value = os.getenv(env_var, "")
    return [item.strip() for item in value.split(",") if item.strip()]


def run_aws_etl() -> bool:
    load_dotenv()

    raw_dir = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
    processed_dir = Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        raise ValueError("AWS_S3_BUCKET must be set for AWS ETL mode")

    raw_prefix = os.getenv("RAW_S3_PREFIX", "raw")
    processed_prefix = os.getenv("PROCESSED_S3_PREFIX", "processed")
    region = os.getenv("AWS_REGION", "us-east-1")
    iam_role_arn = os.getenv("REDSHIFT_IAM_ROLE_ARN")
    redshift_enabled = bool(os.getenv("REDSHIFT_HOST") and os.getenv("REDSHIFT_DB"))

    if _get_env_bool("KAGGLE_DOWNLOAD"):
        dataset = os.getenv("KAGGLE_DATASET")
        if not dataset:
            raise ValueError("KAGGLE_DATASET must be set when KAGGLE_DOWNLOAD=true")
        logger.info(f"Downloading Kaggle dataset: {dataset}")
        download_kaggle_dataset(
            dataset=dataset,
            destination=raw_dir,
            unzip=True,
            force=_get_env_bool("KAGGLE_FORCE_DOWNLOAD"),
            quiet=_get_env_bool("KAGGLE_QUIET", default="true"),
            file_pattern=os.getenv("KAGGLE_FILE_PATTERN", "*.csv"),
        )

    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        logger.warning("No CSV files found in raw directory")
        return False

    logger.info(f"Found {len(csv_files)} CSV file(s) to process")

    for csv_file in csv_files:
        logger.info(f"Processing {csv_file.name}")
        try:
            df = extract_csv(csv_file)
            required_columns = parse_required_columns(os.getenv("REQUIRED_COLUMNS"))
            validate_df(df, required_columns=required_columns)
            df_transformed = transform(df, normalize_cols=True, handle_missing="drop_all")

            output_path = processed_dir / f"{csv_file.stem}.parquet"
            df_transformed.to_parquet(output_path, index=False, compression="snappy")
            logger.info(f"Wrote processed Parquet to {output_path}")

            upload_file(csv_file, bucket, f"{raw_prefix}/{csv_file.name}", region_name=region)
            upload_dataframe_as_parquet(
                df_transformed,
                bucket,
                f"{processed_prefix}/{csv_file.stem}.parquet",
                region_name=region,
            )

            if redshift_enabled:
                if not iam_role_arn:
                    raise ValueError("REDSHIFT_IAM_ROLE_ARN must be set to COPY into Redshift")
                load_dataframe_to_redshift(
                    df_transformed,
                    csv_file.stem,
                    bucket,
                    f"{processed_prefix}/{csv_file.stem}.parquet",
                    iam_role_arn=iam_role_arn,
                    region=region,
                    schema=os.getenv("REDSHIFT_SCHEMA", "public"),
                )

        except (ExtractionError, ValidationError, TransformError, ValueError) as exc:
            logger.error(f"Failed to process {csv_file.name}: {exc}")
            continue

    if upload_directory(raw_dir, bucket, raw_prefix, pattern="*.csv", region_name=region) == 0:
        logger.warning("No raw files uploaded to S3")

    return True


if __name__ == "__main__":
    success = run_aws_etl()
    if not success:
        raise SystemExit(1)
