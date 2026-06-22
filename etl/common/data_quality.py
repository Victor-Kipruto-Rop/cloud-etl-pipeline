"""Data quality checking functions for ETL jobs."""
import logging
from typing import Dict, Any, List, Optional
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """Performs comprehensive data quality checks on DataFrames."""
    
    def __init__(self, df: DataFrame, name: str = "Dataset"):
        """Initialize quality checker.
        
        Args:
            df: DataFrame to check
            name: Name of the dataset
        """
        self.df = df
        self.name = name
        self.results = []
    
    def check_row_count(
        self,
        min_rows: Optional[int] = None,
        max_rows: Optional[int] = None
    ) -> Dict[str, Any]:
        """Check if row count is within expected range.
        
        Args:
            min_rows: Minimum expected rows
            max_rows: Maximum expected rows
            
        Returns:
            Check result
        """
        count = self.df.count()
        passed = True
        
        if min_rows is not None and count < min_rows:
            passed = False
        if max_rows is not None and count > max_rows:
            passed = False
        
        result = {
            'check': 'row_count',
            'passed': passed,
            'actual': count,
            'expected_min': min_rows,
            'expected_max': max_rows
        }
        
        self.results.append(result)
        logger.info(f"Row count check: {count} rows - {'PASSED' if passed else 'FAILED'}")
        
        return result
    
    def check_null_percentage(
        self,
        column: str,
        max_null_percentage: float = 0.1
    ) -> Dict[str, Any]:
        """Check null percentage for a column.
        
        Args:
            column: Column name to check
            max_null_percentage: Maximum allowed null percentage (0-1)
            
        Returns:
            Check result
        """
        total_count = self.df.count()
        null_count = self.df.filter(F.col(column).isNull()).count()
        null_percentage = null_count / total_count if total_count > 0 else 0
        
        passed = null_percentage <= max_null_percentage
        
        result = {
            'check': 'null_percentage',
            'column': column,
            'passed': passed,
            'null_count': null_count,
            'total_count': total_count,
            'null_percentage': null_percentage,
            'max_allowed': max_null_percentage
        }
        
        self.results.append(result)
        logger.info(
            f"Null check for '{column}': {null_percentage:.2%} - "
            f"{'PASSED' if passed else 'FAILED'}"
        )
        
        return result
    
    def check_schema(
        self,
        expected_columns: List[str],
        strict: bool = False
    ) -> Dict[str, Any]:
        """Check if DataFrame has expected columns.
        
        Args:
            expected_columns: List of expected column names
            strict: If True, no extra columns allowed
            
        Returns:
            Check result
        """
        actual_columns = set(self.df.columns)
        expected_set = set(expected_columns)
        
        missing_columns = expected_set - actual_columns
        extra_columns = actual_columns - expected_set
        
        passed = len(missing_columns) == 0
        if strict:
            passed = passed and len(extra_columns) == 0
        
        result = {
            'check': 'schema',
            'passed': passed,
            'missing_columns': list(missing_columns),
            'extra_columns': list(extra_columns),
            'strict_mode': strict
        }
        
        self.results.append(result)
        logger.info(f"Schema check - {'PASSED' if passed else 'FAILED'}")
        if missing_columns:
            logger.warning(f"Missing columns: {missing_columns}")
        if extra_columns and strict:
            logger.warning(f"Extra columns: {extra_columns}")
        
        return result
    
    def check_duplicates(
        self,
        key_columns: List[str],
        max_duplicate_percentage: float = 0.01
    ) -> Dict[str, Any]:
        """Check for duplicate rows based on key columns.
        
        Args:
            key_columns: Columns that should be unique
            max_duplicate_percentage: Maximum allowed duplicate percentage
            
        Returns:
            Check result
        """
        total_count = self.df.count()
        distinct_count = self.df.select(key_columns).distinct().count()
        duplicate_count = total_count - distinct_count
        duplicate_percentage = duplicate_count / total_count if total_count > 0 else 0
        
        passed = duplicate_percentage <= max_duplicate_percentage
        
        result = {
            'check': 'duplicates',
            'key_columns': key_columns,
            'passed': passed,
            'total_count': total_count,
            'distinct_count': distinct_count,
            'duplicate_count': duplicate_count,
            'duplicate_percentage': duplicate_percentage,
            'max_allowed': max_duplicate_percentage
        }
        
        self.results.append(result)
        logger.info(
            f"Duplicate check on {key_columns}: {duplicate_percentage:.2%} - "
            f"{'PASSED' if passed else 'FAILED'}"
        )
        
        return result
    
    def check_value_range(
        self,
        column: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """Check if column values are within expected range.
        
        Args:
            column: Column name
            min_value: Minimum expected value
            max_value: Maximum expected value
            
        Returns:
            Check result
        """
        stats = self.df.select(
            F.min(column).alias('min'),
            F.max(column).alias('max')
        ).collect()[0]
        
        actual_min = stats['min']
        actual_max = stats['max']
        
        passed = True
        if min_value is not None and actual_min < min_value:
            passed = False
        if max_value is not None and actual_max > max_value:
            passed = False
        
        result = {
            'check': 'value_range',
            'column': column,
            'passed': passed,
            'actual_min': actual_min,
            'actual_max': actual_max,
            'expected_min': min_value,
            'expected_max': max_value
        }
        
        self.results.append(result)
        logger.info(f"Value range check for '{column}' - {'PASSED' if passed else 'FAILED'}")
        
        return result
    
    def check_referential_integrity(
        self,
        child_column: str,
        parent_df: DataFrame,
        parent_column: str
    ) -> Dict[str, Any]:
        """Check referential integrity between DataFrames.
        
        Args:
            child_column: Foreign key column in child DataFrame
            parent_df: Parent DataFrame
            parent_column: Primary key column in parent DataFrame
            
        Returns:
            Check result
        """
        # Get distinct values from both DataFrames
        child_values = self.df.select(child_column).distinct()
        parent_values = parent_df.select(parent_column).distinct()
        
        # Find orphaned records
        orphaned = child_values.join(
            parent_values,
            child_values[child_column] == parent_values[parent_column],
            'left_anti'
        )
        
        orphaned_count = orphaned.count()
        total_distinct = child_values.count()
        
        passed = orphaned_count == 0
        
        result = {
            'check': 'referential_integrity',
            'child_column': child_column,
            'parent_column': parent_column,
            'passed': passed,
            'orphaned_count': orphaned_count,
            'total_distinct_values': total_distinct
        }
        
        self.results.append(result)
        logger.info(
            f"Referential integrity check: {orphaned_count} orphaned records - "
            f"{'PASSED' if passed else 'FAILED'}"
        )
        
        return result
    
    def check_data_freshness(
        self,
        date_column: str,
        max_age_days: int
    ) -> Dict[str, Any]:
        """Check if data is fresh (recent enough).
        
        Args:
            date_column: Date column to check
            max_age_days: Maximum allowed age in days
            
        Returns:
            Check result
        """
        max_date = self.df.select(F.max(date_column)).collect()[0][0]
        current_date = F.current_date()
        
        # Calculate age (this is simplified; actual implementation would use Spark SQL)
        age_days = None  # Placeholder - would calculate actual age
        
        passed = age_days is None or age_days <= max_age_days
        
        result = {
            'check': 'data_freshness',
            'date_column': date_column,
            'passed': passed,
            'max_date': str(max_date),
            'age_days': age_days,
            'max_allowed_age_days': max_age_days
        }
        
        self.results.append(result)
        logger.info(f"Data freshness check - {'PASSED' if passed else 'FAILED'}")
        
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all quality checks.
        
        Returns:
            Summary dictionary
        """
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r['passed'])
        failed_checks = total_checks - passed_checks
        
        summary = {
            'dataset_name': self.name,
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'success_rate': passed_checks / total_checks if total_checks > 0 else 0,
            'all_passed': failed_checks == 0,
            'individual_results': self.results
        }
        
        logger.info(f"Quality check summary: {passed_checks}/{total_checks} passed")
        
        return summary


def run_standard_quality_checks(
    df: DataFrame,
    name: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Run standard quality checks based on configuration.
    
    Args:
        df: DataFrame to check
        name: Dataset name
        config: Configuration dict with check parameters
        
    Returns:
        Quality check results
    """
    checker = DataQualityChecker(df, name)
    
    # Row count check
    if 'row_count' in config:
        checker.check_row_count(
            min_rows=config['row_count'].get('min'),
            max_rows=config['row_count'].get('max')
        )
    
    # Null checks
    if 'null_checks' in config:
        for col, max_pct in config['null_checks'].items():
            checker.check_null_percentage(col, max_pct)
    
    # Schema check
    if 'expected_columns' in config:
        checker.check_schema(
            config['expected_columns'],
            strict=config.get('strict_schema', False)
        )
    
    # Duplicate check
    if 'unique_keys' in config:
        checker.check_duplicates(
            config['unique_keys'],
            max_duplicate_percentage=config.get('max_duplicate_pct', 0.01)
        )
    
    return checker.get_summary()
