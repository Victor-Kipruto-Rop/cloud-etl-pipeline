#!/bin/bash
# Script to create PR from terraform/backend-bootstrap to main
# Usage: GITHUB_TOKEN=<your-token> ./scripts/create_bootstrap_pr.sh

set -euo pipefail

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "ERROR: GITHUB_TOKEN environment variable not set" >&2
  echo "Usage: GITHUB_TOKEN=<your-token> $0" >&2
  exit 1
fi

REPO_OWNER="Victor-Kipruto-Rop"
REPO_NAME="cloud-etl-pipeline"

echo "Creating PR from terraform/backend-bootstrap to main..."

curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/pulls" \
  -d @- << 'EOF'
{
  "title": "feat(terraform): add bootstrap infrastructure with state management and environment backends",
  "head": "terraform/backend-bootstrap",
  "base": "main",
  "body": "## Overview\n\nThis PR introduces a comprehensive Terraform bootstrap infrastructure for managing state across dev, staging, and production environments with S3-backed remote state and DynamoDB locking.\n\n## Changes\n\n### Bootstrap Infrastructure\n- **terraform/bootstrap/**: Reusable module that creates:\n  - S3 bucket with encryption, versioning, and public access blocking\n  - DynamoDB table for state locking (pay-per-request billing)\n  - Modern Terraform syntax (AWS provider 4.x+ compatible)\n\n- **terraform/bootstrap-runner/**: Wrapper configuration for easy bootstrap initialization:\n  - Input variables with comprehensive descriptions and validation rules\n  - Terraform provider configuration with default tags\n  - Outputs to display created S3 bucket and DynamoDB table names\n\n### Environment Backends\n- **terraform/backends/**: Environment-specific backend configurations:\n  - backend.dev.hcl — Dev state bucket and locking table\n  - backend.staging.hcl — Staging state bucket and locking table\n  - backend.prod.hcl — Production state bucket and locking table\n- **terraform/backend.hcl.example**: Template for users to customize\n\n### Operational Scripts\n- **terraform/init_workspace.sh**: Initialize Terraform backend and create workspace for environment\n- **terraform/drift_check.sh**: Run drift detection with S3/DynamoDB health checks\n- **terraform/gen_backend_from_bootstrap.sh**: Generate backend files from bootstrap outputs\n\n### Documentation\n- **terraform/USAGE.md**: Quick-start guide and drift detection setup\n- **terraform/bootstrap/README.md**: Bootstrap module usage instructions\n- **terraform/backend-bootstrap/CI_IAM_GUIDANCE.md**: OIDC and IAM policies for GitHub Actions\n\n## Key Features\n\n✅ **AWS Provider 4.x+ Compatible** — Modernized S3 bucket configuration with separate resource blocks\n✅ **State Locking** — DynamoDB-backed locking prevents concurrent state mutations\n✅ **Versioning** — S3 versioning enabled for disaster recovery\n✅ **Environment Separation** — Distinct backends for dev, staging, production\n✅ **Validation** — Input variable validation for bucket names and DynamoDB table names\n✅ **Default Tags** — Consistent resource tagging across all bootstrap infrastructure\n✅ **OIDC Ready** — Documentation for GitHub Actions OIDC role assumption\n\n## Testing\n\n- Terraform configuration validated for syntax and provider compatibility\n- Variable validation rules applied to bucket and table names\n- Outputs tested to ensure proper S3 and DynamoDB resource exposure\n\n## Related Documentation\n\nSee DEPLOYMENT.md and terraform/USAGE.md for usage guidance."
}
EOF

echo ""
echo "✅ PR creation request sent! Check GitHub for the new PR."
