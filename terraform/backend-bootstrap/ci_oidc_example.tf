/*
Example usage: instantiate the CI OIDC role module.

Customize the variables below for your repository and state resources, then
run `terraform init` and `terraform apply` in this folder.
*/

module "ci_oidc" {
  source = "../../modules/ci_oidc_role"

  name_prefix         = "cloud-etl"
  repository          = "OWNER/REPO"       # replace with your repo
  branch              = "main"             # optional branch restriction
  state_bucket_arn    = "arn:aws:s3:::YOUR_TF_STATE_BUCKET"
  state_bucket_name   = "YOUR_TF_STATE_BUCKET"
  dynamodb_table_arn  = "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/YOUR_TABLE"
  kms_key_arn         = ""                 # optional
}

output "ci_runner_role_arn" {
  value = module.ci_oidc.runner_role_arn
}

output "ci_bootstrap_role_arn" {
  value = module.ci_oidc.bootstrap_role_arn
}
