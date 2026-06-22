"""Common transformation functions for ETL jobs."""
import logging
from typing import List, Optional, Dict, Any
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import *

logger = logging.getLogger(__name__)


def handle_nulls(
    df: DataFrame,
    strategies: Dict[str, Any]
) -> DataFrame:
    """Handle null values based on column-specific strategies.
    
    Args:
        df: Input DataFrame
        strategies: Dict mapping column names to replacement strategies
                   e.g., {'col1': 'drop', 'col2': 0, 'col3': 'unknown'}
        
    Returns:
        DataFrame with nulls handled
    """
    for col, strategy in strategies.items():
        if col not in df.columns:
            logger.warning(f"Column '{col}' not found in DataFrame")
            continue
        
        if strategy == 'drop':
            df = df.filter(F.col(col).isNotNull())
        elif isinstance(strategy, (int, float, str)):
            df = df.fillna({col: strategy})
        else:
            logger.warning(f"Unknown strategy '{strategy}' for column '{col}'")
    
    return df


def cast_columns(
    df: DataFrame,
    schema_mapping: Dict[str, str]
) -> DataFrame:
    """Cast columns to specified data types.
    
    Args:
        df: Input DataFrame
        schema_mapping: Dict mapping column names to target types
                       e.g., {'price': 'double', 'quantity': 'integer'}
        
    Returns:
        DataFrame with casted columns
    """
    type_mapping = {
        'string': StringType(),
        'integer': IntegerType(),
        'long': LongType(),
        'double': DoubleType(),
        'float': FloatType(),
        'boolean': BooleanType(),
        'date': DateType(),
        'timestamp': TimestampType()
    }
    
    for col, target_type in schema_mapping.items():
        if col not in df.columns:
            logger.warning(f"Column '{col}' not found in DataFrame")
            continue
        
        if target_type.lower() in type_mapping:
            df = df.withColumn(col, F.col(col).cast(type_mapping[target_type.lower()]))
            logger.info(f"Cast column '{col}' to {target_type}")
        else:
            logger.warning(f"Unknown type '{target_type}' for column '{col}'")
    
    return df


def add_date_partitions(
    df: DataFrame,
    date_column: str,
    include_year: bool = True,
    include_month: bool = True,
    include_day: bool = False,
    include_quarter: bool = False
) -> DataFrame:
    """Add date partition columns from a date column.
    
    Args:
        df: Input DataFrame
        date_column: Source date column
        include_year: Add year partition
        include_month: Add month partition
        include_day: Add day partition
        include_quarter: Add quarter partition
        
    Returns:
        DataFrame with partition columns
    """
    if date_column not in df.columns:
        raise ValueError(f"Date column '{date_column}' not found")
    
    # Ensure date column is timestamp
    df = df.withColumn(date_column, F.col(date_column).cast(TimestampType()))
    
    if include_year:
        df = df.withColumn(f"{date_column}_year", F.year(date_column))
    
    if include_month:
        df = df.withColumn(f"{date_column}_month", F.month(date_column))
    
    if include_day:
        df = df.withColumn(f"{date_column}_day", F.dayofmonth(date_column))
    
    if include_quarter:
        df = df.withColumn(f"{date_column}_quarter", F.quarter(date_column))
    
    logger.info(f"Added date partitions from '{date_column}'")
    return df


def create_surrogate_key(
    df: DataFrame,
    key_columns: List[str],
    key_name: str = "surrogate_key"
) -> DataFrame:
    """Create a surrogate key from multiple columns.
    
    Args:
        df: Input DataFrame
        key_columns: Columns to hash for surrogate key
        key_name: Name of the new key column
        
    Returns:
        DataFrame with surrogate key
    """
    # Concatenate columns and hash
    concat_expr = F.concat_ws("_", *[F.col(c) for c in key_columns])
    df = df.withColumn(key_name, F.md5(concat_expr))
    
    logger.info(f"Created surrogate key '{key_name}' from {key_columns}")
    return df


def standardize_addresses(
    df: DataFrame,
    address_columns: List[str]
) -> DataFrame:
    """Standardize address fields.
    
    Args:
        df: Input DataFrame
        address_columns: List of address column names
        
    Returns:
        DataFrame with standardized addresses
    """
    for col in address_columns:
        if col in df.columns:
            # Trim whitespace, uppercase
            df = df.withColumn(col, F.trim(F.upper(F.col(col))))
    
    return df


def calculate_age_group(
    df: DataFrame,
    age_column: str,
    group_column: str = "age_group"
) -> DataFrame:
    """Calculate age group from age column.
    
    Args:
        df: Input DataFrame
        age_column: Source age column
        group_column: Target age group column name
        
    Returns:
        DataFrame with age groups
    """
    df = df.withColumn(
        group_column,
        F.when(F.col(age_column) < 18, "Under 18")
        .when((F.col(age_column) >= 18) & (F.col(age_column) < 30), "18-29")
        .when((F.col(age_column) >= 30) & (F.col(age_column) < 40), "30-39")
        .when((F.col(age_column) >= 40) & (F.col(age_column) < 50), "40-49")
        .when((F.col(age_column) >= 50) & (F.col(age_column) < 60), "50-59")
        .when((F.col(age_column) >= 60) & (F.col(age_column) < 70), "60-69")
        .otherwise("70+")
    )
    
    return df


def extract_domain_from_email(
    df: DataFrame,
    email_column: str,
    domain_column: str = "email_domain"
) -> DataFrame:
    """Extract domain from email address.
    
    Args:
        df: Input DataFrame
        email_column: Source email column
        domain_column: Target domain column name
        
    Returns:
        DataFrame with email domains
    """
    df = df.withColumn(
        domain_column,
        F.regexp_extract(F.col(email_column), r'@(.+)$', 1)
    )
    
    return df


def calculate_price_tier(
    df: DataFrame,
    price_column: str,
    tier_column: str = "price_tier",
    thresholds: Optional[List[float]] = None
) -> DataFrame:
    """Calculate price tiers.
    
    Args:
        df: Input DataFrame
        price_column: Source price column
        tier_column: Target tier column name
        thresholds: Price thresholds [low, medium, high]
        
    Returns:
        DataFrame with price tiers
    """
    if thresholds is None:
        # Calculate percentiles
        quantiles = df.approxQuantile(price_column, [0.33, 0.67], 0.01)
        thresholds = quantiles
    
    df = df.withColumn(
        tier_column,
        F.when(F.col(price_column) < thresholds[0], "Low")
        .when((F.col(price_column) >= thresholds[0]) & (F.col(price_column) < thresholds[1]), "Medium")
        .otherwise("High")
    )
    
    logger.info(f"Created price tiers with thresholds: {thresholds}")
    return df


def explode_json_column(
    df: DataFrame,
    json_column: str,
    schema: Optional[StructType] = None
) -> DataFrame:
    """Parse and explode JSON column.
    
    Args:
        df: Input DataFrame
        json_column: JSON column name
        schema: Optional schema for JSON parsing
        
    Returns:
        DataFrame with exploded JSON
    """
    if schema:
        df = df.withColumn(json_column, F.from_json(F.col(json_column), schema))
    else:
        # Infer schema
        df = df.withColumn(json_column, F.from_json(F.col(json_column), "map<string, string>"))
    
    # Explode into separate columns
    df = df.select("*", F.col(json_column).alias("parsed_json"))
    
    return df


def aggregate_to_daily(
    df: DataFrame,
    date_column: str,
    group_columns: List[str],
    agg_columns: Dict[str, List[str]]
) -> DataFrame:
    """Aggregate data to daily granularity.
    
    Args:
        df: Input DataFrame
        date_column: Date column for grouping
        group_columns: Additional grouping columns
        agg_columns: Dict mapping agg functions to column lists
                    e.g., {'sum': ['amount', 'quantity'], 'avg': ['price']}
        
    Returns:
        Aggregated DataFrame
    """
    # Convert to date
    df = df.withColumn(f"{date_column}_date", F.to_date(date_column))
    
    # Build aggregation expressions
    agg_exprs = []
    for agg_func, cols in agg_columns.items():
        for col in cols:
            if agg_func == 'sum':
                agg_exprs.append(F.sum(col).alias(f"{col}_sum"))
            elif agg_func == 'avg':
                agg_exprs.append(F.avg(col).alias(f"{col}_avg"))
            elif agg_func == 'count':
                agg_exprs.append(F.count(col).alias(f"{col}_count"))
            elif agg_func == 'min':
                agg_exprs.append(F.min(col).alias(f"{col}_min"))
            elif agg_func == 'max':
                agg_exprs.append(F.max(col).alias(f"{col}_max"))
    
    # Group and aggregate
    result = df.groupBy([f"{date_column}_date"] + group_columns).agg(*agg_exprs)
    
    return result
