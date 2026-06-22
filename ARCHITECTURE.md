# Architecture Documentation

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ETL Pipeline Architecture                     │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   Data Sources   │
│   (CSV Files)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│   EXTRACT LAYER              │
│  ┌────────────────────────┐  │
│  │ • CSV Reader           │  │
│  │ • Encoding Detection   │  │
│  │ • Error Handling       │  │
│  └────────────────────────┘  │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│   TRANSFORM LAYER            │
│  ┌────────────────────────┐  │
│  │ • Column Normalization │  │
│  │ • Data Cleaning        │  │
│  │ • Type Conversion      │  │
│  │ • Deduplication        │  │
│  └────────────────────────┘  │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│   LOAD LAYER                 │
│  ┌────────────────────────┐  │
│  │ • Batch Insert         │  │
│  │ • Connection Pooling   │  │
│  │ • Error Handling       │  │
│  └────────────────────────┘  │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────┐
│   PostgreSQL     │
│   Database       │
└──────────────────┘

┌──────────────────────────────────────────┐
│        Supporting Infrastructure          │
├──────────────────────────────────────────┤
│ • Logging (File & Console)               │
│ • Health Checks                          │
│ • Configuration Management               │
│ • Error Handling & Retries               │
│ • Performance Monitoring                 │
│ • REST API & Scheduler                   │
│ • Database Migrations                    │
│ • Data Validation                        │
└──────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Extract Layer (`src/extract/extract_data.py`)

**Responsibilities:**
- Read CSV files from `data/raw/`
- Detect and handle encoding automatically
- Validate file structure
- Handle large files with streaming

**Features:**
- Automatic encoding detection (UTF-8, UTF-16, Latin-1, etc.)
- Error handling with custom ExtractionError
- Logging of extraction metrics
- Support for custom delimiters

**Flow:**
```
CSV File → Detect Encoding → Read Data → Validate → Return DataFrame
```

---

### 2. Transform Layer (`src/transform/transform_data.py`)

**Responsibilities:**
- Normalize column names (snake_case, lowercase)
- Clean and validate data
- Handle missing values
- Deduplicate records
- Convert data types

**Features:**
- Column name normalization
- Removal of special characters
- Type inference and conversion
- Duplicate row removal
- Logging of transformation stats

**Flow:**
```
DataFrame → Normalize Columns → Clean Data → Deduplicate → Type Conversion → Validated DataFrame
```

---

### 3. Load Layer (`src/load/load_to_db.py`)

**Responsibilities:**
- Connect to PostgreSQL database
- Create tables if needed
- Insert data in batches
- Handle connection pooling
- Retry on failure

**Features:**
- Connection pooling for performance
- Batch insert for efficiency
- Automatic table creation
- Error handling and retries
- Transaction management

**Flow:**
```
DataFrame → Prepare Data → Batch Insert → Commit → Log Results
```

---

### 4. Configuration Management (`src/config.py`)

**Responsibilities:**
- Load environment variables from `.env`
- Validate configuration
- Provide access to settings
- Support different environments
- Support optional AWS helper configuration via `config/aws_config.yaml` and dataset definitions in `config/domains.yaml`

**Key Classes:**
- `DatabaseConfig`: Database connection settings
- `PipelineConfig`: Pipeline execution settings
- `Config`: Main configuration container

---

### 5. Health Checks (`src/health.py`)

**Responsibilities:**
- Check database connectivity
- Verify file system accessibility
- Validate dependencies
- Generate status reports

**Checks:**
1. Database health
2. File system availability
3. Dependencies installation

---

### 6. Migrations (`src/migrations.py`)

**Responsibilities:**
- Track schema versions
- Apply migrations safely
- Support rollbacks
- Maintain migration history

**Features:**
- Version tracking
- Execution time logging
- Rollback support
- Migration status reporting

---

### 7. Logging Configuration (`src/logging_config.py`)

**Responsibilities:**
- Configure logging for the application
- Manage log rotation
- Validate logging setup
- Provide logger instances

**Log Files:**
- `logs/pipeline.log`: All logs
- `logs/errors.log`: Error logs only

---

### 8. REST API & Scheduler (`src/api.py`)

**Responsibilities:**
- Provide REST endpoints for pipeline control
- Schedule periodic executions
- Report pipeline status
- Expose health information

**Endpoints:**
- `GET /health`: Health check
- `POST /api/v1/pipeline/run`: Trigger pipeline
- `GET /api/v1/pipeline/status`: Pipeline status
- `GET /api/v1/pipeline/config`: Configuration
- `POST /api/v1/scheduler/schedule`: Schedule execution

---

## Data Flow

### Complete ETL Flow

```
1. INITIALIZATION
   └─ Load configuration from .env
   └─ Initialize logging
   └─ Run health checks
   └─ Apply database migrations

2. EXTRACTION PHASE
   └─ Scan data/raw/ for CSV files
   └─ Read each file with encoding detection
   └─ Collect statistics (rows, columns)

3. TRANSFORMATION PHASE
   └─ Normalize column names
   └─ Clean and validate data
   └─ Remove duplicates
   └─ Convert data types
   └─ Save to data/processed/

4. LOADING PHASE
   └─ Connect to PostgreSQL
   └─ Create/verify tables
   └─ Batch insert data
   └─ Commit transactions

5. REPORTING
   └─ Log final statistics
   └─ Report errors
   └─ Generate audit trail

6. CLEANUP
   └─ Close database connections
   └─ Finalize logs
```

---

## Database Schema

### Tables

```sql
-- cars table
CREATE TABLE cars (
    id SERIAL PRIMARY KEY,
    make VARCHAR(255),
    model VARCHAR(255),
    year INTEGER
);

-- dealers table
CREATE TABLE dealers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    location VARCHAR(255)
);

-- sales table
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    car_id INTEGER REFERENCES cars(id),
    dealer_id INTEGER REFERENCES dealers(id),
    price DECIMAL(10, 2),
    sale_date DATE
);

-- schema_migrations table (for migration tracking)
CREATE TABLE schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(255) UNIQUE,
    description TEXT,
    installed_on TIMESTAMP,
    execution_time_ms INTEGER
);
```

---

## Deployment Architecture

### Docker Compose Setup

```yaml
Services:
1. db (PostgreSQL 15)
   - Persistent volume for data
   - Environment variables for config
   - Health checks

2. etl (Python Application)
   - Depends on db service
   - Mounts data volumes
   - Runs pipeline on startup
```

---

## Error Handling Strategy

```
┌─────────────────────┐
│ Error Occurs        │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ Log Error    │
    └──────┬───────┘
           │
           ▼
    ┌────────────────────┐
    │ Retry? (if < max)  │
    └─────┬──────────┬───┘
          │ Yes      │ No
          │          ▼
          │     ┌─────────────┐
          │     │ Report Error│
          │     └─────┬───────┘
          │           │
          └───────┬───┘
                  │
                  ▼
         ┌────────────────┐
         │ Continue/Stop  │
         └────────────────┘
```

---

## Performance Considerations

### Optimization Strategies

1. **Chunked Processing**
   - Default: 10,000 rows per chunk
   - Configurable via `CHUNK_SIZE`

2. **Connection Pooling**
   - Reuses database connections
   - Reduces connection overhead

3. **Batch Inserts**
   - Groups multiple rows
   - Reduces database round trips

4. **Parallel Processing** (Future)
   - Process multiple files concurrently
   - Utilize multi-core systems

---

## Monitoring & Observability

### Metrics Tracked

- Files processed
- Rows extracted/transformed/loaded
- Execution time
- Error count
- Memory usage
- Database response time

### Log Levels

- **DEBUG**: Detailed execution information
- **INFO**: General progress and statistics
- **WARNING**: Recoverable issues
- **ERROR**: Unrecoverable errors
- **CRITICAL**: System failures

---

## Security Considerations

1. **Database Credentials**
   - Stored in `.env` (not in version control)
   - Use strong passwords
   - Consider encrypted secrets in production

2. **File Permissions**
   - Data directories protected from unauthorized access
   - Log files contain sensitive information

3. **Input Validation**
   - CSV files validated before processing
   - SQL injection prevention via parameterized queries

4. **API Security** (Future)
   - Authentication/authorization
   - Rate limiting
   - HTTPS/TLS encryption

---

## Scaling Considerations

### For Larger Datasets

1. **Partition Data**
   - Split files by source system
   - Process in parallel

2. **Optimize Database**
   - Add indexes on key columns
   - Use partitioned tables

3. **Infrastructure**
   - Use Kubernetes for orchestration
   - Distribute across multiple nodes
   - Use managed database services

---

## Future Enhancements

- [ ] API authentication & authorization
- [ ] Advanced scheduling (Airflow integration)
- [ ] Data quality monitoring
- [ ] Web dashboard
- [ ] Incremental/CDC support
- [ ] Multiple data sources (APIs, databases)
- [ ] Data lineage tracking
- [ ] Advanced error recovery
