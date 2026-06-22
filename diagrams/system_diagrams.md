# System Diagrams

## ETL Pipeline Data Flow

### High-Level Data Flow
```
┌─────────────┐
│  CSV Files  │
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ EXTRACT              │
│ - Read CSV           │
│ - Detect Encoding    │
│ - Validate Format    │
└──────┬───────────────┘
       │
       ▼ (Raw Data)
┌──────────────────────┐
│ TRANSFORM            │
│ - Normalize Columns  │
│ - Clean Data         │
│ - Remove Duplicates  │
│ - Type Conversion    │
└──────┬───────────────┘
       │
       ▼ (Processed Data)
┌──────────────────────┐
│ LOAD                 │
│ - Batch Insert       │
│ - Transaction Mgmt   │
│ - Error Handling     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ PostgreSQL Database  │
│ - cars               │
│ - dealers            │
│ - sales              │
└──────────────────────┘
```

---

## Application Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   API Layer  │  │   Pipeline   │  │  Scheduler   │   │
│  │  (Flask)     │  │  Orchestrator│  │  (Schedule)  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│       │                   │                  │            │
│       └───────────────────┼──────────────────┘            │
│                           │                               │
│       ┌───────────────────▼────────────────┐             │
│       │      ETL Core Modules              │             │
│       ├──────────────────────────────────┤             │
│       │ • Extract  (extract_data.py)    │             │
│       │ • Transform (transform_data.py) │             │
│       │ • Load (load_to_db.py)          │             │
│       └───────────────────┬────────────────┘             │
│                           │                               │
│       ┌───────────────────▼────────────────┐             │
│       │   Support Services                │             │
│       ├──────────────────────────────────┤             │
│       │ • Configuration (config.py)     │             │
│       │ • Logging (logging_config.py)   │             │
│       │ • Health Checks (health.py)     │             │
│       │ • Migrations (migrations.py)    │             │
│       └───────────────────────────────────┘             │
│                                                           │
└─────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐    ┌─────────┐    ┌──────────┐
   │   File   │    │Database │    │  Logs    │
   │ System   │    │         │    │          │
   └─────────┘    └─────────┘    └──────────┘
```

---

## Component Interaction Diagram

```
┌──────────────────────────────────────────────────┐
│           Main Pipeline (pipeline.py)            │
└────────────────┬─────────────────────────────────┘
                 │
     ┌───────────┼───────────┐
     │           │           │
     ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│ Extract │ │Transform│ │  Load   │
│ Module  │ │ Module  │ │ Module  │
└────┬────┘ └────┬────┘ └────┬────┘
     │           │           │
     └───────────┼───────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Config Service │
        └────────┬───────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
    ┌─────────┐      ┌─────────┐
    │Database │      │File Sys │
    │Conn Str │      │Paths    │
    └─────────┘      └─────────┘
```

---

## Database Connection Flow

```
┌────────────────────┐
│ Pipeline Request   │
└─────────┬──────────┘
          │
          ▼
┌────────────────────────────┐
│ Load Config from .env      │
│ POSTGRES_HOST              │
│ POSTGRES_USER              │
│ POSTGRES_PASSWORD          │
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│ Create Connection String   │
│ postgresql://user:pwd@host │
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│ SQLAlchemy Engine          │
│ with Connection Pooling    │
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│ Health Check Database      │
│ (SELECT 1 to verify)       │
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│ Apply Migrations           │
│ (schema_migrations table)  │
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│ Load/Insert Data           │
│ (Batch Insert)             │
└────────────────────────────┘
```

---

## Error Handling Flow

```
┌──────────────────────┐
│ Pipeline Execution   │
└──────────┬───────────┘
           │
           ▼
    ┌──────────────┐
    │ Try Block    │
    │ Process Data │
    └─┬────────────┘
      │ Success
      ▼
    ┌──────────────┐
    │ Commit & Log │
    │ Statistics   │
    └──────────────┘
      │ Error
      ▼
    ┌──────────────────────┐
    │ Catch Exception      │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────────┐
    │ Retry Count < MAX?       │
    └──┬───────────────────┬───┘
       │ Yes               │ No
       ▼                   ▼
   ┌───────┐         ┌──────────┐
   │ Retry │         │ Log Error│
   │ (with │         │ Rollback │
   │ delay)│         │ Cleanup  │
   └───────┘         └──────────┘
       │                  │
       └──────┬───────────┘
              │
              ▼
    ┌──────────────────┐
    │ Continue Pipeline│
    │ or Exit with Code│
    └──────────────────┘
```

---

## State Diagram

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  INIT CONFIG│
        ┌──────────▶│LOGGING      │◀────┐
        │           │MIGRATIONS   │     │
        │           └──────┬──────┘     │
        │                  │ FAIL       │
        │                  ▼            │
        │           ┌─────────────┐     │
        │   FAIL    │ HEALTH CHECK│     │
        └───────────│             │     │
                    └──────┬──────┘     │
                           │ SUCCESS   │
                           ▼           │
                    ┌─────────────┐    │
                    │  EXTRACT    │    │
                    │  CSV FILES  │    │
                    └──────┬──────┘    │
                           │ FAIL      │
                           ├───────────┘
                           │ SUCCESS
                           ▼
                    ┌─────────────┐
                    │ TRANSFORM   │
                    │  DATA       │
                    └──────┬──────┘
                           │ FAIL
                           ├───────────┐
                           │           │
                    SUCCESS│           │
                           ▼           │
                    ┌─────────────┐    │
                    │  LOAD       │    │
                    │  DATABASE   │    │
                    └──────┬──────┘    │
                           │           │
                    SUCCESS│ FAIL      │
                           ▼           │
                    ┌─────────────┐    │
                    │  LOG STATS  │◀───┘
                    │  CLEANUP    │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   EXIT      │
                    │  (SUCCESS)  │
                    └─────────────┘
```

---

## Testing Architecture

```
┌──────────────────────────────────────────┐
│         Test Suite Structure             │
├──────────────────────────────────────────┤
│                                           │
│  ┌──────────────────────────────────┐   │
│  │   Unit Tests                     │   │
│  │  - test_pipeline.py              │   │
│  │  - test_data_validation.py       │   │
│  │  - test_logging.py               │   │
│  └──────────────────────────────────┘   │
│                                           │
│  ┌──────────────────────────────────┐   │
│  │   Performance Tests              │   │
│  │  - test_benchmark.py             │   │
│  └──────────────────────────────────┘   │
│                                           │
│  ┌──────────────────────────────────┐   │
│  │   CI/CD Workflows                │   │
│  │  - .github/workflows/ci.yml      │   │
│  │  - .github/workflows/lint.yml    │   │
│  └──────────────────────────────────┘   │
│                                           │
└──────────────────────────────────────────┘
```

---

## Deployment Architecture

```
┌────────────────────────────────────────┐
│       Docker Compose Setup             │
├────────────────────────────────────────┤
│                                         │
│  Container 1: PostgreSQL               │
│  ├─ Image: postgres:15                 │
│  ├─ Port: 5432                         │
│  ├─ Volume: db_data:/var/lib/...       │
│  └─ Env: POSTGRES_* variables          │
│                                         │
│  Container 2: ETL Application          │
│  ├─ Image: cloud-etl-pipeline:latest   │
│  ├─ Depends on: db service             │
│  ├─ Volumes:                           │
│  │  ├─ ./data:/app/data                │
│  │  └─ ./logs:/app/logs                │
│  └─ Env: .env file                     │
│                                         │
└────────────────────────────────────────┘
```

---

## Monitoring Dashboard Flow (Future)

```
┌────────────────┐
│ Dashboard UI   │
│ (Web Interface)│
└────────┬───────┘
         │
         ▼
┌────────────────┐
│ REST API       │
│ (/health,      │
│  /status, etc) │
└────────┬───────┘
         │
    ┌────┴────┬────────────┐
    │          │            │
    ▼          ▼            ▼
┌────────┐┌────────┐┌──────────┐
│Pipeline││Database││File Sys  │
│Status  ││Health  ││Health    │
└────────┘└────────┘└──────────┘
    │          │            │
    └────┬─────┴────────────┘
         │
         ▼
    ┌──────────────┐
    │ Metrics &    │
    │ Alerts       │
    └──────────────┘
```
