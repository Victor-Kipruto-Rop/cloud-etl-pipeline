/**
 * Terraform Variables for Cloud ETL Pipeline
 */

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "cloud-etl-pipeline"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# Glue Configuration
variable "glue_database_name" {
  description = "AWS Glue database name"
  type        = string
  default     = "etl_catalog"
}

variable "domains" {
  description = "Data pipeline domains"
  type        = list(string)
  default     = ["ecommerce", "healthcare", "finance", "sports", "climate"]
}

# Redshift Configuration
variable "redshift_cluster_identifier" {
  description = "Redshift cluster identifier"
  type        = string
  default     = "etl-analytics-cluster"
}

variable "redshift_database_name" {
  description = "Redshift database name"
  type        = string
  default     = "analytics_dw"
}

variable "redshift_master_username" {
  description = "Redshift master username"
  type        = string
  default     = "admin"
}

variable "redshift_node_type" {
  description = "Redshift node type"
  type        = string
  default     = "dc2.large"
}

variable "redshift_number_of_nodes" {
  description = "Number of Redshift nodes"
  type        = number
  default     = 2
}

# MWAA (Airflow) Configuration
variable "mwaa_environment_name" {
  description = "MWAA environment name"
  type        = string
  default     = "etl-mwaa-environment"
}

variable "mwaa_airflow_version" {
  description = "Apache Airflow version"
  type        = string
  default     = "2.5.1"
}

variable "mwaa_environment_class" {
  description = "MWAA environment class"
  type        = string
  default     = "mw1.small"
}

variable "mwaa_max_workers" {
  description = "Maximum number of Airflow workers"
  type        = number
  default     = 10
}

variable "mwaa_min_workers" {
  description = "Minimum number of Airflow workers"
  type        = number
  default     = 1
}

variable "mwaa_schedulers" {
  description = "Number of Airflow schedulers"
  type        = number
  default     = 2
}

# Kinesis Configuration
variable "kinesis_streams" {
  description = "Kinesis stream configurations"
  type = map(object({
    shard_count      = number
    retention_period = number
  }))
  default = {
    ecommerce_events = {
      shard_count      = 2
      retention_period = 24
    }
  }
}

# Tags
variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
