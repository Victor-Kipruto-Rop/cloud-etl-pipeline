-- Migration: Initialize schema
-- Version: 20240101_000000_init_schema

-- Up migration
CREATE TABLE IF NOT EXISTS cars (
    id SERIAL PRIMARY KEY,
    make VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dealers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales (
    id SERIAL PRIMARY KEY,
    car_id INTEGER REFERENCES cars(id),
    dealer_id INTEGER REFERENCES dealers(id),
    price DECIMAL(10, 2),
    sale_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cars_make_model ON cars(make, model);
CREATE INDEX idx_sales_car_id ON sales(car_id);
CREATE INDEX idx_sales_dealer_id ON sales(dealer_id);

-- Down migration (for rollback)
DROP TABLE IF EXISTS sales CASCADE;
DROP TABLE IF EXISTS dealers CASCADE;
DROP TABLE IF EXISTS cars CASCADE;
