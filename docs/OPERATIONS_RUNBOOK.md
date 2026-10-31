# ETL Operations Runbook

## Before a run

1. Confirm the source file is expected and its origin is trusted.
2. Confirm the configured dataset contract and required columns.
3. Verify available disk space in the raw, processed, and log directories.
4. Confirm database and AWS credentials are supplied through the approved secret mechanism.
5. Confirm the target environment and bucket/prefix before enabling cloud upload.

## Run locally

Create and activate a virtual environment, install dependencies, and configure a local
.env file from .env.example. Then execute:

    python -m src.pipeline

For the optional AWS path, configure AWS_REGION and AWS_S3_BUCKET, then run:

    python -m src.cloud.aws_etl

Do not run the AWS path against production buckets until IAM, encryption, retention,
prefix isolation, and data handling policies have been reviewed.

## Failure response

### Validation or schema failure

- Preserve the original source file and inspect the validation message.
- Compare the incoming schema with the source contract.
- Do not weaken required-field or uniqueness checks merely to make a run pass.
- Correct the source or approve a versioned contract change, then replay the input.

### Local artifact write failure

- The atomic writer leaves the previous completed output in place.
- Check disk capacity, directory ownership, filesystem health, and permissions.
- Retry only after the underlying issue is corrected.
- Compare output modification time and source checksum before publishing downstream.

### Database load failure

- Stop downstream publication if the database is a required sink.
- Inspect connectivity, credentials, transaction rollback, and database capacity.
- Re-run only after confirming the sink's write semantics are idempotent.

### AWS upload or Redshift failure

- Check the active AWS identity and least-privilege policy.
- Verify bucket, region, object prefix, encryption, and Redshift IAM role configuration.
- Check whether the object upload completed before retrying the Redshift load.
- Reconcile source and target row counts before marking the run complete.

## Recovery and replay

- Keep the source artifact immutable and retain a checksum for the replay record.
- Use a unique run identifier and record source name, checksum, timestamps, row counts,
  output locations, and final status in the operational record.
- Reprocess through the normal validation and transformation path.
- Do not advance a production checkpoint until the required sink transaction commits.
- Quarantine invalid records with a reason and controlled replay path; do not silently drop
  them or repeatedly retry deterministic data errors.


## Incremental medallion mode

Enable MEDALLION_PIPELINE_ENABLED=true and configure MEDALLION_ROOT. The default
metadata URL in the example environment is local SQLite and is suitable only for
single-machine development. For shared or production execution, set
METADATA_DATABASE_URL to a managed PostgreSQL database with backups and restricted
network access.

When enabling a database sink, set DATABASE_URL, TARGET_SCHEMA, TARGET_TABLE and
UPSERT_KEY_COLUMNS. The target table and a matching unique constraint must exist
before the first run. Do not choose an arbitrary row number as a business key.

A successful source checksum is recorded in etl_checkpoints only after layer artifacts
and the configured database sink have committed. An unchanged source is skipped.
A changed source is processed as a new run. Failed runs do not advance checkpoints.

## Quarantine and replay

1. Query pending records in etl_quarantine and inspect reason_code / reason_message.
2. Correct the source data or transformation contract before replay.
3. Use restore_quarantined_file from src.reliability.replay to copy the original
   source into a controlled intake directory.
4. Re-run the ordinary pipeline path; do not write directly into warehouse tables.
5. After the run succeeds and the downstream sink is reconciled, call
   MetadataStore.mark_replayed(record_id).
6. Keep the original quarantine record and incident evidence according to retention
   policy. Do not automatically delete the original source.

## dbt and Airflow

- Install dbt separately with requirements-dbt.txt and validate the profile using
  dbt debug before running models against a warehouse.
- Confirm the raw.orders source table exists and matches dbt/models/staging/sources.yml.
- Deploy dags/cloud_etl_pipeline.py only after the Airflow worker image has the
  repository, dependencies, environment configuration and approved connections.
- Use Airflow task logs and etl_runs metadata together when investigating a failed run.

## AWS data lake

The standalone module at infra/aws/data_lake provisions an encrypted private bucket,
versioning, TLS-only access and prefix-scoped read/write permissions. Run Terraform
format, validate and plan in a controlled environment before any apply. Verify the
execution role already exists and review retention settings with the data owner.

## Incident closure

Record the impact, affected datasets, start/end time, root cause, recovery action, row-count
reconciliation, and follow-up prevention work. Update the production-readiness checklist
when an incident reveals a missing control.
