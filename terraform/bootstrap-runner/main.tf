module "state_bootstrap" {
  source               = "../bootstrap"
  region               = var.region
  bucket_name          = var.bucket_name
  dynamodb_table_name  = var.dynamodb_table_name
  tags                 = var.tags
}
