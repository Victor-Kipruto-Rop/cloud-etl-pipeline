# Security policy

This repository follows a defense-in-depth security model for code, dependencies, secrets, container images, and release promotion.

## Scope

This policy applies to:
- application code in the repository
- Python dependencies and GitHub Actions updates
- Docker and container images built for deployment
- Terraform infrastructure configuration
- CI/CD workflows and release promotion to dev, staging, and production

## Required controls

### 1. Code scanning and review

- GitHub CodeQL must be enabled for the default branch and pull requests.
- Code scanning findings must be reviewed before merge to protected branches.
- High and critical code-scanning results must be fixed or explicitly accepted with documented risk.

### 2. Secret protection

- GitHub secret scanning and push protection must be enabled.
- Production secrets must never be stored in repository files or committed logs.
- Secrets must be supplied through GitHub Environment secrets, AWS Secrets Manager, or an equivalent secret store.
- Local development must use environment-specific templates such as `.env.dev.example`, `.env.staging.example`, and `.env.production.example`.

### 3. Dependency hygiene

- Dependabot security updates must be enabled for pip, GitHub Actions, and Docker.
- Dependency review must run for pull requests and block moderate-or-higher vulnerabilities when the policy is enforced.
- Dependency upgrades must be reviewed and merged through the standard PR process.

### 4. Container security

- Every container image built for release must be scanned with Trivy before promotion.
- Critical and high CVEs must be resolved before production deployment.
- The release pipeline must generate and verify an SBOM before moving an image into production.
- Container image provenance must be verified before deployment approval.

### 5. Infrastructure and deployment security

- Dockerfile policy checks must run in CI via Hadolint.
- Terraform posture checks must run via tfsec or equivalent policy tooling.
- Terraform and deployment changes must require review and approval before production rollout.
- Production deployments must go through dev -> staging -> production gates with explicit smoke tests and environment approval.
- Rollback must be possible and documented for failed production health checks.

### 6. Release requirements

Production promotion is allowed only when all of the following are true:
- CI is green
- CodeQL analysis is clean or accepted with documented risk
- secret scans are clean
- dependency review passes
- Trivy image scan passes
- SBOM and provenance checks pass
- Dockerfile and Terraform policy checks pass
- smoke tests on the target environment pass
- the designated environment approver confirms the release

## Exceptions

Exceptions may be granted only by a repository maintainer and must be documented in writing with:
- the affected system or dependency
- the risk being accepted
- the expiration date of the exception
- the mitigation steps in place

## Reporting

Security concerns should be reported privately to the repository maintainers through the GitHub security advisory flow or by contacting the project owner directly.

## Related files

- `.github/workflows/security.yml`
- `.github/workflows/release-promotion.yml`
- `.github/workflows/release-security-gate.yml`
- `.github/dependabot.yml`
- `scripts/health_check.sh`
- `scripts/rollback_production.sh`
