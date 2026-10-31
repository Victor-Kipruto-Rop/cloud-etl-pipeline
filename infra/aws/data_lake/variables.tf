variable "bucket_name" {
  description = "Globally unique S3 bucket name for the ETL data lake."
  type        = string
}

variable "environment" {
  description = "Deployment environment used for resource tags."
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be dev, staging, or production."
  }
}

variable "execution_role_name" {
  description = "Existing IAM role that receives scoped read/write access; empty disables attachment."
  type        = string
  default     = ""
}

variable "bronze_expiration_days" {
  description = "Retention period for bronze objects. Set to 0 to retain indefinitely."
  type        = number
  default     = 365
  validation {
    condition     = var.bronze_expiration_days >= 0
    error_message = "bronze_expiration_days must be zero or greater."
  }
}

variable "noncurrent_version_expiration_days" {
  description = "Retention for noncurrent object versions."
  type        = number
  default     = 90
  validation {
    condition     = var.noncurrent_version_expiration_days >= 1
    error_message = "noncurrent_version_expiration_days must be at least one."
  }
}

variable "tags" {
  description = "Additional resource tags."
  type        = map(string)
  default     = {}
}
