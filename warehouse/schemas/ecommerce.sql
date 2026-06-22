-- E-commerce Data Warehouse - Star Schema
-- Brazilian E-commerce Dataset (Olist)
-- Drop and recreate tables with proper distribution and sort keys

-- Drop tables if exist
DROP TABLE IF EXISTS fact_orders CASCADE;
DROP TABLE IF EXISTS fact_order_items CASCADE;
DROP TABLE IF EXISTS dim_customers CASCADE;
DROP TABLE IF EXISTS dim_products CASCADE;
DROP TABLE IF EXISTS dim_sellers CASCADE;
DROP TABLE IF EXISTS dim_dates CASCADE;

-- Dimension: Customers
CREATE TABLE dim_customers (
    customer_sk VARCHAR(64) NOT NULL ENCODE lzo,
    customer_id VARCHAR(64) NOT NULL ENCODE lzo,
    customer_unique_id VARCHAR(64) ENCODE lzo,
    customer_zip_code_prefix VARCHAR(10) ENCODE lzo,
    customer_city VARCHAR(100) ENCODE lzo,
    customer_state VARCHAR(2) ENCODE lzo,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (customer_id)
)
DISTSTYLE KEY
DISTKEY (customer_id)
SORTKEY (customer_id);

-- Dimension: Products
CREATE TABLE dim_products (
    product_sk VARCHAR(64) NOT NULL ENCODE lzo,
    product_id VARCHAR(64) NOT NULL ENCODE lzo,
    product_category_name VARCHAR(100) ENCODE lzo,
    product_category_name_english VARCHAR(100) ENCODE lzo,
    product_name_length INTEGER ENCODE az64,
    product_description_length INTEGER ENCODE az64,
    product_photos_qty INTEGER ENCODE az64,
    product_weight_g DECIMAL(10,2) ENCODE az64,
    product_length_cm DECIMAL(10,2) ENCODE az64,
    product_height_cm DECIMAL(10,2) ENCODE az64,
    product_width_cm DECIMAL(10,2) ENCODE az64,
    product_volume_cm3 DECIMAL(15,2) ENCODE az64,
    product_size_category VARCHAR(20) ENCODE lzo,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (product_id)
)
DISTSTYLE KEY
DISTKEY (product_id)
SORTKEY (product_id);

-- Dimension: Sellers
CREATE TABLE dim_sellers (
    seller_sk VARCHAR(64) NOT NULL ENCODE lzo,
    seller_id VARCHAR(64) NOT NULL ENCODE lzo,
    seller_zip_code_prefix VARCHAR(10) ENCODE lzo,
    seller_city VARCHAR(100) ENCODE lzo,
    seller_state VARCHAR(2) ENCODE lzo,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (seller_id)
)
DISTSTYLE KEY
DISTKEY (seller_id)
SORTKEY (seller_id);

-- Dimension: Dates
CREATE TABLE dim_dates (
    date_id DATE NOT NULL ENCODE az64,
    year INTEGER ENCODE az64,
    quarter INTEGER ENCODE az64,
    month INTEGER ENCODE az64,
    month_name VARCHAR(10) ENCODE lzo,
    week INTEGER ENCODE az64,
    day INTEGER ENCODE az64,
    day_of_week INTEGER ENCODE az64,
    day_name VARCHAR(10) ENCODE lzo,
    is_weekend BOOLEAN ENCODE runlength,
    is_holiday BOOLEAN ENCODE runlength,
    PRIMARY KEY (date_id)
)
DISTSTYLE ALL
SORTKEY (date_id);

-- Fact: Orders
CREATE TABLE fact_orders (
    order_id VARCHAR(64) NOT NULL ENCODE lzo,
    customer_id VARCHAR(64) NOT NULL ENCODE lzo,
    order_status VARCHAR(20) ENCODE lzo,
    order_purchase_timestamp TIMESTAMP ENCODE az64,
    order_approved_at TIMESTAMP ENCODE az64,
    order_delivered_carrier_date TIMESTAMP ENCODE az64,
    order_delivered_customer_date TIMESTAMP ENCODE az64,
    order_estimated_delivery_date TIMESTAMP ENCODE az64,
    delivery_days INTEGER ENCODE az64,
    is_delayed BOOLEAN ENCODE runlength,
    order_year INTEGER ENCODE az64,
    order_month INTEGER ENCODE az64,
    order_quarter INTEGER ENCODE az64,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (order_id),
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id)
)
DISTSTYLE KEY
DISTKEY (customer_id)
SORTKEY (order_purchase_timestamp, order_year, order_month);

-- Fact: Order Items
CREATE TABLE fact_order_items (
    order_id VARCHAR(64) NOT NULL ENCODE lzo,
    order_item_id INTEGER NOT NULL ENCODE az64,
    product_id VARCHAR(64) NOT NULL ENCODE lzo,
    seller_id VARCHAR(64) NOT NULL ENCODE lzo,
    shipping_limit_date TIMESTAMP ENCODE az64,
    price DECIMAL(10,2) ENCODE az64,
    freight_value DECIMAL(10,2) ENCODE az64,
    total_value DECIMAL(10,2) ENCODE az64,
    order_year INTEGER ENCODE az64,
    order_month INTEGER ENCODE az64,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (order_id, order_item_id),
    FOREIGN KEY (order_id) REFERENCES fact_orders(order_id),
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id),
    FOREIGN KEY (seller_id) REFERENCES dim_sellers(seller_id)
)
DISTSTYLE KEY
DISTKEY (order_id)
SORTKEY (order_id, order_year, order_month);

-- Create indexes for better query performance
-- Note: Redshift doesn't support traditional indexes, sort keys are used instead

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO GROUP analytics_users;
GRANT ALL ON ALL TABLES IN SCHEMA public TO GROUP etl_users;

-- Analyze tables for query optimization
ANALYZE dim_customers;
ANALYZE dim_products;
ANALYZE dim_sellers;
ANALYZE dim_dates;
ANALYZE fact_orders;
ANALYZE fact_order_items;

-- Comments for documentation
COMMENT ON TABLE dim_customers IS 'Customer dimension table with geographic information';
COMMENT ON TABLE dim_products IS 'Product dimension table with category and physical attributes';
COMMENT ON TABLE dim_sellers IS 'Seller dimension table with geographic information';
COMMENT ON TABLE dim_dates IS 'Date dimension table for time-based analysis';
COMMENT ON TABLE fact_orders IS 'Order fact table with delivery metrics';
COMMENT ON TABLE fact_order_items IS 'Order items fact table with pricing details';
