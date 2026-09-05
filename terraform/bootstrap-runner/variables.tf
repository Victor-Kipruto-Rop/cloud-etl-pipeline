variable "region" {
  description = "AWS region for bootstrap resources"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "S3 bucket name for Terraform state (must be globally unique)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.bucket_name)) && length(var.bucket_name) >= 3 && length(var.bucket_name) <= 63
    error_message = "Bucket name must be 3-63 characters, lowercase letters, numbers, and hyphens only."
  }
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for Terraform state locking"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9_.-]+$", var.dynamodb_table_name)) && length(var.dynamodb_table_name) <= 255
    error_message = "Table name must be 255 characters or fewer and contain only alphanumeric characters, hyphens, underscores, and periods."
  }
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "cloud-etl-pipeline"
    Environment = "bootstrap"
    ManagedBy   = "Terraform"
  }
}
