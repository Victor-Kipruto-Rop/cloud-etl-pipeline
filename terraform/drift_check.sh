#!/usr/bin/env bash
set -euo pipefail
# Usage: ./drift_check.sh <env>
ENV=${1:-}
if [[ -z "$ENV" ]]; then
  echo "Usage: $0 <dev|staging|prod>" >&2
  exit 2
fi

echo "Running drift detection for environment=$ENV"
export TF_WORKSPACE="$ENV"

# Ensure backend/init and workspace selected
./terraform/init_workspace.sh "$ENV"

# Basic state locking / backup checks (S3 + DynamoDB) - best-effort checks
BACKEND_FILE="terraform/backends/backend.${ENV}.hcl"
BUCKET=$(grep '^bucket' "$BACKEND_FILE" | awk -F= '{gsub(/\"| /, "", $2); print $2}')
TABLE=$(grep '^dynamodb_table' "$BACKEND_FILE" | awk -F= '{gsub(/\"| /, "", $2); print $2}')

echo "Checking S3 bucket $BUCKET exists and versioning is enabled"
if ! aws s3api head-bucket --bucket "$BUCKET" >/dev/null 2>&1; then
  echo "Warning: S3 bucket $BUCKET not accessible or does not exist"
else
  ver=$(aws s3api get-bucket-versioning --bucket "$BUCKET" --query 'Status' --output text || echo "")
  echo "Bucket versioning: ${ver:-Disabled}"
fi

echo "Checking DynamoDB lock table $TABLE"
if ! aws dynamodb describe-table --table-name "$TABLE" >/dev/null 2>&1; then
  echo "Warning: DynamoDB table $TABLE not found or inaccessible"
else
  echo "DynamoDB table $TABLE exists"
fi

echo "Running terraform plan (detailed-exitcode) to detect drift"
terraform plan -input=false -refresh=true -detailed-exitcode -out=plan_${ENV}.tfplan || PLAN_EXIT=$?
PLAN_EXIT=${PLAN_EXIT:-0}
if [[ "$PLAN_EXIT" -eq 0 ]]; then
  echo "No changes detected (plan exit 0)"
  exit 0
elif [[ "$PLAN_EXIT" -eq 2 ]]; then
  echo "Drift detected (plan exit 2)"
  terraform show -no-color plan_${ENV}.tfplan > plan_${ENV}.txt || true
  echo "Plan written to plan_${ENV}.txt"
  exit 2
else
  echo "Terraform plan failed with exit $PLAN_EXIT"
  exit "$PLAN_EXIT"
fi
