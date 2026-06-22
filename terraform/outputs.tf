/**
 * Terraform Outputs for Cloud ETL Pipeline
 */

# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.networking.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.networking.public_subnet_ids
}

# S3 Outputs
output "data_bucket_name" {
  description = "S3 data bucket name"
  value       = module.s3.data_bucket_name
}

output "scripts_bucket_name" {
  description = "S3 scripts bucket name"
  value       = module.s3.scripts_bucket_name
}

output "logs_bucket_name" {
  description = "S3 logs bucket name"
  value       = module.s3.logs_bucket_name
}

# Glue Outputs
output "glue_database_name" {
  description = "Glue database name"
  value       = module.glue.database_name
}

output "glue_job_names" {
  description = "Map of Glue job names by domain"
  value       = module.glue.glue_job_names
}

output "glue_crawler_names" {
  description = "Map of Glue crawler names by domain"
  value       = module.glue.glue_crawler_names
}

# Redshift Outputs
output "redshift_cluster_endpoint" {
  description = "Redshift cluster endpoint"
  value       = module.redshift.cluster_endpoint
  sensitive   = true
}

output "redshift_cluster_id" {
  description = "Redshift cluster identifier"
  value       = module.redshift.cluster_id
}

output "redshift_database_name" {
  description = "Redshift database name"
  value       = module.redshift.database_name
}

# MWAA Outputs
output "mwaa_environment_name" {
  description = "MWAA environment name"
  value       = module.airflow.environment_name
}

output "mwaa_webserver_url" {
  description = "MWAA webserver URL"
  value       = module.airflow.webserver_url
  sensitive   = true
}

# Lambda Outputs
output "lambda_function_arns" {
  description = "Map of Lambda function ARNs"
  value       = module.lambda.lambda_function_arns
}

# Step Functions Outputs
output "step_function_arns" {
  description = "Map of Step Function state machine ARNs by domain"
  value       = module.step_functions.state_machine_arns
}

# Kinesis Outputs
output "kinesis_stream_arns" {
  description = "Map of Kinesis stream ARNs"
  value       = module.kinesis.stream_arns
}

# SageMaker Outputs
output "sagemaker_role_arn" {
  description = "SageMaker execution role ARN"
  value       = module.sagemaker.execution_role_arn
}

# Monitoring Outputs
output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = module.monitoring.sns_topic_arn
}

output "cloudwatch_dashboard_names" {
  description = "List of CloudWatch dashboard names"
  value       = module.monitoring.dashboard_names
}

# IAM Outputs
output "glue_service_role_arn" {
  description = "Glue service role ARN"
  value       = module.iam.glue_service_role_arn
}

output "lambda_role_arn" {
  description = "Lambda execution role ARN"
  value       = module.iam.lambda_role_arn
}

output "redshift_role_arn" {
  description = "Redshift service role ARN"
  value       = module.iam.redshift_role_arn
}

# Deployment Information
output "deployment_info" {
  description = "Deployment information and next steps"
  value = <<-EOT
    ========================================
    Cloud ETL Pipeline - Deployment Complete
    ========================================
    
    Environment: ${var.environment}
    Region: ${var.aws_region}
    
    Next Steps:
    1. Upload Glue scripts to: s3://${module.s3.scripts_bucket_name}/glue/
    2. Upload Airflow DAGs to: s3://${module.s3.scripts_bucket_name}/dags/
    3. Access MWAA: ${module.airflow.webserver_url}
    4. Connect to Redshift: ${module.redshift.cluster_endpoint}
    5. View CloudWatch dashboards for monitoring
    
    For detailed deployment instructions, see DEPLOYMENT.md
    ========================================
  EOT
}
