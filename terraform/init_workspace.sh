#!/usr/bin/env bash
set -euo pipefail
# Usage: ./init_workspace.sh <env>
ENV=${1:-}
if [[ -z "$ENV" ]]; then
  echo "Usage: $0 <dev|staging|prod>" >&2
  exit 2
fi

BACKEND_FILE="terraform/backends/backend.${ENV}.hcl"
if [[ ! -f "$BACKEND_FILE" ]]; then
  echo "Backend file $BACKEND_FILE not found. Create from backend.hcl.example and replace placeholders." >&2
  exit 2
fi

echo "Initializing Terraform backend for environment=$ENV using $BACKEND_FILE"
terraform init -backend-config="$BACKEND_FILE"

# Use workspaces to isolate state (optional)
if terraform workspace list | grep -q "${ENV}"; then
  terraform workspace select "$ENV"
else
  terraform workspace new "$ENV"
fi

echo "Initialized and selected workspace '$ENV'"
