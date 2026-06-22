"""Database migration system for ETL pipeline schema management."""

import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy import text
import sqlalchemy as sa
from typing import Optional

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database schema migrations with version tracking."""

    def __init__(self, engine, migrations_dir: Path = Path("sql/migrations")):
        """Initialize migration manager.

        Args:
            engine: SQLAlchemy engine instance
            migrations_dir: Directory containing migration SQL files
        """
        self.engine = engine
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        self._init_migrations_table()

    def _init_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    installed_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER
                )
            """))
            conn.commit()
        logger.info("Migrations table initialized")

    def create_migration(self, name: str, up_sql: str, down_sql: str = None):
        """Create a new migration file.

        Args:
            name: Migration name (e.g., 'create_users_table')
            up_sql: SQL for applying migration
            down_sql: SQL for reverting migration
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = f"{timestamp}_{name}"

        migration_file = self.migrations_dir / f"{version}.sql"

        content = f"""-- Migration: {name}
-- Version: {version}

-- Up migration
{up_sql}

-- Down migration (for rollback)
{down_sql or "-- No rollback defined"}
"""

        migration_file.write_text(content)
        logger.info(f"Created migration: {version}")
        return version

    def apply_migrations(self):
        """Apply all pending migrations."""
        applied = self._get_applied_migrations()

        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        pending = [f for f in migration_files if f.stem not in applied]

        if not pending:
            logger.info("No pending migrations")
            return

        for migration_file in pending:
            self._apply_migration(migration_file)

    def _apply_migration(self, migration_file: Path):
        """Apply a single migration file."""
        import time

        start_time = time.time()

        version = migration_file.stem
        content = migration_file.read_text()

        # Extract up migration (everything before "-- Down migration")
        up_sql = content.split("-- Down migration")[0].strip()
        up_sql = "\n".join(
            [
                line
                for line in up_sql.split("\n")
                if not line.strip().startswith("--") or "Up migration" not in line
            ]
        ).strip()

        try:
            with self.engine.connect() as conn:
                conn.execute(text(up_sql))

                execution_time = int((time.time() - start_time) * 1000)

                conn.execute(
                    text("""
                    INSERT INTO schema_migrations (version, description, execution_time_ms)
                    VALUES (:version, :desc, :time)
                """),
                    {
                        "version": version,
                        "desc": migration_file.stem,
                        "time": execution_time,
                    },
                )
                conn.commit()

            logger.info(f"Applied migration: {version} ({execution_time}ms)")
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {e}")
            raise

    def rollback(self, steps: int = 1):
        """Rollback migrations."""
        # Implementation for rollback logic
        logger.info(f"Rolling back {steps} migrations")
        # To be fully implemented based on specific needs

    def _get_applied_migrations(self) -> set:
        """Get set of applied migration versions."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version FROM schema_migrations"))
                return {row[0] for row in result}
        except:
            return set()

    def status(self):
        """Display migration status."""
        applied = self._get_applied_migrations()
        all_migrations = {f.stem for f in self.migrations_dir.glob("*.sql")}
        pending = all_migrations - applied

        logger.info(f"Applied migrations: {len(applied)}")
        logger.info(f"Pending migrations: {len(pending)}")

        if pending:
            for migration in sorted(pending):
                logger.info(f"  - {migration}")
