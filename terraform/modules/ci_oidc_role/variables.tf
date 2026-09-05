variable "name_prefix" {
  description = "Prefix for IAM role names"
  type        = string
  default     = "cloud-etl"
}

variable "repository" {
  description = "GitHub repository in the form owner/repo (used in OIDC subject)"
  type        = string
}

variable "branch" {
  description = "Optional branch filter for OIDC subject (e.g. refs/heads/main). If empty, allows any branch for the repo."
  type        = string
  default     = ""
}

variable "state_bucket_arn" {
  description = "ARN of the Terraform S3 state bucket (used by runner policy)"
  type        = string
  default     = ""
}

variable "state_bucket_name" {
  description = "Name of the Terraform S3 state bucket (used by runner policy)"
  type        = string
  default     = ""
}

variable "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table used for Terraform state locking"
  type        = string
  default     = ""
}

variable "kms_key_arn" {
  description = "Optional KMS key ARN used to encrypt state objects (optional)"
  type        = string
  default     = ""
}

variable "bootstrap_bucket_name" {
  description = "Name of the S3 bucket created by the bootstrap role (used to scope S3 permissions)"
  type        = string
  default     = ""
}

variable "bootstrap_dynamodb_table" {
  description = "Name of the DynamoDB lock table created by the bootstrap role (used to scope DynamoDB permissions)"
  type        = string
  default     = ""
}</oldString>


