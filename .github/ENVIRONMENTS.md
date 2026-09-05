# GitHub environments and deployment policy

This repository expects the following GitHub Environments to exist in the repository settings:

- `dev`
- `staging`
- `production`

## Required protections

- Protect `main` with required status checks and required PR reviews
- Require at least one reviewer approval for `staging` and `production`
- Require successful `CI Pipeline` status checks before deployment
- Require a smoke test or health check pass before any production promotion
- Enforce environment-specific secrets and variables
- Block direct pushes to protected release branches
- Require all deployment jobs to target an explicit environment

## Production-only approval gate

The workflow at `.github/workflows/production-approval-gate.yml` is the formal approval checkpoint for production. It must be executed or approved before a production deployment proceeds.

Rules:
- `production` deployments require a human approval in the GitHub Environment
- The gate validates `DEPLOY_HEALTH_URL` before allowing release continuation
- The gate must be approved after the change has passed CI and smoke tests
- No production deploy should bypass this approval gate

## Recommended variables

For each environment, define:
- `AWS_REGION`
- `DEPLOY_HEALTH_URL`
- `AWS_ACCOUNT_ID`

## Recommended secrets

- `AWS_ROLE_TO_ASSUME`
- `AWS_ACCESS_KEY_ID` (only when absolutely required and short-lived)
- `AWS_SECRET_ACCESS_KEY` (only when absolutely required and short-lived)
- `GITHUB_TOKEN` is handled by GitHub Actions automatically

## Promotion order

1. Merge to `main`
2. CI runs lint, tests, and smoke checks
3. Deploy to `dev` after automated validation passes
4. Run dev smoke checks and then promote to `staging`
5. Run staging smoke checks and require approval before production
6. Run the production approval gate and require environment approval
7. Execute a production canary rollout with an explicit traffic percentage
8. Only proceed to full production rollout after healthy canary validation
9. Automatically roll back if smoke checks or health checks fail

## Production rollback

- Revert the previous stable image or Terraform state version
- Run required database rollback steps if a migration was applied
- Verify the health endpoint and downstream metrics are back to normal
- Record incident and remediation in deployment notes
- Require a new approval gate before redeploying the fixed version

## Branch protection checklist

Use repository settings to enforce:
- required PR reviews
- required status checks
- dismissal of stale reviews
- conversation resolution
- no force pushes
- no deletions
- linear history
