# Troubleshooting Guide

## Common Issues and Solutions

### Database Connection Issues

#### Problem: `psycopg2.OperationalError: could not connect to server`

**Causes:**
- PostgreSQL service is not running
- Incorrect host/port in `.env` file
- Database credentials are wrong
- Network connectivity issues

**Solutions:**
1. **Check if PostgreSQL is running:**
   ```bash
   # On Linux/macOS
   pg_isready -h localhost -p 5432
   
   # Should return: accepting connections
   ```

2. **Verify connection settings in `.env`:**
   ```bash
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   ```

3. **Test connection manually:**
   ```bash
   psql -h localhost -U postgres -d etl_db
   ```

4. **If using Docker:**
   ```bash
   docker-compose up -d db
   # Wait 10 seconds for database to start
   docker-compose logs db
   ```

---

### Data Transformation Issues

#### Problem: `KeyError` or missing columns after transform

**Causes:**
- Column names have unexpected characters or spacing
- CSV file has inconsistent headers
- Data type mismatches

**Solutions:**
1. **Check CSV headers:**
   ```bash
   head -1 data/raw/your_file.csv
   ```

2. **Enable debug logging:**
   ```bash
   LOG_LEVEL=DEBUG python -m src.pipeline
   ```

3. **Verify transform function:**
   ```python
   from src.transform.transform_data import transform
   import pandas as pd
   
   df = pd.read_csv("data/raw/your_file.csv")
   print("Columns:", df.columns.tolist())
   result = transform(df)
   print("Transformed columns:", result.columns.tolist())
   ```

---

#### Problem: `TypeError: unsupported operand type(s)`

**Causes:**
- Data type conversions failing
- NaN/None values in numeric columns
- Mixed type data

**Solutions:**
1. **Check data types:**
   ```python
   print(df.dtypes)
   print(df.isnull().sum())
   ```

2. **Handle NaN values:**
   ```python
   df = df.fillna(0)  # Fill with 0
   df = df.dropna()   # Drop NaN rows
   ```

3. **Convert types explicitly:**
   ```python
   df['column'] = pd.to_numeric(df['column'], errors='coerce')
   ```

---

### File System Issues

#### Problem: `FileNotFoundError: data/raw` not found

**Causes:**
- Data directory structure not created
- Incorrect path in configuration
- Working directory is wrong

**Solutions:**
1. **Create directory structure:**
   ```bash
   mkdir -p data/raw data/processed
   ```

2. **Check current directory:**
   ```bash
   pwd
   ```

3. **Verify .env path configuration:**
   ```bash
   RAW_DATA_DIR=data/raw
   PROCESSED_DATA_DIR=data/processed
   ```

---

#### Problem: `PermissionError: Permission denied`

**Causes:**
- Insufficient file permissions
- Read-only file system
- File is being used by another process

**Solutions:**
1. **Check file permissions:**
   ```bash
   ls -la data/raw/
   ls -la data/processed/
   ```

2. **Fix permissions:**
   ```bash
   chmod 755 data/raw data/processed
   ```

3. **Check if file is in use:**
   ```bash
   lsof data/processed/*.csv
   ```

---

### Memory and Performance Issues

#### Problem: `MemoryError` or slow processing

**Causes:**
- Processing too many rows at once
- Large file sizes
- Insufficient system memory

**Solutions:**
1. **Reduce chunk size in `.env`:**
   ```bash
   CHUNK_SIZE=5000  # Default is 10000
   ```

2. **Monitor memory usage:**
   ```bash
   # During pipeline execution
   watch -n 1 'ps aux | grep python'
   ```

3. **Check system resources:**
   ```bash
   free -h  # Memory
   df -h    # Disk space
   ```

4. **Split large files:**
   ```bash
   split -l 100000 large_file.csv chunk_
   ```

---

### Logging Issues

#### Problem: No log files created

**Causes:**
- Log directory doesn't exist
- Insufficient permissions
- Logging not configured

**Solutions:**
1. **Check log directory:**
   ```bash
   ls -la logs/
   ```

2. **Create log directory:**
   ```bash
   mkdir -p logs
   chmod 755 logs
   ```

3. **Validate logging configuration:**
   ```python
   from src.logging_config import LogValidator
   results = LogValidator.validate()
   print(results)
   ```

---

#### Problem: Log levels not working

**Causes:**
- LOG_LEVEL not set in `.env`
- Logging configuration not applied
- Level not in correct format

**Solutions:**
1. **Set LOG_LEVEL in `.env`:**
   ```bash
   LOG_LEVEL=DEBUG  # or INFO, WARNING, ERROR, CRITICAL
   ```

2. **Check current log level:**
   ```python
   import logging
   print(logging.getLogger().level)
   ```

3. **Reconfigure logging:**
   ```python
   from src.logging_config import LogConfig
   LogConfig.configure(level='DEBUG')
   ```

---

### Docker Issues

#### Problem: `docker-compose up` fails

**Causes:**
- Docker daemon not running
- Port already in use
- Missing environment variables

**Solutions:**
1. **Start Docker daemon:**
   ```bash
   # macOS
   open /Applications/Docker.app
   
   # Linux
   sudo systemctl start docker
   ```

2. **Check port availability:**
   ```bash
   lsof -i :5432  # PostgreSQL
   lsof -i :5000  # API
   ```

3. **Clean up containers:**
   ```bash
   docker-compose down -v  # Remove volumes too
   docker system prune -a
   ```

---

### Pipeline Execution Issues

#### Problem: `ExtractionError` or `TransformError`

**Causes:**
- Malformed CSV data
- Encoding issues
- Missing required columns

**Solutions:**
1. **Check file encoding:**
   ```bash
   file -bi data/raw/your_file.csv
   ```

2. **Convert encoding if needed:**
   ```bash
   iconv -f UTF-16 -t UTF-8 input.csv > output.csv
   ```

3. **Validate CSV structure:**
   ```bash
   head -5 data/raw/your_file.csv
   tail -5 data/raw/your_file.csv
   ```

---

#### Problem: Pipeline runs but no data is loaded

**Causes:**
- Data is empty after transformation
- Database table doesn't exist
- Data volume mounted incorrectly

**Solutions:**
1. **Check extracted data:**
   ```python
   from src.extract.extract_data import extract_csv
   df = extract_csv('data/raw/your_file.csv')
   print(f"Rows: {len(df)}, Columns: {len(df.columns)}")
   ```

2. **Run migrations:**
   ```python
   from src.migrations import MigrationManager
   from sqlalchemy import create_engine
   
   engine = create_engine(connection_string)
   manager = MigrationManager(engine)
   manager.apply_migrations()
   ```

3. **Check Docker volumes:**
   ```bash
   docker volume ls
   docker inspect volume_name
   ```

---

### Health Check Issues

#### Problem: Health check fails

**Causes:**
- Database unreachable
- Required directories missing
- Dependencies not installed

**Solutions:**
1. **Run health check:**
   ```python
   from src.health import HealthChecker
   
   checker = HealthChecker()
   results = checker.run_all_checks()
   print(checker.get_status_report())
   ```

2. **Install missing dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Check file system:**
   ```bash
   ls -la data/raw data/processed logs
   ```

---

## Getting Help

### Enable Debug Logging

```bash
LOG_LEVEL=DEBUG python -m src.pipeline
```

### Check Pipeline Statistics

The pipeline logs detailed statistics including:
- Files processed
- Rows extracted/transformed/loaded
- Execution time
- Errors encountered

Look for these in `logs/pipeline.log`

### Run Health Checks

```bash
python -c "from src.health import HealthChecker; print(HealthChecker().get_status_report())"
```

### Test Individual Components

```bash
# Test extraction
python -c "from src.extract.extract_data import extract_csv; df = extract_csv('data/raw/file.csv'); print(f'Rows: {len(df)}')"

# Test transform
python -c "from src.transform.transform_data import transform; import pandas as pd; df = pd.read_csv('data/raw/file.csv'); print(transform(df).shape)"

# Test database connection
python -c "from src.config import get_config; from sqlalchemy import create_engine; engine = create_engine(get_config().database.get_connection_string()); print('Connected!')"
```

---

## Performance Optimization

### For Large Datasets

1. **Increase chunk size:**
   ```bash
   CHUNK_SIZE=50000
   ```

2. **Use parallel processing:**
   - Modify transform functions to use multiprocessing
   - Process multiple files concurrently

3. **Database optimization:**
   - Add indexes on frequently queried columns
   - Use bulk insert instead of row-by-row

4. **Monitor system resources:**
   ```bash
   htop
   iotop
   ```

---

## Reporting Issues

When reporting bugs, include:
1. Full error message and traceback
2. Configuration (excluding passwords)
3. Data sample (if possible)
4. System information (`uname -a`, Python version)
5. Pipeline logs from `logs/pipeline.log`
6. Output of health checks
