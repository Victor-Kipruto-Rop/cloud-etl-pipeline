resource "aws_s3_bucket" "data_lake" {
  bucket = var.bucket_name
  tags = merge(var.tags, {
    Project     = "CloudETLPipeline"
    Environment = var.environment
    ManagedBy   = "Terraform"
  })
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket                  = aws_s3_bucket.data_lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    id     = "bronze-retention"
    status = "Enabled"
    filter {
      prefix = "bronze/"
    }
    dynamic "expiration" {
      for_each = var.bronze_expiration_days > 0 ? [1] : []
      content {
        days = var.bronze_expiration_days
      }
    }
  }
  rule {
    id     = "noncurrent-version-retention"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_expiration_days
    }
  }
  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

data "aws_iam_policy_document" "bucket_transport" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.data_lake.arn, "${aws_s3_bucket.data_lake.arn}/*"]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  policy = data.aws_iam_policy_document.bucket_transport.json
  depends_on = [
    aws_s3_bucket_public_access_block.data_lake,
    aws_s3_bucket_ownership_controls.data_lake,
  ]
}

data "aws_iam_policy_document" "etl_data_access" {
  statement {
    sid       = "ListDataLakePrefixes"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data_lake.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["bronze/*", "silver/*", "gold/*", "quarantine/*"]
    }
  }
  statement {
    sid    = "ReadWritePipelineObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:AbortMultipartUpload",
      "s3:ListMultipartUploadParts"
    ]
    resources = [
      "${aws_s3_bucket.data_lake.arn}/bronze/*",
      "${aws_s3_bucket.data_lake.arn}/silver/*",
      "${aws_s3_bucket.data_lake.arn}/gold/*",
      "${aws_s3_bucket.data_lake.arn}/quarantine/*"
    ]
  }
}

resource "aws_iam_policy" "etl_data_access" {
  name        = "${var.bucket_name}-etl-data-access"
  description = "Prefix-scoped data lake access for the Cloud ETL pipeline."
  policy      = data.aws_iam_policy_document.etl_data_access.json
}

resource "aws_iam_role_policy_attachment" "etl_data_access" {
  count      = var.execution_role_name == "" ? 0 : 1
  role       = var.execution_role_name
  policy_arn = aws_iam_policy.etl_data_access.arn
}
