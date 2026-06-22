# ETL Pipeline

[![CI](https://github.com/Victor-Kipruto-Rop/cloud-etl-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Victor-Kipruto-Rop/cloud-etl-pipeline/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A Python ETL repository that ingests Kaggle datasets, runs local extract/transform/load workflows, and optionally uploads raw and processed data to AWS S3.

## What this project contains

- Local Kaggle ingestion scripts for e-commerce, healthcare, finance, sports, and climate domains under `ingest/`
- A modular ETL pipeline under `src/` and `etl/`
- Root environment configuration templates in `.env.example` and reusable settings under `config/`
- AWS helper code for S3 upload and optional Redshift load under `src/cloud/`
- E-commerce analytics SQL in `analytics/ecommerce_queries.sql`
- Warehouse schema DDL in `warehouse/schemas/*.sql`
- Monitoring examples in `monitoring/`
- A pytest-based test suite in `tests/`

> Note: `terraform/` contains a Terraform root configuration and AWS provider file, but the referenced Terraform module sources are not included in this repository. The supported workflow is local development with optional AWS helper support.

## Status

- Local ETL and data ingestion are implemented in Python.
- AWS S3 upload and optional Redshift helper methods exist, but full multi-service cloud provisioning is not available in this checkout.
- `dags/` and `k8s/` provide deployment skeletons rather than a complete cloud production stack.
- `.env` is a local configuration file that should not be committed.
- Data directories under `data/` are excluded from version control and should be created locally.
- This repository is best used for local pipeline development, testing, and Kaggle ingestion.

## Quick Start

### Prerequisites

- Python 3.10+
- Git
- `pip`
- Kaggle account + API credentials
- Optional: AWS CLI and AWS credentials for S3 upload

### Local setup

```bash
git clone https://github.com/Victor-Kipruto-Rop/cloud-etl-pipeline.git
cd cloud-etl-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p data/raw data/processed data/analytics
```

### Run the local pipeline

```bash
python -m ingest.kaggle_ingest --domain ecommerce
```

The `ingest/kaggle_ingest.py` script downloads Kaggle dataset files into `data/raw/` and can optionally trigger local processing workflows.

### Run the AWS helper locally

```bash
AWS_S3_BUCKET=your-bucket \
AWS_REGION=us-west-1 \
KAGGLE_DATASET=olistbr/brazilian-ecommerce \
KAGGLE_DOWNLOAD=true \
KAGGLE_FORCE_DOWNLOAD=true \
.venv/bin/python3 -m src.cloud.aws_etl
```

This command downloads the specified Kaggle dataset, processes CSV files, writes Parquet outputs to `data/processed/`, uploads raw CSV files to S3, and optionally uploads processed Parquet files.

### Run tests

```bash
.venv/bin/python3 -m pytest -q
```

## Supported workflows

- `ingest/`: dataset download and ingestion orchestration
- `src/pipeline.py`: local ETL orchestration
- `src/extract/`, `src/transform/`, `src/load/`: pipeline stages
- `src/cloud/aws_etl.py`: AWS helper orchestration
- `src/cloud/aws_s3.py`: S3 upload utilities
- `src/cloud/aws_redshift.py`: Redshift load helper
- `dags/`: Airflow DAG skeleton for ecommerce ETL orchestration
- `k8s/`: Kubernetes ETL job manifest skeleton

## Project structure

```
cloud-etl-pipeline/
├── README.md
├── ARCHITECTURE.md
├── DEPLOYMENT.md
├── IMPLEMENTATION_SUMMARY.md
├── RELEASE_NOTES.md
├── CREDIBILITY_AUDIT_FIXES.md
├── TROUBLESHOOTING.md
├── PROJECT_STRUCTURE.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── config/
│   ├── aws_config.yaml
│   └── domains.yaml
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── lint.yml
│       ├── python-app.yml
│       ├── run_pipeline.yml
│       ├── deploy_glue.yml
│       └── deploy_terraform.yml
├── ingest/
│   ├── kaggle_ingest.py
│   ├── ecommerce_ingest.py
│   ├── healthcare_ingest.py
│   ├── finance_ingest.py
│   ├── sports_ingest.py
│   ├── climate_ingest.py
│   └── config.py
├── src/
│   ├── api.py
│   ├── config.py
│   ├── dashboard.py
│   ├── health.py
│   ├── logging_config.py
│   ├── migrations.py
│   ├── pipeline.py
│   ├── validation.py
│   └── cloud/
│       ├── aws_etl.py
│       ├── aws_redshift.py
│       ├── aws_s3.py
│       └── __init__.py
├── etl/
│   ├── __init__.py
│   └── ecommerce_transform.py
├── analytics/
│   └── ecommerce_queries.sql
├── warehouse/
│   └── schemas/
│       ├── ecommerce.sql
│       ├── healthcare.sql
│       ├── finance.sql
│       ├── sports.sql
│       └── climate.sql
├── monitoring/
│   ├── alert_rules.yml
│   ├── docker-compose.monitoring.yml
│   ├── grafana-dashboard.json
│   ├── playbook.md
│   ├── prometheus.yml
│   └── README.md
├── diagrams/
│   └── system_diagrams.md
├── data/
│   ├── raw/
│   ├── processed/
│   └── analytics/
├── tests/
├── terraform/
│   ├── main.tf
│   ├── outputs.tf
│   └── variables.tf
└── infra/
    └── aws/
        └── provider.tf
```

## Notes

- `data/raw/` and `data/processed/` are local working directories.
- `terraform/` and `infra/aws/` provide AWS configuration skeletons, but the repository is not a complete, runnable cloud deployment package on its own.
- Use the local pipeline path for development and testing.
