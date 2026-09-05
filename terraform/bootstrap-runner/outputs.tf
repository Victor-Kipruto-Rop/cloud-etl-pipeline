output "bucket_name" {
  description = "Name of the S3 bucket storing Terraform state"
  value       = module.state_bootstrap.bucket_name
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  value       = module.state_bootstrap.dynamodb_table_name
}
