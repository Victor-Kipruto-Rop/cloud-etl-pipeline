# CI IAM Guidance for Terraform state and bootstrap

This document recommends a secure IAM role and least-privilege policies for GitHub Actions to bootstrap Terraform state (create S3 bucket + DynamoDB table) and for routine Terraform runs.

## Overview
- Use OIDC (GitHub Actions) to assume an AWS IAM role from workflows — avoid long-lived AWS keys.
- Provide two roles/policies:
  - `tf-bootstrap-role` — used only for the bootstrap workflow that *creates* the S3 bucket and DynamoDB table. Short-lived, audited, and manually approved.
  - `tf-runner-role` — used by normal CI to run `terraform plan` and `apply` (reads/writes state).

## Trust policy (OIDC) — example
Replace `OWNER/REPO` and `ENV` with your values.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:OWNER/REPO:ref:refs/heads/ENV"
        }
      }
    }
  ]
}
```

To limit to GitHub workflows originating from a particular repository and branch, tune the `sub` condition. For more granular control you can use `repo` and `ref` claim filters.

## `tf-bootstrap-role` (policy example)
This role must be able to create the S3 bucket and enable versioning, and create the DynamoDB table. Grant only during the bootstrap window.

Policy (bootstrap-permissions):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutBucketVersioning",
        "s3:PutEncryptionConfiguration",
        "s3:PutBucketPublicAccessBlock",
        "s3:PutBucketPolicy",
        "s3:PutBucketAcl",
        "s3:GetBucketLocation",
        "s3:ListBucket"
      ],
      "Resource": ["arn:aws:s3:::YOUR_BOOTSTRAP_BUCKET", "arn:aws:s3:::YOUR_BOOTSTRAP_BUCKET/*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:UpdateTable",
        "dynamodb:TagResource"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes: you may need `kms:CreateKey` / `kms:PutKeyPolicy` if you enforce SSE-KMS for the bucket; prefer SSE-S3 where possible to avoid extra key management.

## `tf-runner-role` (least-privilege policy example)
This role is used by CI for normal Terraform operations that read/write state and lock/unlock the DynamoDB table.

Policy (runner-permissions):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketVersioning",
        "s3:PutObjectAcl"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR_TF_STATE_BUCKET",
        "arn:aws:s3:::YOUR_TF_STATE_BUCKET/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/YOUR_DYNAMODB_TABLE"
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey*", "kms:DescribeKey"],
      "Resource": "arn:aws:kms:REGION:ACCOUNT_ID:key/YOUR_KMS_KEY_ID"
    }
  ]
}
```

If you are not using KMS for state encryption, remove the `kms` statements.

## How to wire into GitHub Actions
- Create the IAM role with the trust policy above, granting the repository OIDC subject.
- Store the role ARN in `Secrets` or reference it directly in the workflow (`role-to-assume` input used by `aws-actions/configure-aws-credentials`).
- The bootstrap workflow in `.github/workflows/bootstrap-state.yml` expects `secrets.AWS_ROLE_TO_ASSUME` to be set to the role ARN.

## Recommended operational controls
- Limit `tf-bootstrap-role` lifetime: revoke rights after bootstrap completes.
- Enable AWS CloudTrail and monitoring for the role's actions.
- Require manual approval for the bootstrap workflow via `workflow_dispatch` or protected branches.
- Use an allowlist for repository subjects in the OIDC condition.

## Minimal Terraform snippet to create role (example)

See `terraform/aws-iam-role.tf` (example):

```hcl
resource "aws_iam_role" "tf_runner" {
  name = "tf-runner-role"
  assume_role_policy = data.aws_iam_policy_document.github_oidc.json
}

data "aws_iam_policy_document" "github_oidc" {
  statement {
    effect = "Allow"
    principals {
      type = "Federated"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"]
    }
    actions = ["sts:AssumeRoleWithWebIdentity"]
    condition {
      test = "StringEquals"
      values = ["sts.amazonaws.com"]
      variable = "token.actions.githubusercontent.com:aud"
    }
  }
}
```

## Next steps
- Replace placeholders (`ACCOUNT_ID`, `YOUR_TF_STATE_BUCKET`, etc.) with real values from the bootstrap outputs.
- If you want, I can add a Terraform module to create the IAM roles and attach the policies above.
