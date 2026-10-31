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
- Declarative data-quality contracts and a pytest-based test suite in `tests/`
- Atomic CSV / Parquet artifact writes that preserve the last successful output if a write fails
- Container hardening with a non-root runtime user and a Docker build-context ignore policy

> Note: `terraform/` contains a Terraform root configuration and AWS provider file, but the referenced Terraform module sources are not included in this repository. The supported workflow is local development with optional AWS helper support.

## Engineering status

- The local Python ETL path supports CSV extraction, transformation, validation, PostgreSQL loading, and operational metrics.
- AWS helpers support S3 artifact upload and optional Redshift COPY integration when correctly configured.
- CSV and Parquet outputs are published atomically on the local filesystem. A failed write does not replace the previous completed artifact.
- Docker now runs the ETL process as a non-root user and excludes local datasets, logs, and credentials from the build context.
- `dags/`, `k8s/`, and parts of `terraform/` are deployment examples or scaffolds. They must be validated and completed in the target AWS account before use.
- This repository is not certified production-ready. Review [Production Readiness](docs/PRODUCTION_READINESS.md) for the controls and evidence required before a production launch.
- Never commit `.env`, Kaggle credentials, cloud credentials, or customer datasets.

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

## Reliability and operational controls

- Atomic local artifact publication for CSV and Parquet outputs
- Data-quality contracts for required fields, null thresholds, uniqueness, minimum row counts, and allowed values
- CI compilation checks and targeted regression tests for output-write failure handling
- Non-root Docker runtime and build-context exclusions for local data and secrets
- Explicit production-readiness gates covering idempotency, replay, quarantine, IAM, monitoring, backup restoration, and release approvals

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

## Release and deployment policy

This repository expects protected GitHub environments for `dev`, `staging`, and `production`.

Production policy:
- `main` is protected and requires successful CI before merge or deploy
- `staging` requires reviewer approval before promotion
- `production` requires the dedicated approval gate in `.github/workflows/production-approval-gate.yml`
- Production deploys require a health/smoke check and environment approval before applying changes
- Database migrations and Terraform changes must be reviewed and approved before production execution
- The staged rollout workflow defines the release path: `dev` -> `staging` -> `production`
- Production follows a canary rollout and must automatically roll back on failed smoke checks or unhealthy endpoints

## Operational scripts

The repo includes deployment support scripts for production safety:
- `scripts/health_check.sh` checks environment health endpoints
- `scripts/rollback_production.sh` triggers a rollback flow for a previous known-good version
- `.env.dev.example`, `.env.staging.example`, and `.env.production.example` provide environment-specific secret templates

## Monitoring, SLOs, and operational safety

The repository includes Prometheus alert rules for production operations and an example Grafana dashboard. Recommended signal coverage includes:
- pipeline latency alerts for p95 and p99 execution time
- data freshness checks to ensure downstream datasets are refreshed within SLA windows
- warehouse row-count drift checks to detect silent data loss or unexpected source behavior
- dead-letter queue and failed-job thresholds that escalate when operational failures increase
- canary and deployment markers so release changes are visible in Grafana annotations

### Recommended SLO targets

- data freshness: 99% of downstream datasets refreshed within 1 hour
- ETL success rate: 99.5% or better for scheduled jobs
- pipeline latency: p95 under 5 minutes for standard batch runs
- failed job tolerance: fewer than 5 failed jobs in a 15-minute window before alerting

### Grafana deployment annotations

Grafana annotations should be configured for both deploys and rollbacks so each deploy or incident is visible alongside time series data. Typical annotation sources include:
- CI/CD workflow events from GitHub Actions or ArgoCD-style deployment metadata
- manual rollback actions recorded in the runbook or event stream
- environment-level release markers annotated with the image tag and approver

This supports fast correlation between a deploy, a rollback, and the resulting latency, failure, or data freshness signals.

## Production readiness

Read [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md) before using this project for unattended workloads. The checklist separates implemented repository features from infrastructure and operational controls that still require deployment-specific implementation and evidence.

## Notes

- `data/raw/` and `data/processed/` are local working directories.
- `terraform/` and `infra/aws/` provide AWS configuration skeletons, but the repository is not a complete, runnable cloud deployment package on its own.
- Use the local pipeline path for development and testing.
