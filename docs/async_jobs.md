# Async Job API — Examples

The service exposes endpoints to submit asynchronous pipeline jobs, poll status, fetch results, and cancel.

Authentication
- Set environment variable `ADMIN_API_KEY` in production. Use the header `Authorization: Bearer <API_KEY>` or `X-Api-Key: <API_KEY>` for privileged endpoints.

Submit a job

```bash
curl -X POST https://your-host/api/v1/pipeline/jobs \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"pipeline-run","params":{},"timeout":3600}'
# returns 202 with {"status":"queued","job_id":"job-000001"}
```

Check status

```bash
curl https://your-host/api/v1/pipeline/jobs/job-000001
# returns job JSON with status and timestamps
```

Get result

```bash
curl https://your-host/api/v1/pipeline/jobs/job-000001/result
# returns 202 if running, or 200 with result when completed
```

Cancel job (best-effort cooperative cancel)

```bash
curl -X POST https://your-host/api/v1/pipeline/jobs/job-000001/cancel \
  -H "Authorization: Bearer $ADMIN_API_KEY"
# returns 200 if cancelled, 409 if could not cancel
```

Dashboard wiring
- You can add buttons in your dashboard that call the submit endpoint (via a small server-side proxy or with credentials). Prefer server-side actions to avoid exposing the API key.
