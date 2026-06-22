# Project Structure

This repository is organized for a Python-based ETL pipeline with Kaggle ingestion, local processing, and auxiliary AWS helper support.

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
├── dags/
│   └── ecommerce_pipeline_dag.py
├── k8s/
│   └── etl-job.yaml
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
│   ├── test_api_module.py
│   ├── test_benchmark.py
│   ├── test_dashboard.py
│   ├── test_data_validation.py
│   ├── test_further_coverage.py
│   ├── test_kaggle_integration.py
│   ├── test_load_module.py
│   ├── test_logging.py
│   ├── test_perf_copy.py
│   ├── test_pipeline.py
│   └── test_validation.py
├── terraform/
│   ├── main.tf
│   ├── outputs.tf
│   └── variables.tf
└── infra/
    └── aws/
        └── provider.tf
```

## Notes

- The `terraform/` folder contains a root AWS backend and provider configuration.
- The repository is primarily structured for local development and testing.
