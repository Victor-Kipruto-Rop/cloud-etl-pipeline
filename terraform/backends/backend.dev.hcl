bucket         = "terraform-state-<AWS_ACCOUNT_ID>-dev"
key            = "cloud-etl-pipeline/dev/terraform.tfstate"
region         = "us-east-1"
encrypt        = true
dynamodb_table = "terraform-state-lock-dev"
workspace_key_prefix = "env"
