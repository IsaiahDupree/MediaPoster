"""
Verify Orchestrator Tables (ARCH-001)
======================================
Check if orchestrator tables exist and have correct schema.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from loguru import logger

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:54322/postgres"
)


def verify_tables():
    """Verify orchestrator tables exist."""
    try:
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            # Check tables
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE 'orchestrator_%'
                ORDER BY table_name
            """))

            tables = [row[0] for row in result]

            if not tables:
                logger.error("❌ No orchestrator tables found!")
                return False

            logger.success(f"✅ Found {len(tables)} orchestrator tables:")
            for table in tables:
                logger.info(f"   - {table}")

            # Check columns in orchestrator_pipelines
            result = conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'orchestrator_pipelines'
                ORDER BY ordinal_position
            """))

            columns = [(row[0], row[1]) for row in result]
            logger.info(f"\n✅ orchestrator_pipelines columns ({len(columns)}):")
            for col, dtype in columns:
                logger.info(f"   - {col}: {dtype}")

            # Check if we can insert a test pipeline
            logger.info("\n🧪 Testing insert...")
            test_id = "test-verify-001"

            # Delete if exists
            conn.execute(text("""
                DELETE FROM orchestrator_pipelines WHERE pipeline_id = :id
            """), {"id": test_id})
            conn.commit()

            # Insert test
            conn.execute(text("""
                INSERT INTO orchestrator_pipelines (
                    pipeline_id, theme, status
                ) VALUES (
                    :id, :theme, :status
                )
            """), {"id": test_id, "theme": "Test theme", "status": "completed"})
            conn.commit()

            # Read back
            result = conn.execute(text("""
                SELECT pipeline_id, theme, status
                FROM orchestrator_pipelines
                WHERE pipeline_id = :id
            """), {"id": test_id})

            row = result.fetchone()
            if row:
                logger.success(f"✅ Insert/read test passed: {row[0]}, {row[1]}, {row[2]}")
            else:
                logger.error("❌ Insert/read test failed!")
                return False

            # Clean up
            conn.execute(text("""
                DELETE FROM orchestrator_pipelines WHERE pipeline_id = :id
            """), {"id": test_id})
            conn.commit()

            logger.success("\n✅ All orchestrator tables verified and working!")
            return True

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


if __name__ == "__main__":
    success = verify_tables()
    sys.exit(0 if success else 1)
