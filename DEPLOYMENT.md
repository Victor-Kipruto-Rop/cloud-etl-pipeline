# Deployment Guide

This repository is configured for local ETL development, dataset ingestion, and optional AWS upload helper usage.

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
