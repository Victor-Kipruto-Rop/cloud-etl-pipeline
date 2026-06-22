/**
 * Main Terraform Configuration for Cloud ETL Pipeline
 * 
 * This provisions all AWS infrastructure required for the multi-domain
 * data pipeline including S3, Glue, Redshift, MWAA, Lambda, and monitoring.
 */

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket         = "terraform-state-${var.aws_account_id}"
    key            = "cloud-etl-pipeline/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "CloudETLPipeline"
      Environment = var.environment
      ManagedBy   = "Terraform"
      CostCenter  = "DataEngineering"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# Local variables
locals {
  account_id = data.aws_caller_identity.current.account_id
  common_tags = {
    Project     = "CloudETLPipeline"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# VPC and Networking
module "networking" {
  source = "./modules/networking"
  
  vpc_cidr            = var.vpc_cidr
  environment         = var.environment
  availability_zones  = data.aws_availability_zones.available.names
  
  tags = local.common_tags
}

# S3 Buckets
module "s3" {
  source = "./modules/s3"
  
  environment     = var.environment
  account_id      = local.account_id
  data_bucket     = "${var.project_name}-data-${local.account_id}"
  scripts_bucket  = "${var.project_name}-scripts-${local.account_id}"
  logs_bucket     = "${var.project_name}-logs-${local.account_id}"
  
  tags = local.common_tags
}

# IAM Roles and Policies
module "iam" {
  source = "./modules/iam"
  
  environment     = var.environment
  data_bucket     = module.s3.data_bucket_name
  scripts_bucket  = module.s3.scripts_bucket_name
  logs_bucket     = module.s3.logs_bucket_name
  
  tags = local.common_tags
}

# AWS Secrets Manager
module "secrets" {
  source = "./modules/secrets"
  
  environment = var.environment
  
  tags = local.common_tags
}

# AWS Glue (Data Catalog, Jobs, Crawlers)
module "glue" {
  source = "./modules/glue"
  
  environment         = var.environment
  database_name       = var.glue_database_name
  data_bucket         = module.s3.data_bucket_name
  scripts_bucket      = module.s3.scripts_bucket_name
  glue_service_role   = module.iam.glue_service_role_arn
  
  domains = var.domains
  
  tags = local.common_tags
}

# Amazon Redshift
module "redshift" {
  source = "./modules/redshift"
  
  environment            = var.environment
  cluster_identifier     = var.redshift_cluster_identifier
  database_name          = var.redshift_database_name
  master_username        = var.redshift_master_username
  node_type              = var.redshift_node_type
  number_of_nodes        = var.redshift_number_of_nodes
  
  vpc_id                 = module.networking.vpc_id
  subnet_ids             = module.networking.private_subnet_ids
  security_group_ids     = [module.networking.redshift_security_group_id]
  
  iam_roles              = [module.iam.redshift_role_arn]
  
  tags = local.common_tags
}

# AWS Lambda Functions
module "lambda" {
  source = "./modules/lambda"
  
  environment        = var.environment
  scripts_bucket     = module.s3.scripts_bucket_name
  lambda_role_arn    = module.iam.lambda_role_arn
  
  vpc_id             = module.networking.vpc_id
  subnet_ids         = module.networking.private_subnet_ids
  security_group_ids = [module.networking.lambda_security_group_id]
  
  tags = local.common_tags
}

# Step Functions State Machines
module "step_functions" {
  source = "./modules/step_functions"
  
  environment           = var.environment
  step_functions_role   = module.iam.step_functions_role_arn
  glue_jobs             = module.glue.glue_job_names
  lambda_functions      = module.lambda.lambda_function_arns
  
  domains = var.domains
  
  tags = local.common_tags
}

# Amazon MWAA (Managed Airflow)
module "airflow" {
  source = "./modules/airflow"
  
  environment            = var.environment
  environment_name       = var.mwaa_environment_name
  airflow_version        = var.mwaa_airflow_version
  environment_class      = var.mwaa_environment_class
  
  vpc_id                 = module.networking.vpc_id
  subnet_ids             = module.networking.private_subnet_ids
  security_group_ids     = [module.networking.mwaa_security_group_id]
  
  dags_bucket            = module.s3.scripts_bucket_name
  dags_s3_path           = "dags"
  execution_role_arn     = module.iam.mwaa_execution_role_arn
  
  max_workers            = var.mwaa_max_workers
  min_workers            = var.mwaa_min_workers
  schedulers             = var.mwaa_schedulers
  
  tags = local.common_tags
}

# Amazon Kinesis (Streaming)
module "kinesis" {
  source = "./modules/kinesis"
  
  environment     = var.environment
  streams         = var.kinesis_streams
  
  tags = local.common_tags
}

# Amazon SageMaker (ML Pipelines)
module "sagemaker" {
  source = "./modules/sagemaker"
  
  environment          = var.environment
  sagemaker_role_arn   = module.iam.sagemaker_role_arn
  data_bucket          = module.s3.data_bucket_name
  
  vpc_id               = module.networking.vpc_id
  subnet_ids           = module.networking.private_subnet_ids
  security_group_ids   = [module.networking.sagemaker_security_group_id]
  
  tags = local.common_tags
}

# CloudWatch Monitoring and Alarms
module "monitoring" {
  source = "./modules/monitoring"
  
  environment           = var.environment
  sns_topic_arn         = module.monitoring.sns_topic_arn
  
  # Resources to monitor
  glue_jobs             = module.glue.glue_job_names
  lambda_functions      = module.lambda.lambda_function_names
  redshift_cluster      = module.redshift.cluster_id
  step_functions        = module.step_functions.state_machine_arns
  
  tags = local.common_tags
}
