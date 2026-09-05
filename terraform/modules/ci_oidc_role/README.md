# CI OIDC Role module

This Terraform module creates two IAM roles for GitHub Actions OIDC-based access:

- `tf_runner` — least-privilege role used by CI to read/write Terraform state and lock/unlock DynamoDB.
- `tf_bootstrap` — limited role used by a bootstrap workflow to create the S3 bucket and DynamoDB table.

Inputs:
- `repository` — GitHub repository (owner/repo) used to restrict the OIDC subject.
- `branch` — optional branch filter (e.g. `main`). If empty, any branch in the repo is allowed.
- `state_bucket_arn`, `dynamodb_table_arn` — ARNs for the state resources to grant access to.

Outputs:
- `runner_role_arn` — ARN for the TF runner role.
- `bootstrap_role_arn` — ARN for the bootstrap role.
