-- Healthcare Data Warehouse - Star Schema
-- Heart Disease UCI Dataset
-- Drop and recreate tables with proper distribution and sort keys

-- Drop tables if exist
DROP TABLE IF EXISTS fact_diagnoses CASCADE;
DROP TABLE IF EXISTS dim_patients CASCADE;
DROP TABLE IF EXISTS dim_medical_tests CASCADE;
DROP TABLE IF EXISTS dim_dates CASCADE;

-- Dimension: Patients
CREATE TABLE dim_patients (
    patient_id VARCHAR(64) NOT NULL ENCODE lzo,
    age INTEGER ENCODE az64,
    age_group VARCHAR(20) ENCODE lzo,
    sex INTEGER ENCODE az64,
    sex_description VARCHAR(10) ENCODE lzo,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (patient_id)
)
DISTSTYLE ALL
SORTKEY (patient_id, age_group);

-- Dimension: Medical Tests
CREATE TABLE dim_medical_tests (
    test_id VARCHAR(64) NOT NULL ENCODE lzo,
    chest_pain_type INTEGER ENCODE az64,
    chest_pain_description VARCHAR(50) ENCODE lzo,
    resting_ecg INTEGER ENCODE az64,
    resting_ecg_description VARCHAR(50) ENCODE lzo,
    exercise_angina INTEGER ENCODE az64,
    slope INTEGER ENCODE az64,
    slope_description VARCHAR(50) ENCODE lzo,
    thal INTEGER ENCODE az64,
    thal_description VARCHAR(50) ENCODE lzo,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (test_id)
)
DISTSTYLE ALL
SORTKEY (test_id);

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

-- Fact: Diagnoses
CREATE TABLE fact_diagnoses (
    diagnosis_id VARCHAR(64) NOT NULL ENCODE lzo,
    patient_id VARCHAR(64) NOT NULL ENCODE lzo,
    test_id VARCHAR(64) NOT NULL ENCODE lzo,
    diagnosis_date DATE ENCODE az64,
    diagnosis_year INTEGER ENCODE az64,
    trestbps INTEGER ENCODE az64,  -- resting blood pressure
    chol INTEGER ENCODE az64,      -- serum cholesterol mg/dl
    fbs INTEGER ENCODE az64,       -- fasting blood sugar > 120 mg/dl
    thalach INTEGER ENCODE az64,   -- maximum heart rate achieved
    exang INTEGER ENCODE az64,     -- exercise induced angina
    oldpeak DECIMAL(5,2) ENCODE az64,  -- ST depression
    ca INTEGER ENCODE az64,        -- number of major vessels
    target INTEGER ENCODE az64,    -- diagnosis (0=no disease, 1=disease)
    has_heart_disease BOOLEAN ENCODE runlength,
    risk_level VARCHAR(20) ENCODE lzo,
    etl_insert_timestamp TIMESTAMP ENCODE az64,
    etl_update_timestamp TIMESTAMP ENCODE az64,
    etl_batch_id VARCHAR(20) ENCODE lzo,
    PRIMARY KEY (diagnosis_id),
    FOREIGN KEY (patient_id) REFERENCES dim_patients(patient_id),
    FOREIGN KEY (test_id) REFERENCES dim_medical_tests(test_id)
)
DISTSTYLE KEY
DISTKEY (patient_id)
SORTKEY (diagnosis_date, diagnosis_year);

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO GROUP analytics_users;
GRANT ALL ON ALL TABLES IN SCHEMA public TO GROUP etl_users;

-- Analyze tables
ANALYZE dim_patients;
ANALYZE dim_medical_tests;
ANALYZE dim_dates;
ANALYZE fact_diagnoses;

-- Comments
COMMENT ON TABLE dim_patients IS 'Patient dimension with demographic information';
COMMENT ON TABLE dim_medical_tests IS 'Medical test types and descriptions';
COMMENT ON TABLE fact_diagnoses IS 'Diagnosis fact table with heart disease indicators';
