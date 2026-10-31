# Secure S3 Data Lake Module

This standalone Terraform module provisions a private, versioned S3 data bucket,
default server-side encryption, a TLS-only bucket policy, lifecycle controls and a
least-privilege IAM policy scoped to ETL layer prefixes.

## Usage

```hcl
module "etl_data_lake" {
  source              = "./infra/aws/data_lake"
  bucket_name         = "replace-with-a-globally-unique-name"
  environment         = "dev"
  execution_role_name = "existing-etl-workload-role"
}
```

The execution role must already exist. The module attaches a scoped policy when
execution_role_name is non-empty; it does not create a trust relationship or
credentials. Prefer IAM roles / workload identity over long-lived access keys.

## Security controls

- All S3 public-access-block settings are enabled.
- Bucket ownership is enforced; ACL-based public access is not used.
- Objects use SSE-S3 by default.
- Bucket policy denies requests over insecure transport.
- Versioning is enabled.
- Bronze retention and noncurrent-version retention are configurable.
- IAM permissions are restricted to bronze/silver/gold/quarantine prefixes.
- No bucket deletion or object deletion permissions are granted.

## Apply safely

Run terraform init, terraform fmt -check, terraform validate, and terraform plan
from this module directory. Review the plan and account-specific IAM impact before
applying. This module has not been applied to an AWS account as part of this change.

For production, review retention requirements with the data owner and compliance
stakeholders before setting an expiration policy. Quarantine data is not automatically
expired by this module.
