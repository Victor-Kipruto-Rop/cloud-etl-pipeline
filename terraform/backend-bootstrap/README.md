# Backend Bootstrap — CI OIDC wiring

This folder contains helper files to bootstrap Terraform backends and an example
showing how to instantiate the `ci_oidc_role` module and wire its outputs into
GitHub Actions secrets.

Steps
1. Edit `ci_oidc_example.tf` with your `OWNER/REPO`, state bucket, and table ARNs.
2. Run:

```bash
cd terraform/backend-bootstrap
terraform init
terraform apply -auto-approve
```

3. Get the role ARNs produced by the module:

```bash
terraform output -json > outputs.json
jq . ci_runner_role_arn outputs.json
jq . ci_bootstrap_role_arn outputs.json
```

4. Set the role ARN(s) as GitHub repository secrets so the Actions workflows can assume them.
   Recommended secrets:

- `AWS_ROLE_TO_ASSUME_BOOTSTRAP` — used by the bootstrap workflow to create state resources.
- `AWS_ROLE_TO_ASSUME_RUNNER` — used by CI workflows to run `terraform plan`/`apply` and access state.

Using the `gh` CLI:

```bash
# assuming outputs.json contains the ARNs
BOOTSTRAP_ROLE=$(jq -r '.ci_bootstrap_role_arn.value' outputs.json)
RUNNER_ROLE=$(jq -r '.ci_runner_role_arn.value' outputs.json)

gh secret set AWS_ROLE_TO_ASSUME_BOOTSTRAP --body "$BOOTSTRAP_ROLE"
gh secret set AWS_ROLE_TO_ASSUME_RUNNER --body "$RUNNER_ROLE"
```

Or use the GitHub UI to add repository-level secrets under Settings → Secrets → Actions.

5. Update `.github/workflows/bootstrap-state.yml` to use the bootstrap secret (example already uses `secrets.AWS_ROLE_TO_ASSUME`). For runner workflows, configure the `aws-actions/configure-aws-credentials` step to assume `secrets.AWS_ROLE_TO_ASSUME_RUNNER`.

Notes
- For more constrained policies, prefer creating environment-specific roles and limit `token.actions.githubusercontent.com:sub` to the exact `repo:OWNER/REPO:ref:refs/heads/ENV` value.
- If you need me to automate the secret creation without `gh`, I can add a script that uses the GitHub REST API with a personal access token (do not paste tokens in chat).
