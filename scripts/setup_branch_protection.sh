#!/usr/bin/env bash
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required. Install it first: https://cli.github.com/" >&2
  exit 1
fi

OWNER_REPO="${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
BRANCH="${1:-main}"

printf 'Configuring branch protection for %s on %s\n' "$BRANCH" "$OWNER_REPO"

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${OWNER_REPO}/branches/${BRANCH}/protection" \
  -f required_status_checks='{"strict":true,"contexts":["CI Pipeline"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":true,"require_last_push_approval":true,"bypass_pull_request_allowances":{"users":[],"teams":[],"apps":[]}}' \
  -f restrictions='null' \
  -f required_linear_history=true \
  -f allow_force_pushes=false \
  -f allow_deletions=false \
  -f block_creations=false \
  -f required_conversation_resolution=true

printf '\nBranch protection configured. Add environment approvals in GitHub Settings -> Environments.\n'
