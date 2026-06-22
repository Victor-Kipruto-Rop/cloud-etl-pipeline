"""Redshift loader helpers for cloud ETL pipelines."""

import logging
import os
from pathlib import Path
from typing import Dict, Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
import pandas as pd

logger = logging.getLogger(__name__)

REDSHIFT_TYPE_MAP = {
    "int64": "BIGINT",
    "int32": "INTEGER",
    "float64": "DOUBLE PRECISION",
    "float32": "REAL",
    "bool": "BOOLEAN",
    "datetime64[ns]": "TIMESTAMP",
    "object": "VARCHAR(65535)",
}


def redshift_connection(
    host: str,
    database: str,
    user: str,
    password: str,
    port: int = 5439,
):
    """Create a Redshift connection using psycopg2."""
    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password,
    )
    conn.autocommit = True
    return conn


def dataframe_to_redshift_schema(df: pd.DataFrame) -> str:
    """Create a Redshift-compatible CREATE TABLE schema from a DataFrame."""
    columns = []
    for name, dtype in df.dtypes.items():
        redshift_type = REDSHIFT_TYPE_MAP.get(str(dtype), "VARCHAR(65535)")
        sanitized = name.lower().replace(" ", "_")
        columns.append(f"{sanitized} {redshift_type}")
    return ",\n    ".join(columns)


def create_table_if_not_exists(
    conn,
    table_name: str,
    df: pd.DataFrame,
    schema: str = "public",
    diststyle: str = "AUTO",
) -> None:
    """Create a Redshift table if it does not exist."""
    create_sql = sql.SQL(
        "CREATE TABLE IF NOT EXISTS {}.{} ({} ) DISTSTYLE {}"
    ).format(
        sql.Identifier(schema),
        sql.Identifier(table_name),
        sql.SQL(dataframe_to_redshift_schema(df)),
        sql.SQL(diststyle),
    )
    with conn.cursor() as cursor:
        cursor.execute(create_sql)
        logger.info(f"Ensured Redshift table exists: {schema}.{table_name}")


def copy_parquet_from_s3(
    conn,
    table_name: str,
    s3_uri: str,
    iam_role_arn: str,
    region: str,
    schema: str = "public",
    extra_options: Optional[str] = None,
) -> None:
    """Load a Parquet file from S3 into Redshift using COPY."""
    copy_sql = sql.SQL(
        "COPY {}.{} FROM %s IAM_ROLE %s REGION %s FORMAT AS PARQUET {extra}".format(
            extra=extra_options or ""
        )
    ).format(sql.Identifier(schema), sql.Identifier(table_name))

    with conn.cursor() as cursor:
        cursor.execute(copy_sql, (s3_uri, iam_role_arn, region))
        logger.info(f"Copied {s3_uri} into Redshift table {schema}.{table_name}")


def load_dataframe_to_redshift(
    df: pd.DataFrame,
    table_name: str,
    bucket: str,
    key: str,
    iam_role_arn: str,
    region: str,
    schema: str = "public",
    redshift_host: Optional[str] = None,
    redshift_database: Optional[str] = None,
    redshift_user: Optional[str] = None,
    redshift_password: Optional[str] = None,
    port: int = 5439,
) -> None:
    """Write a DataFrame to Parquet, upload to S3, and load it into Redshift."""
    if redshift_host is None:
        redshift_host = os.getenv("REDSHIFT_HOST")
    if redshift_database is None:
        redshift_database = os.getenv("REDSHIFT_DB")
    if redshift_user is None:
        redshift_user = os.getenv("REDSHIFT_USER")
    if redshift_password is None:
        redshift_password = os.getenv("REDSHIFT_PASSWORD")

    if not all([redshift_host, redshift_database, redshift_user, redshift_password]):
        raise ValueError("Missing Redshift connection configuration")

    conn = redshift_connection(
        host=redshift_host,
        database=redshift_database,
        user=redshift_user,
        password=redshift_password,
        port=port,
    )
    try:
        create_table_if_not_exists(conn, table_name, df, schema=schema)
        s3_uri = f"s3://{bucket}/{key}"
        copy_parquet_from_s3(conn, table_name, s3_uri, iam_role_arn, region)
    finally:
        conn.close()
