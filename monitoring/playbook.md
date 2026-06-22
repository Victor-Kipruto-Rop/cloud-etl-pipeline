# Alerting Playbook — ETL Pipeline

This playbook shows example Alertmanager receivers and steps to configure Slack and Email notifications.

1) Slack
  - Create an Incoming Webhook in Slack and copy the URL.
  - In `monitoring/alertmanager/alertmanager.yml` replace `https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK` with your webhook URL.
  - Configure the `channel` to the target channel (e.g. `#alerts`).

2) Email (SMTP)
  - Replace `smarthost`, `auth_username`, and `auth_password` in the `email_configs` block of `alertmanager.yml`.
  - Ensure your SMTP server allows relay from the Alertmanager host.

3) Common responses
  - If an alert fires about `etl_files_failed_total` increasing: check ETL logs, review quarantined files in `data/processed/quarantine`, and re-run the pipeline for the failed files.
  - If `etl_rows_loaded_total` drops near zero: verify the source feeds and check the transform step for failures.

4) Run locally
  - Start monitoring stack:

```bash
docker-compose -f monitoring/docker-compose.monitoring.yml up -d
```

  - Grafana: http://localhost:3000 (default admin/admin)
  - Prometheus: http://localhost:9090
  - Alertmanager: http://localhost:9093
