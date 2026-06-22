"""Common utility functions for Glue ETL jobs."""
import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

logger = logging.getLogger(__name__)


def initialize_glue_job(
    job_name: str,
    required_args: Optional[List[str]] = None
) -> tuple[SparkContext, GlueContext, Job, Dict[str, str]]:
    """Initialize Glue job with standard setup.
    
    Args:
        job_name: Name of the Glue job
        required_args: List of required job arguments
        
    Returns:
        Tuple of (SparkContext, GlueContext, Job, args)
    """
    # Get job arguments
    default_args = ['JOB_NAME']
    if required_args:
        default_args.extend(required_args)
    
    args = getResolvedOptions(sys.argv, default_args)
    
    # Initialize Spark and Glue contexts
    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)
    
    # Configure Spark for better performance
    spark.conf.set("spark.sql.adaptive.enabled", "true")
    spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
    
    logger.info(f"Initialized Glue job: {job_name}")
    logger.info(f"Job arguments: {args}")
    
    return sc, glueContext, job, args


def normalize_column_names(df, snake_case: bool = True):
    """Normalize DataFrame column names.
    
    Args:
        df: PySpark DataFrame
        snake_case: Convert to snake_case if True
        
    Returns:
        DataFrame with normalized column names
    """
    import re
    from pyspark.sql import functions as F
    
    if snake_case:
        # Convert to snake_case
        new_columns = []
        for col in df.columns:
            # Replace spaces and special chars with underscores
            col_clean = re.sub(r'[^\w\s]', '_', col)
            # Replace multiple spaces/underscores with single underscore
            col_clean = re.sub(r'[\s_]+', '_', col_clean)
            # Convert to lowercase
            col_clean = col_clean.lower()
            # Remove leading/trailing underscores
            col_clean = col_clean.strip('_')
            new_columns.append(col_clean)
        
        # Rename columns
        for old_col, new_col in zip(df.columns, new_columns):
            df = df.withColumnRenamed(old_col, new_col)
    else:
        # Just lowercase
        for col in df.columns:
            df = df.withColumnRenamed(col, col.lower())
    
    logger.info(f"Normalized {len(df.columns)} column names")
    return df


def deduplicate_dataframe(
    df,
    partition_columns: Optional[List[str]] = None,
    order_columns: Optional[List[str]] = None
):
    """Remove duplicate rows from DataFrame.
    
    Args:
        df: PySpark DataFrame
        partition_columns: Columns to partition by for deduplication
        order_columns: Columns to order by (keeps first row)
        
    Returns:
        Deduplicated DataFrame
    """
    from pyspark.sql import Window
    from pyspark.sql import functions as F
    
    initial_count = df.count()
    
    if partition_columns and order_columns:
        # Use window function for complex deduplication
        window = Window.partitionBy(partition_columns).orderBy(order_columns)
        df = df.withColumn("_row_num", F.row_number().over(window))
        df = df.filter(F.col("_row_num") == 1).drop("_row_num")
    else:
        # Simple deduplication
        df = df.dropDuplicates()
    
    final_count = df.count()
    duplicates_removed = initial_count - final_count
    
    logger.info(f"Removed {duplicates_removed} duplicate rows ({initial_count} -> {final_count})")
    
    return df


def add_audit_columns(df):
    """Add standard audit columns to DataFrame.
    
    Args:
        df: PySpark DataFrame
        
    Returns:
        DataFrame with audit columns
    """
    from pyspark.sql import functions as F
    
    df = df.withColumn("etl_insert_timestamp", F.current_timestamp())
    df = df.withColumn("etl_update_timestamp", F.current_timestamp())
    df = df.withColumn("etl_batch_id", F.lit(datetime.utcnow().strftime("%Y%m%d%H%M%S")))
    
    logger.info("Added audit columns")
    return df


def write_to_s3_parquet(
    df,
    output_path: str,
    partition_columns: Optional[List[str]] = None,
    mode: str = "overwrite",
    compression: str = "snappy"
) -> None:
    """Write DataFrame to S3 in Parquet format.
    
    Args:
        df: PySpark DataFrame
        output_path: S3 output path
        partition_columns: Columns to partition by
        mode: Write mode (overwrite, append, etc.)
        compression: Compression codec (snappy, gzip, etc.)
    """
    logger.info(f"Writing DataFrame to {output_path}")
    logger.info(f"Partition columns: {partition_columns}")
    logger.info(f"Mode: {mode}, Compression: {compression}")
    
    writer = df.write.mode(mode).option("compression", compression)
    
    if partition_columns:
        writer = writer.partitionBy(partition_columns)
    
    writer.parquet(output_path)
    
    logger.info(f"Successfully wrote {df.count()} rows to {output_path}")


def log_dataframe_info(df, name: str = "DataFrame") -> None:
    """Log DataFrame information for debugging.
    
    Args:
        df: PySpark DataFrame
        name: Name/description of the DataFrame
    """
    logger.info(f"=== {name} Info ===")
    logger.info(f"Row count: {df.count()}")
    logger.info(f"Column count: {len(df.columns)}")
    logger.info(f"Columns: {df.columns}")
    logger.info(f"Schema:")
    df.printSchema()
    logger.info(f"Sample data (5 rows):")
    df.show(5, truncate=False)


def get_latest_partition(spark, s3_path: str, partition_column: str = "ingestion_date") -> str:
    """Get the latest partition from an S3 path.
    
    Args:
        spark: Spark session
        s3_path: Base S3 path
        partition_column: Partition column name
        
    Returns:
        Latest partition value
    """
    import boto3
    from urllib.parse import urlparse
    
    parsed = urlparse(s3_path)
    bucket = parsed.netloc
    prefix = parsed.path.lstrip('/')
    
    s3_client = boto3.client('s3')
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter='/')
    
    if 'CommonPrefixes' not in response:
        raise ValueError(f"No partitions found in {s3_path}")
    
    partitions = [p['Prefix'].rstrip('/').split('/')[-1] for p in response['CommonPrefixes']]
    latest = sorted(partitions)[-1]
    
    logger.info(f"Latest partition: {latest}")
    return latest
