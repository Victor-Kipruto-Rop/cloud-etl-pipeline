-- PostgreSQL raw landing table for the Olist orders CSV used by the sample dbt project.
-- Apply this DDL before enabling DATABASE_URL + TARGET_SCHEMA=raw + TARGET_TABLE=orders.

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.orders (
    order_id VARCHAR(64) PRIMARY KEY,
    customer_id VARCHAR(64) NOT NULL,
    order_status VARCHAR(32) NOT NULL,
    order_purchase_timestamp TIMESTAMPTZ,
    order_approved_at TIMESTAMPTZ,
    order_delivered_carrier_date TIMESTAMPTZ,
    order_delivered_customer_date TIMESTAMPTZ,
    order_estimated_delivery_date TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_raw_orders_customer_id
    ON raw.orders (customer_id);

CREATE INDEX IF NOT EXISTS ix_raw_orders_purchase_timestamp
    ON raw.orders (order_purchase_timestamp);
