bucket         = "terraform-state-<AWS_ACCOUNT_ID>-staging"
key            = "cloud-etl-pipeline/staging/terraform.tfstate"
region         = "us-east-1"
encrypt        = true
dynamodb_table = "terraform-state-lock-staging"
workspace_key_prefix = "env"
