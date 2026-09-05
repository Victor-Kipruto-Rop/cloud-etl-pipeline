# GitHub settings checklist for advanced security

Use this checklist in the GitHub UI to enable the protection gates required by this repository.

## 1. Repository security settings

### Security and analysis

In GitHub go to: Repository -> Settings -> Security & analysis

- [ ] Enable GitHub Advanced Security for this repository
- [ ] Enable secret scanning
- [ ] Enable push protection for secret scanning
- [ ] Enable Dependabot alerts
- [ ] Enable Dependabot security updates
- [ ] Enable private vulnerability reporting if desired

### Code scanning

- [ ] Enable CodeQL analysis
- [ ] Set the default branch to run CodeQL on push and pull request
- [ ] Ensure CodeQL is configured for Python
- [ ] Review and resolve high/critical findings before merging to protected branches

## 2. Branch protection rules

In GitHub go to: Repository -> Settings -> Branches

- [ ] Protect the `main` branch
- [ ] Require a pull request before merging
- [ ] Require status checks to pass before merging
- [ ] Require branches to be up to date before merging
- [ ] Require review from at least one approving reviewer
- [ ] Require conversation resolution before merge
- [ ] Require deployment review for production releases

Required status checks to include:
- [ ] CI / test
- [ ] Security scanning / CodeQL analysis
- [ ] Security scanning / dependency review
- [ ] Security scanning / secret scan
- [ ] Security scanning / Trivy filesystem scan
- [ ] Dockerfile policy check
- [ ] Terraform security posture

## 3. GitHub environments

In GitHub go to: Repository -> Settings -> Environments

Create and configure:
- [ ] `dev`
- [ ] `staging`
- [ ] `production`

For each environment:
- [ ] Add environment protection rules as needed
- [ ] Add required reviewers for production
- [ ] Add environment secrets and variables required by the deployment workflow
- [ ] Configure deployment branch restrictions

Production environment requirements:
- [ ] Require approval before deployment
- [ ] Require successful smoke-test health validation
- [ ] Require SBOM/provenance verification
- [ ] Require Trivy scan success

## 4. Actions permissions

In GitHub go to: Repository -> Settings -> Actions -> General

- [ ] Set Actions permissions to "Read and write permissions" only if required for deployment
- [ ] Restrict GitHub Actions to specific repositories if using organizational policies
- [ ] Ensure workflow permissions include `contents: read` and required write access for packages or deployments
- [ ] Disable unnecessary workflow permissions for the least-privilege model

## 5. Dependabot and updates

In GitHub go to: Repository -> Settings -> Security & analysis -> Dependabot

- [ ] Enable Dependabot alerts
- [ ] Enable Dependabot security updates
- [ ] Confirm the configuration in `.github/dependabot.yml` is in place

## 6. Container registry and package policies

In GitHub go to: Packages or GHCR settings

- [ ] Ensure GitHub Container Registry is enabled for the repository
- [ ] Confirm package visibility aligns with the deployment model
- [ ] Verify the release workflow can push to the GHCR package for the project

## 7. Release validation checklist

Before production release, confirm:
- [ ] CI passes
- [ ] CodeQL passes
- [ ] Secret scanning passes
- [ ] Dependency review passes
- [ ] Trivy image scan passes
- [ ] SBOM and provenance are present
- [ ] Dockerfile policy passes
- [ ] Terraform security posture passes
- [ ] smoke tests pass against the target environment
- [ ] production approver has signed off
- [ ] rollback plan is ready

## 8. Optional hardening

When the project matures, consider:
- [ ] required security review for Terraform changes
- [ ] mandatory signed commits
- [ ] SAML or org-level enforcement for CI runners
- [ ] branch protections for staging and release branches
- [ ] deployment approval policies tied to security findings

## Quick enablement priority order

1. Enable GitHub Advanced Security and secret scanning
2. Protect `main` with required checks
3. Create `dev`, `staging`, and `production` environments with approval rules
4. Turn on CodeQL and Dependabot
5. Validate release gate workflows with a test image
6. Promote to production only after all security gates pass
