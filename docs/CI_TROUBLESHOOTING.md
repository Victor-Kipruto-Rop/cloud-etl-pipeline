# GitHub Actions troubleshooting

## Distinguish workflow errors from runner-allocation failures

A workflow job with `runner_id: 0`, an empty `runner_name`, no startable steps,
and a completion time only seconds after dispatch did not execute on a GitHub-hosted
runner. This is not evidence that a Python test, Terraform command, or Docker build
failed. The job logs may also be unavailable because no runner produced them.

For this repository, inspect the following before changing workflow commands:

1. Open **Settings → Actions → General** and confirm GitHub Actions is enabled
   for the repository and the permitted actions policy allows the actions used
   by the workflow.
2. Open **Billing and licensing → Usage** for the account that owns the repository.
   Check whether GitHub Actions minutes or spending limits prevent hosted jobs.
3. Open the workflow run and inspect each job's runner assignment, start time,
   steps, and logs. A job with no runner and no steps needs an account/repository
   Actions configuration investigation, not a source-code workaround.
4. Check GitHub Status for an Actions incident before repeatedly re-running jobs.
5. Once runner allocation is restored, use **Actions → CI Pipeline → Run workflow**
   to run the complete test and Terraform checks on the selected branch.
6. Re-run only failed jobs when logs show a transient infrastructure failure.
   Fix actual command/test failures in code and run the workflow again.

## Workflow entry points

- Pull requests into `main` or `develop` run the test and Terraform checks.
- Pushes to `main` additionally run the Docker build/configuration check.
- Pushes and scheduled runs include the separately gated performance job.
- Manual dispatch is available for an explicit verification run.

## Local checks

From the repository root, install `requirements.txt` and run:

```bash
python -m compileall -q src ingest etl tests dags
black --check src tests
isort --check-only src tests
flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics
pytest -q --ignore=tests/test_perf_copy.py --cov=src --cov-report=term-missing
terraform fmt -check -recursive infra/aws/data_lake
cd infra/aws/data_lake
terraform init -backend=false
terraform validate
```

The performance test is intentionally separate and requires a reachable PostgreSQL
instance or a working Docker/Testcontainers environment. Terraform validation does
not create cloud resources. Do not run `terraform apply` until the bucket name,
IAM role, account, region, retention, and cost implications have been reviewed.
