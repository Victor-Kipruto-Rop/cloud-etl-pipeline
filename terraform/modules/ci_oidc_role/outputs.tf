output "runner_role_arn" {
  value = aws_iam_role.tf_runner.arn
}

output "bootstrap_role_arn" {
  value = aws_iam_role.tf_bootstrap.arn
}
