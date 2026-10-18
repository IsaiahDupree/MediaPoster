"""
Run Orchestrator Migrations (ARCH-001)
=======================================
Applies orchestrator_pipelines migration to the database.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from loguru import logger

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:54322/postgres"
)


def run_migration():
    """Run the orchestrator migration."""
    try:
        engine = create_engine(DATABASE_URL)

        # Read migration file
        migration_file = Path(__file__).parent.parent.parent / "supabase" / "migrations" / "20250127000001_orchestrator_pipelines.sql"

        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False

        with open(migration_file, "r") as f:
            migration_sql = f.read()

        logger.info("Applying orchestrator_pipelines migration...")

        with engine.connect() as conn:
            # Split by statement (simple approach)
            statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]

            for i, statement in enumerate(statements):
                if statement:
                    try:
                        conn.execute(text(statement))
                        conn.commit()
                        logger.debug(f"Executed statement {i+1}/{len(statements)}")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            logger.debug(f"Skipping existing object: {str(e)[:100]}")
                        else:
                            logger.error(f"Failed to execute statement {i+1}: {e}")
                            raise

        logger.success("✅ Migration applied successfully!")

        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name LIKE 'orchestrator_%'
            """))

            tables = [row[0] for row in result]
            logger.info(f"Tables created: {tables}")

        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
