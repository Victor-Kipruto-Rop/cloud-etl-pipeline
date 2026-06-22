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

3. Confirm ETL metrics are being scraped. By default `prometheus.yml` includes `host.docker.internal:8000` and `localhost:8000` as example ETL targets. If your ETL process exposes metrics on a different host/port, update `prometheus.yml`.

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
