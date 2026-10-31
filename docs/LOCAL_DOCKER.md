# Local Docker Development

This setup runs PostgreSQL and the ETL project locally without installing Python
dependencies on the host. It is intended for development and testing, not as a
production deployment definition.

## Prerequisites

- Docker Engine with the Docker Compose v2 plugin, or Docker Desktop
- Git
- At least 4 GB of available memory recommended

## First-time setup

Linux / macOS:

```bash
cp .env.example .env
mkdir -p data/raw data/processed data/analytics logs
docker compose build
docker compose up -d db
docker compose ps
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
New-Item -ItemType Directory -Force data/raw, data/processed, data/analytics, logs
docker compose build
docker compose up -d db
docker compose ps
```

The PostgreSQL service is available to containers as `db:5432` and from the
host as `localhost:5432`. The default local credentials are deliberately
development-only. Do not reuse them outside a local machine.

## Run the ETL pipeline

Place one or more CSV files in `data/raw/`, then run:

```bash
docker compose run --rm etl
```

The container writes processed files to `data/processed/` and logs to
`logs/`. These directories are bind-mounted, so outputs remain on the host
after the container exits.

To run the incremental medallion path, set
`MEDALLION_PIPELINE_ENABLED=true` in your local `.env` file. The default
metadata database is SQLite under `data/metadata/`, which is persisted by the
data bind mount.

## Interactive development shell

Build and open the development container:

```bash
docker compose --profile dev run --rm dev
```

Inside the container:

```bash
python -m pytest -q
python -m compileall -q src ingest etl tests dags
python -m src.pipeline
```

The repository is mounted at `/workspace`, so edits made on the host are
immediately visible in the container.

## Run tests against local PostgreSQL

Start the database, then run pytest in the development container:

```bash
docker compose up -d db
docker compose --profile dev run --rm -e POSTGRES_HOST=db -e TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/etl_db dev python -m pytest --ignore=tests/test_perf_copy.py -q
```

## Stop and clean up

```bash
docker compose down
```

To also delete the local PostgreSQL volume (this permanently deletes the
containerized development database):

```bash
docker compose down -v
```

## Credentials and data safety

- Never commit `.env`, Kaggle credentials, AWS credentials, or real customer data.
- Keep local datasets in `data/`; the Docker build context excludes this directory.
- Use separate non-production credentials for any external service integration.
- Do not run Terraform apply or connect this local stack to production resources.
