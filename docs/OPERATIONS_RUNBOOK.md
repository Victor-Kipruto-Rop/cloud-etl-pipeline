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

## Incident closure

Record the impact, affected datasets, start/end time, root cause, recovery action, row-count
reconciliation, and follow-up prevention work. Update the production-readiness checklist
when an incident reveals a missing control.
