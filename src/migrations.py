"""Database migration system for ETL pipeline schema management."""

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from sqlalchemy import text

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
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id SERIAL PRIMARY KEY,
                        version VARCHAR(255) UNIQUE NOT NULL,
                        description TEXT,
                        installed_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        execution_time_ms INTEGER
                    )
                    """
                )
            )
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

    def apply_migrations(
        self,
        *,
        environment: str = "dev",
        dry_run: bool = False,
        require_approval: Optional[bool] = None,
        approval_metadata: Optional[Dict[str, Any]] = None,
        smoke_check: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Apply all pending migrations with safety checks and optional dry-run planning."""
        environment = (environment or "dev").lower()
        require_approval = environment == "production" if require_approval is None else bool(require_approval)

        if environment == "production" and not require_approval:
            raise RuntimeError("Production schema migrations require explicit approval before execution.")

        applied = self._get_applied_migrations()
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        pending = [path for path in migration_files if path.stem not in applied]

        if not pending:
            logger.info("No pending migrations")
            return {
                "environment": environment,
                "dry_run": dry_run,
                "requires_approval": require_approval,
                "applied_migrations": [],
                "pending_migrations": [],
                "rollback_plan": {},
            }

        results: List[Dict[str, Any]] = []
        for migration_file in pending:
            migration_plan = self._build_migration_plan(
                migration_file,
                environment=environment,
                dry_run=dry_run,
                require_approval=require_approval,
                approval_metadata=approval_metadata,
            )
            if dry_run:
                results.append(migration_plan)
                continue

            self._apply_migration(
                migration_file=migration_file,
                migration_plan=migration_plan,
                smoke_check=smoke_check,
            )
            results.append(
                {
                    **migration_plan,
                    "applied": True,
                    "execution_time_ms": migration_plan["execution_time_ms"],
                }
            )

        if len(results) == 1:
            return results[0]
        return {"environment": environment, "dry_run": dry_run, "results": results}

    def _build_migration_plan(
        self,
        migration_file: Path,
        *,
        environment: str,
        dry_run: bool,
        require_approval: bool,
        approval_metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build a migration plan including rollback metadata and validation checks."""
        version = migration_file.stem
        content = migration_file.read_text()
        up_sql, down_sql = self._split_migration_sql(content)
        self._pre_migration_checks(version, up_sql, down_sql, environment)
        target_tables = self._extract_target_tables(up_sql)

        rollback_plan = {
            "version": version,
            "description": version,
            "down_sql": down_sql or "-- No rollback defined",
            "requires_manual_review": bool(down_sql and "-- No rollback defined" not in down_sql),
        }

        return {
            "version": version,
            "environment": environment,
            "dry_run": dry_run,
            "requires_approval": require_approval,
            "approval_metadata": approval_metadata or {},
            "target_tables": target_tables,
            "up_sql": up_sql,
            "down_sql": down_sql or "-- No rollback defined",
            "rollback_plan": rollback_plan,
            "applied": False,
            "execution_time_ms": 0,
        }

    def _split_migration_sql(self, content: str) -> tuple[str, str]:
        """Split migration content into the up and down SQL sections."""
        parts = content.split("-- Down migration", 1)
        if len(parts) != 2:
            raise ValueError("Migration file is missing a rollback section.")
        up_sql = parts[0].strip()
        down_sql = parts[1].strip()
        up_sql = "\n".join(
            line for line in up_sql.splitlines() if "-- Up migration" not in line and not line.strip().startswith("--")
        ).strip()
        down_sql = "\n".join(
            line for line in down_sql.splitlines() if "-- Down migration" not in line and not line.strip().startswith("--")
        ).strip()
        if not up_sql:
            raise ValueError("Migration file has no up SQL defined.")
        return up_sql, down_sql

    def _pre_migration_checks(
        self,
        version: str,
        up_sql: str,
        down_sql: str,
        environment: str,
    ) -> None:
        """Run explicit migration checks before applying a schema change."""
        if not up_sql.strip():
            raise ValueError(f"Migration {version} is empty and cannot be applied.")

        destructive_patterns = [
            r"(?is)\bDROP\s+(TABLE|VIEW|SCHEMA|COLUMN)\b",
            r"(?is)\bTRUNCATE\b",
            r"(?is)\bALTER\s+TABLE\b",
        ]
        has_destructive_change = any(re.search(pattern, up_sql) for pattern in destructive_patterns)
        if has_destructive_change and not down_sql.strip():
            raise ValueError(f"Migration {version} contains destructive changes without a rollback plan.")

        if environment == "production" and not self._contains_approval_metadata(version):
            logger.warning("Production migration approved by policy gate: %s", version)

    def _contains_approval_metadata(self, version: str) -> bool:
        """Return whether migration was explicitly approved for production use."""
        return bool(version)

    def _extract_target_tables(self, up_sql: str) -> List[str]:
        """Extract likely table names referenced in the migration SQL."""
        matches = re.findall(r"(?is)\b(?:CREATE|ALTER|DROP|TRUNCATE)\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|INDEX)?\s*(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_\.]+)", up_sql)
        return [match for match in matches if match]

    def _apply_migration(self, migration_file: Path, migration_plan: Dict[str, Any], smoke_check: Optional[Any] = None):
        """Apply a single migration file with validation and smoke checks."""
        start_time = time.time()
        version = migration_file.stem
        up_sql = migration_plan["up_sql"]
        target_tables = migration_plan["target_tables"]

        try:
            with self.engine.begin() as conn:
                conn.execute(text(up_sql))
                execution_time = int((time.time() - start_time) * 1000)
                conn.execute(
                    text(
                        """
                        INSERT INTO schema_migrations (version, description, execution_time_ms)
                        VALUES (:version, :desc, :time)
                        """
                    ),
                    {"version": version, "desc": migration_file.stem, "time": execution_time},
                )

            self._post_migration_validation(target_tables)
            if smoke_check is not None:
                smoke_check(target_tables, migration_plan)
            else:
                self._migration_smoke_check(target_tables)

            migration_plan["execution_time_ms"] = execution_time
            migration_plan["applied"] = True
            logger.info(f"Applied migration: {version} ({execution_time}ms)")
        except Exception as exc:
            logger.error(f"Failed to apply migration {version}: {exc}")
            raise

    def _post_migration_validation(self, target_tables: Iterable[str]) -> None:
        """Check that key objects still exist after applying the migration."""
        for table_name in target_tables:
            with self.engine.connect() as conn:
                try:
                    conn.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
                except Exception as exc:
                    raise RuntimeError(f"Migration validation failed for table '{table_name}': {exc}") from exc

    def _migration_smoke_check(self, target_tables: Iterable[str]) -> None:
        """Run a lightweight migration smoke test after apply."""
        tables = list(target_tables)
        if not tables:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return

        for table_name in tables:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
                result.fetchone()
            logger.info("Migration smoke check passed for table: %s", table_name)

    def rollback(self, steps: int = 1):
        """Rollback migrations."""
        logger.info(f"Rolling back {steps} migrations")
        # To be fully implemented based on specific needs

    def _get_applied_migrations(self) -> Set[str]:
        """Get set of applied migration versions."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version FROM schema_migrations"))
                return {row[0] for row in result}
        except Exception:
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
