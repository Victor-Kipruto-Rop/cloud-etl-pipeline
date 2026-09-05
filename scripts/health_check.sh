#!/usr/bin/env bash
set -euo pipefail

HEALTH_URL="${DEPLOY_HEALTH_URL:-${HEALTH_URL:-}}"
if [[ $# -gt 0 ]]; then
  HEALTH_URL="${1}"
fi

if [[ -z "${HEALTH_URL}" ]]; then
  echo "Usage: DEPLOY_HEALTH_URL=<url> ./scripts/health_check.sh [url]" >&2
  exit 1
fi

HEALTH_ENDPOINT="${HEALTH_URL%/}"
if [[ "${HEALTH_ENDPOINT}" != *"/health" ]]; then
  HEALTH_ENDPOINT="${HEALTH_ENDPOINT}/health"
fi

response="$(curl -fsS --max-time 20 "${HEALTH_ENDPOINT}")" || {
  echo "Health check failed: ${HEALTH_ENDPOINT} did not respond successfully." >&2
  exit 1
}

status="$(printf '%s' "${response}" | python -c 'import json, sys; payload = json.load(sys.stdin); print(payload.get("overall_status", "unknown"))' 2>/dev/null || true)"

printf '%s\n' "${response}"

if [[ "${status}" == "healthy" || "${status}" == "warning" ]]; then
  echo "Health check passed with status: ${status}"
  exit 0
fi

echo "Health check failed with status: ${status:-unknown}" >&2
exit 1
