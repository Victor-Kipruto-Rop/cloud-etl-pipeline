# Deployment Guide

This repository is configured for local ETL development, dataset ingestion, optional AWS upload helper usage, and controlled environment-based promotion.

## GitHub environments and promotion flow

Use separate GitHub Environments named `dev`, `staging`, and `production` in the repository settings.

Required policy:
- `dev`: automatic or manual deployment for non-production validation
- `staging`: required approval before promotion from `main` and before production release
- `production`: required reviewers, explicit environment approval, and a dedicated gate before apply or release

Recommended repository rules:
- Protect `main` with required status checks, linear history, and no force pushes
- Require at least one approving review for staging and production
- Require branch protection for all deployment branches
- Require a successful `CI Pipeline` status before merge or deploy
- Require environment approvals in GitHub Settings -> Environments

The workflow in `.github/workflows/release-promotion.yml` enforces a promotion gate and smoke test step before a release can advance to the selected environment. The workflow in `.github/workflows/production-approval-gate.yml` is the explicit production-only approval requirement and must be used for all production deployments. The workflow in `.github/workflows/staged-rollout.yml` defines the true sequential release path: dev -> staging -> production.

### True staged rollout flow

The rollout sequence is intentionally strict:
1. Deploy to `dev`
2. Run smoke tests on the dev endpoint
3. Promote to `staging`
4. Run smoke tests on the staging endpoint
5. Require explicit production approval
6. Run a production canary rollout with a small percentage of traffic
7. Run successful smoke checks before full promotion
8. Automatically roll back when smoke checks or health checks fail

### Canary and percentage-based deployment guidance

For future production environments beyond Terraform-only infrastructure:
- expose a traffic-routing control or load-balancer switch
- route 5% to 20% of production traffic to the new release first
- validate error rate, latency, and health checkpoints before increasing the percentage
- keep the rollback plan ready so the canary can be reverted immediately

### Automatic rollback policy

Automatic rollback must trigger when:
- the health endpoint returns unhealthy
- the smoke test fails after deployment
- the metrics threshold for error rate or degradation is triggered
- the staged rollout cannot reach the expected healthy state within a timeout

Rollback actions should include:
- restore the last known-good image or version
- restore traffic routing to the stable deployment
- re-run the health endpoint to confirm recovery
- record the incident and release decision in the deployment summary

## Terraform remote backend and locking

Terraform should use a remote S3 backend with DynamoDB locking. A template is provided at `terraform/backend.hcl.example`.

Example initialization:

```bash
terraform init -backend-config=backend.hcl
```

This prevents concurrent state mutation and ensures consistent environment drift control across dev, staging, and production.

## Database migration deployment gates and rollback strategy

For schema changes:
- Run migration SQL in lower environments first
- Validate health checks and smoke tests after each migration
- Require a manual approval gate before production execution
- Keep rollback SQL or reversible migration scripts for each change
- Record migration version metadata in the schema migration table

The migration manager in `src/migrations.py` tracks applied versions and supports rollback-oriented filenames and version metadata. Rollbacks should be executed only after verifying the production impact and confirming the target release window.

## Container image signing and provenance

The release workflow signs images using Sigstore/Cosign and enables provenance generation. This allows verification that the runtime image is the exact artifact promoted through CI.

## Monitoring hardening

Production alerting should be split by environment and routed to the right channels:
- `dev`: team notifications and operational debugging
- `staging`: deployment verification channel
- `production`: on-call escalation with pager-worthy severity thresholds

The monitoring stack in `monitoring/` should be treated as an environment-aware deployment target with separate alert route configuration and review of dashboard correctness before production promotion.

## Operational scripts

The repository includes operational helpers to support deployment execution and rollback safety.

### Health check script

Use the health check helper before and after deployment:

```bash
export DEPLOY_HEALTH_URL=https://staging.example.com
./scripts/health_check.sh
```

This script verifies that the endpoint responds and that the payload reports a healthy or warning state.

### Production rollback script

Use the rollback helper to revert to the last known-good release:

```bash
export PRODUCTION_HEALTH_URL=https://api.example.com
export ROLLBACK_COMMAND='echo "restore previous production image"'
./scripts/rollback_production.sh last-known-good-release
```

This script is designed as a safe rollback wrapper for production environments and can be integrated into incident response or release automation.

## Environment variable templates

The repository includes environment-specific templates for deployment secrets and app configuration:
- `.env.dev.example`
- `.env.staging.example`
- `.env.production.example`

Use these as starting points for local or CI/CD environment configuration, but never commit real secrets into the repo.

## Local Development Setup

### Prerequisites

- Python 3.10+
- Git
- `pip`
- Kaggle account with API credentials
- Optional: AWS CLI if you want to use the AWS upload helper

### Install dependencies

```bash
git clone https://github.com/Victor-Kipruto-Rop/cloud-etl-pipeline.git
cd cloud-etl-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p data/raw data/processed data/analytics
```

### Configure local environment

Copy the example environment file and review the `config/` directory for dataset and AWS settings:

```bash
cp .env.example .env
cat config/aws_config.yaml
cat config/domains.yaml
```

> Do not commit `.env` or Kaggle credentials to source control. Keep sensitive keys in local files only.

### Configure Kaggle credentials

Create `~/.kaggle/kaggle.json`:

```bash
mkdir -p ~/.kaggle
cat > ~/.kaggle/kaggle.json <<EOF
{
  "username": "YOUR_KAGGLE_USERNAME",
  "key": "YOUR_KAGGLE_KEY"
}
