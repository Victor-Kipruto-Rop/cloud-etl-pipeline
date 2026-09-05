Bootstrap Terraform module to create an S3 bucket and DynamoDB table for storing Terraform state and locks.

Usage (local):

```bash
cd terraform/bootstrap
terraform init
terraform apply -var 'bucket_name=terraform-state-123456789012-dev' -var 'dynamodb_table_name=terraform-state-lock-dev' -var 'region=us-east-1'
```

The outputs include `bucket_name` and `dynamodb_table_name` which can be used to populate `terraform/backends/backend.<env>.hcl`.
