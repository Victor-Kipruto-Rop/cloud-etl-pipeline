"""
E-commerce Pipeline DAG for Apache Airflow (MWAA)

This DAG orchestrates the complete end-to-end data pipeline for e-commerce domain:
1. Ingest data from Kaggle to S3
2. Run AWS Glue ETL transformation
3. Run Glue crawler to update catalog
4. Load data into Redshift
5. Run data quality checks
6. Send notifications

Author: Cloud ETL Team
Schedule: Daily at 2 AM UTC
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.operators.glue_crawler import GlueCrawlerOperator
from airflow.providers.amazon.aws.operators.s3 import S3ListOperator
from airflow.providers.amazon.aws.operators.lambda_function import LambdaInvokeFunctionOperator
from airflow.providers.amazon.aws.sensors.glue import GlueJobSensor
from airflow.providers.amazon.aws.sensors.glue_crawler import GlueCrawlerSensor
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.amazon.aws.hooks.sns import SnsHook
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
import json
import logging

logger = logging.getLogger(__name__)

# DAG Default Arguments
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['data-team@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30),
    'execution_timeout': timedelta(hours=2),
}

# DAG Configuration
dag = DAG(
    dag_id='ecommerce_pipeline_dag',
    default_args=default_args,
    description='E-commerce data pipeline: Kaggle -> S3 -> Glue -> Redshift',
    schedule_interval='0 2 * * *',  # Daily at 2 AM UTC
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['ecommerce', 'etl', 'production'],
)


def send_sns_notification(context, status='SUCCESS'):
    """Send SNS notification on task completion or failure.
    
    Args:
        context: Airflow context dict
        status: Status string (SUCCESS or FAILURE)
    """
    sns_hook = SnsHook(aws_conn_id='aws_default')
    
    task_instance = context['task_instance']
    dag_id = context['dag'].dag_id
    execution_date = context['execution_date']
    
    subject = f"Airflow DAG {dag_id} - {status}"
    message = f"""
    DAG: {dag_id}
    Task: {task_instance.task_id}
    Execution Date: {execution_date}
    Status: {status}
    Log URL: {task_instance.log_url}
    """
    
    sns_hook.publish_to_target(
        target_arn='arn:aws:sns:us-east-1:123456789012:etl-pipeline-alerts',
        subject=subject,
        message=message
    )


def check_data_quality(**context):
    """Run data quality checks on processed data.
    
    Args:
        **context: Airflow context
        
    Returns:
        Dict with quality check results
    """
    from quality.validators.schema_validator import validate_schema
    from quality.validators.null_validator import check_nulls
    
    execution_date = context['execution_date'].strftime('%Y-%m-%d')
    s3_path = f"s3://cloud-etl-pipeline-data/processed/ecommerce/{execution_date}/"
    
    results = {
        'execution_date': execution_date,
        'checks_passed': 0,
        'checks_failed': 0,
        'details': []
    }
    
    # Schema validation
    schema_check = validate_schema('ecommerce', s3_path)
    if schema_check['passed']:
        results['checks_passed'] += 1
    else:
        results['checks_failed'] += 1
    results['details'].append(schema_check)
    
    # Null checks
    null_check = check_nulls('ecommerce', s3_path)
    if null_check['passed']:
        results['checks_passed'] += 1
    else:
        results['checks_failed'] += 1
    results['details'].append(null_check)
    
    logger.info(f"Quality checks: {results['checks_passed']} passed, {results['checks_failed']} failed")
    
    # Push results to XCom
    context['task_instance'].xcom_push(key='quality_results', value=results)
    
    # Fail if any check failed
    if results['checks_failed'] > 0:
        raise ValueError(f"{results['checks_failed']} quality checks failed")
    
    return results


def verify_s3_upload(**context):
    """Verify data was successfully uploaded to S3.
    
    Args:
        **context: Airflow context
        
    Returns:
        Dict with verification results
    """
    import boto3
    
    execution_date = context['execution_date'].strftime('%Y-%m-%d')
    bucket = 'cloud-etl-pipeline-data'
    prefix = f"raw/ecommerce/{execution_date}/"
    
    s3_client = boto3.client('s3')
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            raise ValueError(f"No files found in {bucket}/{prefix}")
        
        files = response['Contents']
        total_size = sum(obj['Size'] for obj in files)
        
        result = {
            'file_count': len(files),
            'total_size_mb': round(total_size / (1024**2), 2),
            'files': [obj['Key'] for obj in files]
        }
        
        logger.info(f"S3 verification passed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"S3 verification failed: {e}")
        raise


# Task 1: Start Pipeline
start = EmptyOperator(
    task_id='start_pipeline',
    dag=dag,
)

# Task 2: Ingest from Kaggle
with TaskGroup('ingest_from_kaggle', dag=dag) as ingest_group:
    
    # Invoke Lambda to trigger ingestion
    trigger_ingestion = LambdaInvokeFunctionOperator(
        task_id='trigger_kaggle_ingestion',
        function_name='etl-kaggle-ingestor',
        payload=json.dumps({
            'domain': 'ecommerce',
            'date': '{{ ds }}'
        }),
        aws_conn_id='aws_default',
    )
    
    # Verify S3 upload
    verify_upload = PythonOperator(
        task_id='verify_s3_upload',
        python_callable=verify_s3_upload,
        provide_context=True,
    )
    
    trigger_ingestion >> verify_upload

# Task 3: Run Glue ETL Job
run_glue_job = GlueJobOperator(
    task_id='run_glue_etl_job',
    job_name='ecommerce-transform-job',
    script_args={
        '--RAW_S3_PATH': 's3://cloud-etl-pipeline-data/raw/ecommerce/{{ ds }}/',
        '--PROCESSED_S3_PATH': 's3://cloud-etl-pipeline-data/processed/ecommerce/{{ ds }}/',
        '--INGESTION_DATE': '{{ ds }}'
    },
    aws_conn_id='aws_default',
    region_name='us-east-1',
    iam_role_name='AWSGlueServiceRole-etl',
    dag=dag,
)

# Task 4: Wait for Glue Job Completion
wait_for_glue_job = GlueJobSensor(
    task_id='wait_for_glue_job',
    job_name='ecommerce-transform-job',
    run_id='{{ task_instance.xcom_pull(task_ids="run_glue_etl_job")["JobRunId"] }}',
    aws_conn_id='aws_default',
    poke_interval=30,
    timeout=3600,
    mode='poke',
    dag=dag,
)

# Task 5: Run Glue Crawler
run_crawler = GlueCrawlerOperator(
    task_id='run_glue_crawler',
    crawler_name='ecommerce-crawler',
    aws_conn_id='aws_default',
    dag=dag,
)

# Task 6: Wait for Crawler Completion
wait_for_crawler = GlueCrawlerSensor(
    task_id='wait_for_crawler',
    crawler_name='ecommerce-crawler',
    aws_conn_id='aws_default',
    poke_interval=30,
    timeout=600,
    dag=dag,
)

# Task 7: Load to Redshift
with TaskGroup('load_to_redshift', dag=dag) as redshift_group:
    
    # Create temp staging table
    create_staging = PostgresOperator(
        task_id='create_staging_table',
        postgres_conn_id='redshift_default',
        sql="""
            CREATE TEMP TABLE staging_orders AS 
            SELECT * FROM fact_orders WHERE 1=0;
        """,
    )
    
    # Copy from S3 to staging
    copy_to_staging = PostgresOperator(
        task_id='copy_from_s3',
        postgres_conn_id='redshift_default',
        sql="""
            COPY staging_orders
            FROM 's3://cloud-etl-pipeline-data/processed/ecommerce/{{ ds }}/fact_orders/'
            IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftCopyRole'
            FORMAT AS PARQUET;
        """,
    )
    
    # Merge into fact table
    merge_to_fact = PostgresOperator(
        task_id='merge_to_fact_table',
        postgres_conn_id='redshift_default',
        sql="""
            BEGIN;
            
            DELETE FROM fact_orders
            WHERE order_id IN (SELECT order_id FROM staging_orders);
            
            INSERT INTO fact_orders
            SELECT * FROM staging_orders;
            
            COMMIT;
        """,
    )
    
    # Analyze table
    analyze_table = PostgresOperator(
        task_id='analyze_fact_table',
        postgres_conn_id='redshift_default',
        sql="ANALYZE fact_orders;",
    )
    
    create_staging >> copy_to_staging >> merge_to_fact >> analyze_table

# Task 8: Data Quality Checks
quality_checks = PythonOperator(
    task_id='run_data_quality_checks',
    python_callable=check_data_quality,
    provide_context=True,
    dag=dag,
)

# Task 9: Success Notification
success_notification = PythonOperator(
    task_id='send_success_notification',
    python_callable=lambda **context: send_sns_notification(context, 'SUCCESS'),
    provide_context=True,
    trigger_rule='all_success',
    dag=dag,
)

# Task 10: End Pipeline
end = EmptyOperator(
    task_id='end_pipeline',
    trigger_rule='all_done',
    dag=dag,
)

# Set up failure callback
def on_failure_callback(context):
    """Callback function for task failures."""
    send_sns_notification(context, 'FAILURE')

# Apply failure callback to all tasks
for task in dag.tasks:
    task.on_failure_callback = on_failure_callback

# Define task dependencies
(
    start 
    >> ingest_group 
    >> run_glue_job 
    >> wait_for_glue_job 
    >> run_crawler 
    >> wait_for_crawler 
    >> redshift_group 
    >> quality_checks 
    >> success_notification 
    >> end
)
