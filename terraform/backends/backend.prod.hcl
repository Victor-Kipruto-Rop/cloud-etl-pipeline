bucket         = "terraform-state-<AWS_ACCOUNT_ID>-prod"
key            = "cloud-etl-pipeline/prod/terraform.tfstate"
region         = "us-east-1"
encrypt        = true
dynamodb_table = "terraform-state-lock-prod"
workspace_key_prefix = "env"
