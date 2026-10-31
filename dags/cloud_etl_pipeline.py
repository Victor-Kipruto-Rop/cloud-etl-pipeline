"""Airflow DAG that invokes the repository's canonical ETL entrypoint.

The Airflow worker image must include this repository and runtime dependencies.
Supply credentials through Airflow Connections or workload identity, not DAG code.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def execute_pipeline():
    from src.pipeline import run_pipeline

    result = run_pipeline()
    if result is False:
        raise RuntimeError("ETL pipeline returned an unsuccessful result")
    return {"status": "succeeded"}


with DAG(
    dag_id="cloud_etl_pipeline",
    description="Run the Cloud ETL pipeline with bounded retries",
    start_date=datetime(2025, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "data-engineering",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=30),
        "execution_timeout": timedelta(hours=2),
    },
    tags=["etl", "data-engineering", "cloud-etl"],
) as dag:
    run_etl = PythonOperator(
        task_id="run_etl",
        python_callable=execute_pipeline,
        do_xcom_push=False,
    )
