# ETL Dashboard Summary

This project now generates a visual dashboard automatically after the ETL pipeline completes.

## Generated artifacts

- `visualizations/dashboard.html`
- `visualizations/state_distribution.png`
- `visualizations/condition_distribution.png`
- `visualizations/sales_condition_distribution.png`
- `visualizations/selling_price_vs_mmr.png`
- `visualizations/top_10_dealers_by_sales.png`
- `visualizations/top_sellers.png`

## What it includes

- state-level distribution of processed car price records
- condition distribution for sales records
- relationship between MMR and selling price
- top sellers by processed record count

## How it works

When the pipeline runs, it reads processed CSV output from `data/processed/` and generates dashboard charts in `visualizations/`.
The HTML report `visualizations/dashboard.html` includes embedded chart images and a short summary of the processed dataset.
