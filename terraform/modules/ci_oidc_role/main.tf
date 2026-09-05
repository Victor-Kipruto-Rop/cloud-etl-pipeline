data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "github_oidc" {
  statement {
    effect = "Allow"
    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"]
    }

    actions = ["sts:AssumeRoleWithWebIdentity"]

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Allow the repository; optionally restrict to branch
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.repository}:ref:refs/heads/${var.branch != "" ? var.branch : "*"}"]
    }
  }
}

resource "aws_iam_role" "tf_runner" {
  name               = "${var.name_prefix}-tf-runner"
  assume_role_policy = data.aws_iam_policy_document.github_oidc.json
}

resource "aws_iam_role_policy" "tf_runner_policy" {
  name   = "${var.name_prefix}-tf-runner-policy"
  role   = aws_iam_role.tf_runner.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketVersioning"
        ],
        Resource = [
          var.state_bucket_arn,
          "${var.state_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:DescribeTable"
        ],
        Resource = [
          var.dynamodb_table_arn
        ]
      }
    ]
  })
}

# Optional KMS permissions when using SSE-KMS for state
resource "aws_iam_role_policy" "tf_runner_kms" {
  count  = var.kms_key_arn == "" ? 0 : 1
  name   = "${var.name_prefix}-tf-runner-kms"
  role   = aws_iam_role.tf_runner.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey*", "kms:DescribeKey"],
        Resource = [var.kms_key_arn]
      }
    ]
  })
}

#########################
# Bootstrap role (limited create permissions)
#########################
resource "aws_iam_role" "tf_bootstrap" {
  name               = "${var.name_prefix}-tf-bootstrap"
  assume_role_policy = data.aws_iam_policy_document.github_oidc.json
}

resource "aws_iam_role_policy" "tf_bootstrap_policy" {
  name = "${var.name_prefix}-tf-bootstrap-policy"
  role = aws_iam_role.tf_bootstrap.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      merge(
        {
          Effect = "Allow"
          Action = [
            "s3:CreateBucket",
            "s3:PutBucketVersioning",
            "s3:PutBucketPolicy",
            "s3:PutBucketAcl",
            "s3:PutEncryptionConfiguration",
            "s3:PutBucketPublicAccessBlock",
            "s3:GetBucketLocation",
            "s3:ListBucket"
          ]
          Resource = [
            "arn:aws:s3:::*"
          ]
        },
        var.bootstrap_bucket_name == "" ? {} : {
          Condition = {
            StringLike = {
              "aws:RequestBucket" = [var.bootstrap_bucket_name]
            }
          }
        }
      ),
      {
        Effect = "Allow",
        Action = [
          "dynamodb:CreateTable",
          "dynamodb:DescribeTable",
          "dynamodb:UpdateTable",
          "dynamodb:TagResource"
        ],
        Resource = ["*"]
      }
    ]
  })
}

output "tf_runner_role_arn" {
  value = aws_iam_role.tf_runner.arn
}

output "tf_bootstrap_role_arn" {
  value = aws_iam_role.tf_bootstrap.arn
}
