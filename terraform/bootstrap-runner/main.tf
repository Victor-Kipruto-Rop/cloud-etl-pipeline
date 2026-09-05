terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = var.tags
  }
}

module "state_bootstrap" {
  source               = "../bootstrap"
  region               = var.region
  bucket_name          = var.bucket_name
  dynamodb_table_name  = var.dynamodb_table_name
  tags                 = var.tags
}
