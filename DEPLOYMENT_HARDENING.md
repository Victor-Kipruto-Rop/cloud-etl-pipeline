# Deployment Hardening Checklist

This file summarizes recommended production-grade deployment hardening steps for the `cloud-etl-pipeline` project.

1. Orchestration & Rollout
   - Environments: `dev` → `staging` → `production` promotion pipeline.
   - Use feature flags and canary/percentage-based traffic shifting for critical changes.
   - Implement automatic rollback on failed health checks or smoke tests.
   - Require manual approval for production deploys (approval gate).

2. Secrets & Credentials
   - Use GitHub OIDC to assume short-lived AWS roles from Actions; avoid long-lived keys.
   - Restrict the CI role to least privilege (see `terraform/backend-bootstrap/CI_IAM_GUIDANCE.md`).
   - Rotate credentials and monitor usage via CloudTrail.

3. CI/CD Security
   - Run CodeQL, dependency review, and secret scanning on PRs.
   - Run container scanning (Trivy/Grype) for images built in CI.
   - Generate and verify SBOMs for built images.
   - Fail the pipeline for high/critical vulnerabilities, or require manual approval.

4. Terraform & Infra Safety
   - Per-environment backends with S3 + DynamoDB for state locking.
   - Enable S3 bucket versioning and encryption (SSE-S3 or SSE-KMS).
   - Use `terraform plan -detailed-exitcode` in CI and require review before apply.
   - Use drift detection (scheduled) and alert on unexpected changes.

5. Migration Hardening
   - Run pre-deploy checks and dry-run migrations against a staging clone.
   - Use transactional migrations or reversible scripts when possible.
   - Create migration rollback plans and smoke tests to validate data integrity.

6. Observability & SLOs
   - Export SLOs and error budgets to Prometheus/Grafana.
   - Add canary-specific metrics and health checks for new releases.
   - Ensure alerts for freshness, latency p95/p99, and SLO burn rate.

7. Release Metadata & Audit
   - Write `deploy_info.json` at release time with `version`, `commit`, `status`, `timestamp`, `deployed_by`.
   - Record `last_successful_deploy` and `last_failed_deploy` fields for dashboard and health output.

8. Automated Safety Controls
   - Enforce policy checks (Dockerfile, Terraform) using tools like `tflint`, `checkov`, `conftest`.
   - Add SBOM verification and image allowlists for production clusters.

9. Disaster Recovery
   - Backup critical state and metadata (S3 + DynamoDB) and verify restore playbooks.
   - Define RTO/RPO and test restore procedures periodically.

Next steps
- I can add a Terraform module to create the IAM roles for CI OIDC.
- I can add GitHub Action workflows to implement canary deploys and approval gates.
