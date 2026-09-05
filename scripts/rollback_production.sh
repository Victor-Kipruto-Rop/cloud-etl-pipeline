#!/usr/bin/env bash
set -euo pipefail

TARGET_TAG="${1:-${ROLLBACK_TARGET_TAG:-${PREVIOUS_RELEASE_TAG:-}}}"
ROLLBACK_COMMAND="${ROLLBACK_COMMAND:-}"
HEALTH_URL="${PRODUCTION_HEALTH_URL:-${DEPLOY_HEALTH_URL:-}}"

if [[ -z "${TARGET_TAG}" ]]; then
  echo "Usage: ./scripts/rollback_production.sh <previous-release-tag>" >&2
  echo "Or set ROLLBACK_TARGET_TAG or PREVIOUS_RELEASE_TAG before running." >&2
  exit 1
fi

if [[ -z "${ROLLBACK_COMMAND}" ]]; then
  echo "No ROLLBACK_COMMAND supplied; this is a dry-run rollback plan for ${TARGET_TAG}."
  echo "Recommended actions:"
  echo "  1. Restore the previous stable image/tag: ${TARGET_TAG}"
  echo "  2. Revert traffic routing back to the last known-good deployment"
  echo "  3. Re-run health checks on the production endpoint"
  echo "  4. Verify dashboard and metrics recover before resuming normal traffic"
  exit 0
fi

echo "Executing rollback command for tag: ${TARGET_TAG}"
eval "${ROLLBACK_COMMAND}"

echo "Rollback command completed. Verifying health endpoint..."
if [[ -n "${HEALTH_URL}" ]]; then
  export DEPLOY_HEALTH_URL="${HEALTH_URL}"
  "$(dirname "$0")/health_check.sh"
else
  echo "No production health URL configured; skipping post-rollback health validation."
fi

echo "Rollback verification complete."
