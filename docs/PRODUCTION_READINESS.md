# Production Readiness and Release Gates

This repository is an extensible ETL engineering project. The presence of AWS,
Terraform, Airflow, Kubernetes, monitoring, or deployment examples does not by
itself mean those components are deployed or production-validated.

## Implemented in this repository

- Python CSV ingestion, transformation, validation, and PostgreSQL loading paths.
- Optional Kaggle ingestion and AWS S3 / Redshift helper integrations.
- Unit and integration-oriented tests, Docker packaging, and GitHub Actions CI.
- Data-quality contracts for required columns, null ratios, uniqueness, row counts,
  and allowed values.
- Atomic local CSV / Parquet artifact publication. A failed write does not replace
  a previously published local output file.

## Required before a production launch

### Data correctness
- Define source-specific contracts and stable business keys.
- Use idempotent upserts or merge semantics for every production sink.
- Persist ingestion checkpoints only after durable writes commit.
- Define late-arriving data, replay, backfill, and schema-evolution policies.
- Route invalid records to a durable quarantine with reason codes and controlled replay.
- Compare source, landed, transformed, and published row counts.

### Security and governance
- Use IAM roles / workload identity instead of long-lived AWS access keys where possible.
- Store credentials in a secret manager; never place secrets in images, logs, workflow
  output, or committed environment files.
- Restrict S3 bucket access, enable encryption, block public access, and define lifecycle
  and retention policies.
- Use TLS for database connections and least-privilege database roles.
- Classify sensitive fields, define retention, and redact personal data from logs.
- Pin and review dependencies; generate an SBOM and scan dependencies and container images.

### Reliability and operations
- Set explicit connection, task, and API timeouts.
- Retry only transient failures with capped exponential backoff and jitter.
- Make tasks safe to rerun and define a maximum retry / dead-letter policy.
- Record run IDs, source object versions, checksums, row counts, duration, and outcomes.
- Alert on freshness, failure rate, volume anomalies, quality failures, and DLQ growth.
- Document restore procedures and prove backup restoration in a non-production environment.

### Deployment controls
- Validate Terraform and review plans before apply.
- Use separate AWS accounts or isolated roles for dev, staging, and production.
- Require protected environments and human approval for production.
- Promote the same immutable artifact between environments.
- Run integration and smoke tests after deployment; define a tested rollback procedure.
- Do not claim canary deployment or automatic rollback until traffic shifting and rollback
  are implemented and exercised in the target runtime.

## Release checklist

- [ ] Source contracts and primary keys reviewed
- [ ] Idempotent sink behaviour tested under retries and reruns
- [ ] Data-quality and reconciliation thresholds agreed
- [ ] Quarantine and replay procedures tested
- [ ] Secrets and IAM permissions reviewed
- [ ] S3 encryption, access, lifecycle, and retention verified
- [ ] Database migrations and rollback plan reviewed
- [ ] CI, integration tests, and container build pass
- [ ] Terraform plan reviewed and approved
- [ ] Monitoring, alert routing, and runbooks verified
- [ ] Backup restore and disaster recovery exercise completed
- [ ] Staging soak test completed and production approval recorded

A release is production-ready only when the applicable controls above are implemented,
configured in the target environment, and evidenced by successful tests or operational
records. A green unit-test run alone is not a production certification.
