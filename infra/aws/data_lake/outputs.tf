output "bucket_name" {
  value = aws_s3_bucket.data_lake.id
}

output "bucket_arn" {
  value = aws_s3_bucket.data_lake.arn
}

output "etl_policy_arn" {
  value = aws_iam_policy.etl_data_access.arn
}
