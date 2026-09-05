Terraform usage and environment backends

This folder contains Terraform configuration for the Cloud ETL Pipeline.

Environment-specific backends

Example backend files are provided in `terraform/backends/` for `dev`, `staging`, and `prod`. They contain placeholders for `<AWS_ACCOUNT_ID>` — replace these with your real account IDs before use, or provide equivalent values via `-backend-config`.

Quick start (local):

```bash
# prepare backend
cp terraform/backends/backend.dev.hcl terraform/backend.hcl
# edit terraform/backend.hcl to replace <AWS_ACCOUNT_ID>
# initialize and select workspace
./terraform/init_workspace.sh dev
# plan/apply
terraform plan
terraform apply
```

Drift detection

Run the provided drift detection script which calls `terraform plan -detailed-exitcode` and verifies S3/DynamoDB locking resources:

```bash
./terraform/drift_check.sh dev
```

GitHub Actions

A scheduled workflow `.github/workflows/terraform-drift-detection.yml` runs drift checks daily. Configure `AWS_ROLE_TO_ASSUME` secret or other AWS credentials in repository secrets before enabling.

State locking and backups

- Ensure your S3 bucket used for Terraform state has versioning enabled.
- Ensure a DynamoDB table exists per environment (named in the backend files) to support state locking.
- Periodically verify S3 state object history and export copies for long-term backups if required.
