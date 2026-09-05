# Monitoring quickstart

This folder contains example configs to run a local Prometheus + Grafana + Alertmanager stack for the ETL pipeline.

Quickstart
1. Start the stack:

```bash
docker-compose -f monitoring/docker-compose.monitoring.yml up -d
```

2. Visit the services:
- Grafana: http://localhost:3000 (default admin/admin)
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093

3. Confirm ETL metrics are being scraped. By default `prometheus.yml` includes `host.docker.internal:8000`, `localhost:8000`, and `172.17.0.1:8000` as example ETL targets. If your ETL process exposes metrics on a different host/port, update `prometheus.yml`.

4. Start the ETL pipeline with metrics enabled by setting `METRICS_PORT`. For example:

```bash
METRICS_PORT=8000 .venv/bin/python3 -m src.pipeline
```

The pipeline exposes Prometheus metrics on the configured port when `METRICS_PORT` is set.

Current ETL metric names:
- `etl_files_processed_total`
- `etl_files_failed_total`
- `etl_rows_extracted_total`
- `etl_rows_loaded_total`
- `etl_current_in_progress`

Provisioned dashboards
- `etl-dashboard.json` — ETL-specific counters: files processed, files failed, rows loaded rate.
- `cpu-dashboard.json` — Example CPU usage panels (uses `node_exporter` metrics).
- `memory-dashboard.json` — Example memory usage panels (uses `node_exporter` metrics).

Alerting
- `alertmanager/alertmanager.yml` contains example Slack and email receivers. Update webhook URL and SMTP settings before production use.
- `alert_rules.yml` is included and referenced by `prometheus.yml`.

Troubleshooting
- Grafana shows no dashboards: check that Grafana provisioning path is mounted and `prometheus` datasource is reachable at `http://prometheus:9090`.
- Alerts not delivered: verify `alertmanager` is reachable and receivers are configured with correct credentials/webhooks.
- Testcontainers-based tests failing locally: ensure Docker is running and your user can run containers.

Security
- Do NOT commit real Slack webhooks, SMTP passwords, or other secrets. Use environment variables or a secret manager in CI/CD.

Production hardening
- Separate Grafana/Prometheus/Alertmanager configuration by environment to avoid dev alert noise in production pages.
- Route production alerts to on-call responders and use severity labels with explicit escalation rules.
- Validate dashboard queries against real target names before promoting to production.
- Treat alert suppression windows as an operational process with owners and expiry dates.
- Ensure health and smoke checks back the deployment promotion workflow before approving production releases.

Grafana dashboard import and recommendations

- Purpose: import `grafana-dashboard-import.json` into Grafana to visualize ETL SLOs, freshness, and latency.

Quick import (UI):
1. Grafana → Dashboards → Manage → Import
2. Upload `monitoring/grafana-dashboard-import.json`
3. Select Prometheus datasource used by this project and import.

Quick import (API):
```bash
export GRAFANA_URL="https://grafana.example.com"
export GRAFANA_API_KEY="<api-key>"
curl -s -H "Content-Type: application/json" -H "Authorization: Bearer $GRAFANA_API_KEY" \
	-X POST "$GRAFANA_URL/api/dashboards/db" \
	--data-binary @monitoring/grafana-dashboard-import.json
```

Recommended panel settings:
- Dashboard refresh: `30s` or `1m` for near-real-time freshness and latency.
- Time picker: set to `Last 30 days` when evaluating SLO Compliance panels.
- Template variables: add a `source` variable (Prometheus label) to filter `Freshness by Source`.

Prometheus metrics expected:
- `etl_files_processed_total`
- `etl_files_failed_total`
- `etl_current_in_progress`
- `etl_rows_loaded_total`
- `etl_rows_extracted_total`
- `etl_last_successful_run_timestamp_seconds`
- `etl_pipeline_latency_seconds_bucket`

Notes:
- The JSON is import-ready; panel IDs and grid positions are set for a 24-column layout.
- Adjust thresholds in Grafana if your SLO target differs from 99%.
