-- Climate Data Warehouse - Star Schema
-- Global Temperature Data from Berkeley Earth
-- Drop and recreate tables with proper distribution and sort keys

-- Drop tables if exist
DROP TABLE IF EXISTS fact_temperatures CASCADE;
DROP TABLE IF EXISTS dim_locations CASCADE;
DROP TABLE IF EXISTS dim_countries CASCADE;
DROP TABLE IF EXISTS dim_dates CASCADE;

-- Dimension: Locations
CREATE TABLE dim_locations (
    location_id VARCHAR(64) NOT NULL ENCODE lzo,
    city VARCHAR(200) ENCODE lzo,
    state VARCHAR(100) ENCODE lzo,
    country VARCHAR(100) ENCODE lzo,
    latitude DECIMAL(10,6) ENCODE az64,
    longitude DECIMAL(10,6) ENCODE az64,
    continent VARCHAR(50) ENCODE lzo,
    region VARCHAR(100) ENCODE lzo,
    climate_zone VARCHAR(50) ENCODE lzo,
    elevation_meters INTEGER ENCODE az64,
    population INTEGER ENCODE az64,
    is_coastal BOOLEAN ENCODE runlength,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (location_id)
)
DISTSTYLE ALL
SORTKEY (location_id, country);

-- Dimension: Countries
CREATE TABLE dim_countries (
    country_id VARCHAR(64) NOT NULL ENCODE lzo,
    country_name VARCHAR(100) NOT NULL ENCODE lzo,
    country_code VARCHAR(3) ENCODE lzo,
    continent VARCHAR(50) ENCODE lzo,
    region VARCHAR(100) ENCODE lzo,
    subregion VARCHAR(100) ENCODE lzo,
    total_area_km2 DECIMAL(15,2) ENCODE az64,
    land_area_km2 DECIMAL(15,2) ENCODE az64,
    population BIGINT ENCODE az64,
    gdp_usd BIGINT ENCODE az64,
    development_level VARCHAR(50) ENCODE lzo,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (country_id)
)
DISTSTYLE ALL
SORTKEY (country_name);

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
    decade INTEGER ENCODE az64,
    century INTEGER ENCODE az64,
    PRIMARY KEY (date_id)
)
DISTSTYLE ALL
SORTKEY (date_id);

-- Fact: Temperatures
CREATE TABLE fact_temperatures (
    measurement_id VARCHAR(64) NOT NULL ENCODE lzo,
    location_id VARCHAR(64) NOT NULL ENCODE lzo,
    country_id VARCHAR(64) ENCODE lzo,
    measurement_date DATE ENCODE az64,
    measurement_year INTEGER ENCODE az64,
    measurement_month INTEGER ENCODE az64,
    measurement_decade INTEGER ENCODE az64,
    avg_temperature DECIMAL(8,3) ENCODE az64,
    avg_temperature_uncertainty DECIMAL(8,3) ENCODE az64,
    min_temperature DECIMAL(8,3) ENCODE az64,
    max_temperature DECIMAL(8,3) ENCODE az64,
    temperature_celsius DECIMAL(8,3) ENCODE az64,
    temperature_fahrenheit DECIMAL(8,3) ENCODE az64,
    temperature_anomaly DECIMAL(8,3) ENCODE az64,  -- Deviation from baseline
    is_above_average BOOLEAN ENCODE runlength,
    is_record_high BOOLEAN ENCODE runlength,
    is_record_low BOOLEAN ENCODE runlength,
    data_quality_flag VARCHAR(10) ENCODE lzo,
    measurement_source VARCHAR(50) ENCODE lzo,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (measurement_id),
    FOREIGN KEY (location_id) REFERENCES dim_locations(location_id),
    FOREIGN KEY (country_id) REFERENCES dim_countries(country_id)
)
DISTSTYLE KEY
DISTKEY (location_id)
SORTKEY (measurement_date, measurement_year, measurement_month);

-- Create aggregate table for yearly averages
CREATE TABLE fact_temperatures_yearly (
    location_id VARCHAR(64) NOT NULL ENCODE lzo,
    country_id VARCHAR(64) ENCODE lzo,
    measurement_year INTEGER NOT NULL ENCODE az64,
    measurement_decade INTEGER ENCODE az64,
    avg_annual_temperature DECIMAL(8,3) ENCODE az64,
    min_annual_temperature DECIMAL(8,3) ENCODE az64,
    max_annual_temperature DECIMAL(8,3) ENCODE az64,
    temperature_range DECIMAL(8,3) ENCODE az64,
    temperature_variance DECIMAL(10,4) ENCODE az64,
    warmest_month INTEGER ENCODE az64,
    coldest_month INTEGER ENCODE az64,
    warming_trend DECIMAL(10,6) ENCODE az64,
    data_completeness_pct DECIMAL(5,2) ENCODE az64,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    PRIMARY KEY (location_id, measurement_year)
)
DISTSTYLE KEY
DISTKEY (location_id)
SORTKEY (measurement_year, location_id);

-- Create aggregate table for global averages
CREATE TABLE fact_global_temperatures (
    measurement_date DATE NOT NULL ENCODE az64,
    measurement_year INTEGER ENCODE az64,
    measurement_month INTEGER ENCODE az64,
    global_land_avg_temp DECIMAL(8,3) ENCODE az64,
    global_land_max_temp DECIMAL(8,3) ENCODE az64,
    global_land_min_temp DECIMAL(8,3) ENCODE az64,
    global_land_ocean_avg_temp DECIMAL(8,3) ENCODE az64,
    global_avg_temp_uncertainty DECIMAL(8,3) ENCODE az64,
    northern_hemisphere_avg DECIMAL(8,3) ENCODE az64,
    southern_hemisphere_avg DECIMAL(8,3) ENCODE az64,
    tropical_avg DECIMAL(8,3) ENCODE az64,
    decade_avg DECIMAL(8,3) ENCODE az64,
    century_avg DECIMAL(8,3) ENCODE az64,
    warming_acceleration DECIMAL(10,6) ENCODE az64,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    PRIMARY KEY (measurement_date)
)
DISTSTYLE ALL
SORTKEY (measurement_date);

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO GROUP analytics_users;
GRANT ALL ON ALL TABLES IN SCHEMA public TO GROUP etl_users;

-- Analyze tables
ANALYZE dim_locations;
ANALYZE dim_countries;
ANALYZE dim_dates;
ANALYZE fact_temperatures;
ANALYZE fact_temperatures_yearly;
ANALYZE fact_global_temperatures;

-- Comments
COMMENT ON TABLE dim_locations IS 'Geographic location dimension with climate zones';
COMMENT ON TABLE dim_countries IS 'Country dimension with geographic and demographic data';
COMMENT ON TABLE fact_temperatures IS 'Temperature measurement fact table';
COMMENT ON TABLE fact_temperatures_yearly IS 'Yearly aggregated temperature statistics';
COMMENT ON TABLE fact_global_temperatures IS 'Global temperature averages and trends';
