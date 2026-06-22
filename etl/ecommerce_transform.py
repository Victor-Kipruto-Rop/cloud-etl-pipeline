"""E-commerce domain AWS Glue PySpark ETL transformation job.

This job transforms raw e-commerce data from S3 into a star schema
optimized for analytics, with fact and dimension tables.
"""
import sys
import logging
from datetime import datetime
from typing import Dict, Any
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame

# Import common utilities
from common.utils import (
    initialize_glue_job,
    normalize_column_names,
    deduplicate_dataframe,
    add_audit_columns,
    write_to_s3_parquet,
    log_dataframe_info
)
from common.transformations import (
    handle_nulls,
    cast_columns,
    add_date_partitions,
    create_surrogate_key
)
from common.data_quality import DataQualityChecker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EcommerceETL:
    """E-commerce ETL transformation job."""
    
    def __init__(self, glue_context: GlueContext, spark_context: SparkContext):
        """Initialize ETL job.
        
        Args:
            glue_context: AWS Glue context
            spark_context: Spark context
        """
        self.glue_context = glue_context
        self.spark = glue_context.spark_session
        self.sc = spark_context
        
    def read_raw_data(self, s3_path: str, file_name: str) -> DataFrame:
        """Read raw CSV data from S3.
        
        Args:
            s3_path: S3 path to raw data
            file_name: Name of the CSV file
            
        Returns:
            DataFrame with raw data
        """
        full_path = f"{s3_path}/{file_name}"
        logger.info(f"Reading raw data from {full_path}")
        
        df = self.spark.read.format("csv") \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .load(full_path)
        
        logger.info(f"Read {df.count()} rows from {file_name}")
        return df
    
    def transform_orders(self, orders_df: DataFrame) -> DataFrame:
        """Transform orders data into fact table.
        
        Args:
            orders_df: Raw orders DataFrame
            
        Returns:
            Transformed fact_orders DataFrame
        """
        logger.info("Transforming orders to fact table")
        
        # Normalize column names
        df = normalize_column_names(orders_df)
        
        # Cast columns to correct types
        schema_mapping = {
            'order_id': 'string',
            'customer_id': 'string',
            'order_status': 'string',
            'order_purchase_timestamp': 'timestamp',
            'order_approved_at': 'timestamp',
            'order_delivered_carrier_date': 'timestamp',
            'order_delivered_customer_date': 'timestamp',
            'order_estimated_delivery_date': 'timestamp'
        }
        df = cast_columns(df, schema_mapping)
        
        # Handle nulls
        null_strategies = {
            'order_id': 'drop',
            'customer_id': 'drop',
            'order_status': 'unknown'
        }
        df = handle_nulls(df, null_strategies)
        
        # Add calculated columns
        df = df.withColumn(
            'delivery_days',
            F.datediff(
                F.col('order_delivered_customer_date'),
                F.col('order_purchase_timestamp')
            )
        )
        
        df = df.withColumn(
            'is_delayed',
            F.when(
                F.col('order_delivered_customer_date') > F.col('order_estimated_delivery_date'),
                True
            ).otherwise(False)
        )
        
        # Add date partitions
        df = add_date_partitions(
            df,
            'order_purchase_timestamp',
            include_year=True,
            include_month=True,
            include_quarter=True
        )
        
        # Rename partition columns for consistency
        df = df.withColumnRenamed('order_purchase_timestamp_year', 'order_year') \
               .withColumnRenamed('order_purchase_timestamp_month', 'order_month') \
               .withColumnRenamed('order_purchase_timestamp_quarter', 'order_quarter')
        
        # Add audit columns
        df = add_audit_columns(df)
        
        # Deduplicate
        df = deduplicate_dataframe(df, ['order_id'], ['order_purchase_timestamp'])
        
        logger.info(f"Transformed {df.count()} orders")
        return df
    
    def transform_customers(self, customers_df: DataFrame) -> DataFrame:
        """Transform customers data into dimension table.
        
        Args:
            customers_df: Raw customers DataFrame
            
        Returns:
            Transformed dim_customers DataFrame
        """
        logger.info("Transforming customers to dimension table")
        
        # Normalize column names
        df = normalize_column_names(customers_df)
        
        # Cast columns
        schema_mapping = {
            'customer_id': 'string',
            'customer_unique_id': 'string',
            'customer_zip_code_prefix': 'string',
            'customer_city': 'string',
            'customer_state': 'string'
        }
        df = cast_columns(df, schema_mapping)
        
        # Handle nulls
        null_strategies = {
            'customer_id': 'drop',
            'customer_city': 'Unknown',
            'customer_state': 'Unknown'
        }
        df = handle_nulls(df, null_strategies)
        
        # Standardize state codes
        df = df.withColumn('customer_state', F.upper(F.col('customer_state')))
        
        # Add surrogate key
        df = create_surrogate_key(df, ['customer_id'], 'customer_sk')
        
        # Add audit columns
        df = add_audit_columns(df)
        
        # Deduplicate
        df = deduplicate_dataframe(df, ['customer_id'], ['customer_unique_id'])
        
        logger.info(f"Transformed {df.count()} customers")
        return df
    
    def transform_products(self, products_df: DataFrame, categories_df: DataFrame) -> DataFrame:
        """Transform products data into dimension table.
        
        Args:
            products_df: Raw products DataFrame
            categories_df: Product category translations
            
        Returns:
            Transformed dim_products DataFrame
        """
        logger.info("Transforming products to dimension table")
        
        # Normalize column names
        products_df = normalize_column_names(products_df)
        categories_df = normalize_column_names(categories_df)
        
        # Join with category translations
        df = products_df.join(
            categories_df,
            products_df.product_category_name == categories_df.product_category_name,
            'left'
        ).drop(categories_df.product_category_name)
        
        # Cast columns
        schema_mapping = {
            'product_id': 'string',
            'product_category_name': 'string',
            'product_name_length': 'integer',
            'product_description_length': 'integer',
            'product_photos_qty': 'integer',
            'product_weight_g': 'double',
            'product_length_cm': 'double',
            'product_height_cm': 'double',
            'product_width_cm': 'double'
        }
        df = cast_columns(df, schema_mapping)
        
        # Calculate product volume
        df = df.withColumn(
            'product_volume_cm3',
            F.col('product_length_cm') * F.col('product_height_cm') * F.col('product_width_cm')
        )
        
        # Categorize products by size
        df = df.withColumn(
            'product_size_category',
            F.when(F.col('product_volume_cm3') < 1000, 'Small')
            .when((F.col('product_volume_cm3') >= 1000) & (F.col('product_volume_cm3') < 10000), 'Medium')
            .otherwise('Large')
        )
        
        # Add surrogate key
        df = create_surrogate_key(df, ['product_id'], 'product_sk')
        
        # Add audit columns
        df = add_audit_columns(df)
        
        # Deduplicate
        df = deduplicate_dataframe(df, ['product_id'], None)
        
        logger.info(f"Transformed {df.count()} products")
        return df
    
    def transform_sellers(self, sellers_df: DataFrame) -> DataFrame:
        """Transform sellers data into dimension table.
        
        Args:
            sellers_df: Raw sellers DataFrame
            
        Returns:
            Transformed dim_sellers DataFrame
        """
        logger.info("Transforming sellers to dimension table")
        
        # Normalize column names
        df = normalize_column_names(sellers_df)
        
        # Cast columns
        schema_mapping = {
            'seller_id': 'string',
            'seller_zip_code_prefix': 'string',
            'seller_city': 'string',
            'seller_state': 'string'
        }
        df = cast_columns(df, schema_mapping)
        
        # Standardize state codes
        df = df.withColumn('seller_state', F.upper(F.col('seller_state')))
        
        # Add surrogate key
        df = create_surrogate_key(df, ['seller_id'], 'seller_sk')
        
        # Add audit columns
        df = add_audit_columns(df)
        
        # Deduplicate
        df = deduplicate_dataframe(df, ['seller_id'], None)
        
        logger.info(f"Transformed {df.count()} sellers")
        return df
    
    def transform_order_items(
        self,
        order_items_df: DataFrame,
        orders_df: DataFrame,
        products_df: DataFrame,
        sellers_df: DataFrame
    ) -> DataFrame:
        """Transform order items with enriched data.
        
        Args:
            order_items_df: Raw order items DataFrame
            orders_df: Transformed orders DataFrame
            products_df: Transformed products DataFrame
            sellers_df: Transformed sellers DataFrame
            
        Returns:
            Enriched fact_order_items DataFrame
        """
        logger.info("Transforming order items with enrichment")
        
        # Normalize column names
        df = normalize_column_names(order_items_df)
        
        # Cast columns
        schema_mapping = {
            'order_id': 'string',
            'order_item_id': 'integer',
            'product_id': 'string',
            'seller_id': 'string',
            'shipping_limit_date': 'timestamp',
            'price': 'double',
            'freight_value': 'double'
        }
        df = cast_columns(df, schema_mapping)
        
        # Calculate total value
        df = df.withColumn('total_value', F.col('price') + F.col('freight_value'))
        
        # Join with orders to get date partitions
        df = df.join(
            orders_df.select('order_id', 'order_year', 'order_month'),
            'order_id',
            'left'
        )
        
        # Add audit columns
        df = add_audit_columns(df)
        
        logger.info(f"Transformed {df.count()} order items")
        return df
    
    def run_quality_checks(self, df: DataFrame, name: str) -> Dict[str, Any]:
        """Run data quality checks.
        
        Args:
            df: DataFrame to check
            name: Dataset name
            
        Returns:
            Quality check results
        """
        logger.info(f"Running quality checks for {name}")
        
        checker = DataQualityChecker(df, name)
        
        # Basic checks
        checker.check_row_count(min_rows=100)
        
        # Check for nulls in key columns
        if 'order_id' in df.columns:
            checker.check_null_percentage('order_id', max_null_percentage=0.0)
        if 'customer_id' in df.columns:
            checker.check_null_percentage('customer_id', max_null_percentage=0.0)
        
        results = checker.get_summary()
        
        if not results['all_passed']:
            logger.warning(f"Quality checks failed for {name}: {results}")
        else:
            logger.info(f"All quality checks passed for {name}")
        
        return results


def main():
    """Main ETL execution."""
    # Initialize Glue job
    args = getResolvedOptions(
        sys.argv,
        ['JOB_NAME', 'RAW_S3_PATH', 'PROCESSED_S3_PATH', 'INGESTION_DATE']
    )
    
    sc, glue_context, job, _ = initialize_glue_job(
        args['JOB_NAME'],
        ['RAW_S3_PATH', 'PROCESSED_S3_PATH', 'INGESTION_DATE']
    )
    
    # Create ETL instance
    etl = EcommerceETL(glue_context, sc)
    
    raw_path = args['RAW_S3_PATH']
    processed_path = args['PROCESSED_S3_PATH']
    ingestion_date = args['INGESTION_DATE']
    
    try:
        # Read raw data
        logger.info("=== Reading Raw Data ===")
        orders_raw = etl.read_raw_data(raw_path, "olist_orders_dataset.csv")
        customers_raw = etl.read_raw_data(raw_path, "olist_customers_dataset.csv")
        products_raw = etl.read_raw_data(raw_path, "olist_products_dataset.csv")
        sellers_raw = etl.read_raw_data(raw_path, "olist_sellers_dataset.csv")
        order_items_raw = etl.read_raw_data(raw_path, "olist_order_items_dataset.csv")
        categories_raw = etl.read_raw_data(raw_path, "product_category_name_translation.csv")
        
        # Transform data
        logger.info("=== Transforming Data ===")
        fact_orders = etl.transform_orders(orders_raw)
        dim_customers = etl.transform_customers(customers_raw)
        dim_products = etl.transform_products(products_raw, categories_raw)
        dim_sellers = etl.transform_sellers(sellers_raw)
        fact_order_items = etl.transform_order_items(
            order_items_raw, fact_orders, dim_products, dim_sellers
        )
        
        # Run quality checks
        logger.info("=== Running Quality Checks ===")
        etl.run_quality_checks(fact_orders, "fact_orders")
        etl.run_quality_checks(dim_customers, "dim_customers")
        etl.run_quality_checks(dim_products, "dim_products")
        etl.run_quality_checks(dim_sellers, "dim_sellers")
        etl.run_quality_checks(fact_order_items, "fact_order_items")
        
        # Write transformed data to S3
        logger.info("=== Writing Transformed Data ===")
        write_to_s3_parquet(
            fact_orders,
            f"{processed_path}/fact_orders/",
            partition_columns=['order_year', 'order_month'],
            mode='overwrite'
        )
        
        write_to_s3_parquet(
            dim_customers,
            f"{processed_path}/dim_customers/",
            mode='overwrite'
        )
        
        write_to_s3_parquet(
            dim_products,
            f"{processed_path}/dim_products/",
            mode='overwrite'
        )
        
        write_to_s3_parquet(
            dim_sellers,
            f"{processed_path}/dim_sellers/",
            mode='overwrite'
        )
        
        write_to_s3_parquet(
            fact_order_items,
            f"{processed_path}/fact_order_items/",
            partition_columns=['order_year', 'order_month'],
            mode='overwrite'
        )
        
        logger.info("=== ETL Job Completed Successfully ===")
        job.commit()
        
    except Exception as e:
        logger.error(f"ETL job failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
