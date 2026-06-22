-- Finance Data Warehouse - Star Schema
-- US Stocks and ETFs Price/Volume Data
-- Drop and recreate tables with proper distribution and sort keys

-- Drop tables if exist
DROP TABLE IF EXISTS fact_stock_prices CASCADE;
DROP TABLE IF EXISTS dim_stocks CASCADE;
DROP TABLE IF EXISTS dim_exchanges CASCADE;
DROP TABLE IF EXISTS dim_dates CASCADE;

-- Dimension: Stocks
CREATE TABLE dim_stocks (
    stock_id VARCHAR(64) NOT NULL ENCODE lzo,
    ticker_symbol VARCHAR(10) NOT NULL ENCODE lzo,
    security_name VARCHAR(200) ENCODE lzo,
    security_type VARCHAR(20) ENCODE lzo,  -- Stock or ETF
    sector VARCHAR(100) ENCODE lzo,
    industry VARCHAR(100) ENCODE lzo,
    market_cap_category VARCHAR(20) ENCODE lzo,
    is_active BOOLEAN ENCODE runlength,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (stock_id)
)
DISTSTYLE ALL
SORTKEY (ticker_symbol);

-- Dimension: Exchanges
CREATE TABLE dim_exchanges (
    exchange_id VARCHAR(64) NOT NULL ENCODE lzo,
    exchange_code VARCHAR(10) NOT NULL ENCODE lzo,
    exchange_name VARCHAR(100) ENCODE lzo,
    country VARCHAR(50) ENCODE lzo,
    currency VARCHAR(3) ENCODE lzo,
    timezone VARCHAR(50) ENCODE lzo,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (exchange_id)
)
DISTSTYLE ALL
SORTKEY (exchange_code);

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
    is_trading_day BOOLEAN ENCODE runlength,
    PRIMARY KEY (date_id)
)
DISTSTYLE ALL
SORTKEY (date_id);

-- Fact: Stock Prices
CREATE TABLE fact_stock_prices (
    price_id VARCHAR(64) NOT NULL ENCODE lzo,
    stock_id VARCHAR(64) NOT NULL ENCODE lzo,
    exchange_id VARCHAR(64) ENCODE lzo,
    trade_date DATE NOT NULL ENCODE az64,
    trade_year INTEGER ENCODE az64,
    trade_month INTEGER ENCODE az64,
    trade_quarter INTEGER ENCODE az64,
    open_price DECIMAL(18,4) ENCODE az64,
    high_price DECIMAL(18,4) ENCODE az64,
    low_price DECIMAL(18,4) ENCODE az64,
    close_price DECIMAL(18,4) ENCODE az64,
    adjusted_close DECIMAL(18,4) ENCODE az64,
    volume BIGINT ENCODE az64,
    daily_return DECIMAL(10,6) ENCODE az64,
    price_change DECIMAL(18,4) ENCODE az64,
    price_change_pct DECIMAL(10,4) ENCODE az64,
    volume_change_pct DECIMAL(10,4) ENCODE az64,
    volatility DECIMAL(10,6) ENCODE az64,
    is_up_day BOOLEAN ENCODE runlength,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (price_id),
    FOREIGN KEY (stock_id) REFERENCES dim_stocks(stock_id),
    FOREIGN KEY (exchange_id) REFERENCES dim_exchanges(exchange_id)
)
DISTSTYLE KEY
DISTKEY (stock_id)
SORTKEY (trade_date, trade_year, trade_month);

-- Create aggregate table for monthly summaries
CREATE TABLE fact_stock_prices_monthly (
    stock_id VARCHAR(64) NOT NULL ENCODE lzo,
    trade_year INTEGER NOT NULL ENCODE az64,
    trade_month INTEGER NOT NULL ENCODE az64,
    month_open DECIMAL(18,4) ENCODE az64,
    month_high DECIMAL(18,4) ENCODE az64,
    month_low DECIMAL(18,4) ENCODE az64,
    month_close DECIMAL(18,4) ENCODE az64,
    total_volume BIGINT ENCODE az64,
    avg_daily_volume BIGINT ENCODE az64,
    monthly_return DECIMAL(10,6) ENCODE az64,
    trading_days INTEGER ENCODE az64,
    up_days INTEGER ENCODE az64,
    down_days INTEGER ENCODE az64,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    PRIMARY KEY (stock_id, trade_year, trade_month)
)
DISTSTYLE KEY
DISTKEY (stock_id)
SORTKEY (trade_year, trade_month, stock_id);

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO GROUP analytics_users;
GRANT ALL ON ALL TABLES IN SCHEMA public TO GROUP etl_users;

-- Analyze tables
ANALYZE dim_stocks;
ANALYZE dim_exchanges;
ANALYZE dim_dates;
ANALYZE fact_stock_prices;
ANALYZE fact_stock_prices_monthly;

-- Comments
COMMENT ON TABLE dim_stocks IS 'Stock and ETF dimension with security details';
COMMENT ON TABLE dim_exchanges IS 'Exchange dimension with trading venue information';
COMMENT ON TABLE fact_stock_prices IS 'Daily stock price fact table with OHLCV data';
COMMENT ON TABLE fact_stock_prices_monthly IS 'Monthly aggregated stock prices';
