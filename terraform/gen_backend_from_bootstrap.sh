#!/usr/bin/env bash
set -euo pipefail
# Usage: ./terraform/gen_backend_from_bootstrap.sh <env> <bucket> <dynamodb_table>
ENV=${1:-}
BUCKET=${2:-}
TABLE=${3:-}
if [[ -z "$ENV" || -z "$BUCKET" || -z "$TABLE" ]]; then
  echo "Usage: $0 <dev|staging|prod> <bucket> <dynamodb_table>" >&2
  exit 2
fi

OUT="terraform/backends/backend.${ENV}.hcl"
cat > "$OUT" <<EOF
bucket         = "${BUCKET}"
key            = "cloud-etl-pipeline/${ENV}/terraform.tfstate"
region         = "us-east-1"
encrypt        = true
dynamodb_table = "${TABLE}"
workspace_key_prefix = "env"
EOF

echo "Wrote $OUT"
