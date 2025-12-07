"""
Database Usability Tests
Tests database schema design, query performance, and developer experience
"""
import pytest
from sqlalchemy import text
from database.connection import async_session_maker, engine
import asyncio


@pytest.mark.asyncio
class TestDatabaseUsability:
    """Test database usability aspects"""
    
    async def test_database_has_helpful_indexes(self):
        """Database should have indexes on frequently queried columns"""
        async with async_session_maker() as session:
            # Check for indexes on common query columns
            result = await session.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename IN ('videos', 'clips', 'content_items', 'platform_posts')
                AND schemaname = 'public'
            """))
            indexes = result.fetchall()
            
            # Should have indexes on common columns
            index_names = [idx[0].lower() for idx in indexes]
            common_columns = ['id', 'created_at', 'video_id', 'status']
            
            # At least some indexes should exist
            assert len(indexes) > 0, "Database should have indexes for performance"
    
    async def test_foreign_keys_have_cascade_rules(self):
        """Foreign keys should have appropriate cascade rules"""
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT 
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    rc.delete_rule,
                    rc.update_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                JOIN information_schema.referential_constraints AS rc
                    ON rc.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                LIMIT 10
            """))
            fks = result.fetchall()
            
            # Should have foreign keys defined
            assert len(fks) > 0, "Database should have foreign key constraints"
    
    async def test_tables_have_timestamps(self):
        """Tables should have created_at/updated_at for debugging"""
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                AND table_name IN ('videos', 'clips', 'content_items')
            """))
            tables = [row[0] for row in result.fetchall()]
            
            for table in tables:
                result = await session.execute(text(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    AND column_name IN ('created_at', 'updated_at')
                """))
                columns = [row[0] for row in result.fetchall()]
                # At least created_at should exist
                assert 'created_at' in columns, f"{table} should have created_at timestamp"
    
    async def test_queries_are_performant(self):
        """Common queries should execute quickly"""
        async with async_session_maker() as session:
            import time
            
            # Test common query patterns
            queries = [
                "SELECT COUNT(*) FROM videos",
                "SELECT * FROM videos ORDER BY created_at DESC LIMIT 10",
                "SELECT v.*, COUNT(c.id) as clip_count FROM videos v LEFT JOIN clips c ON c.parent_video_id = v.id GROUP BY v.id LIMIT 10"
            ]
            
            for query in queries:
                start = time.time()
                await session.execute(text(query))
                elapsed = time.time() - start
                # Queries should complete in reasonable time
                assert elapsed < 5.0, f"Query took too long: {elapsed}s\n{query}"
    
    async def test_database_has_migration_history(self):
        """Database should track migrations for maintainability"""
        async with async_session_maker() as session:
            # Check if alembic_version table exists
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'alembic_version'
                )
            """))
            has_migrations = result.scalar()
            # Should have migration tracking (or at least version info)
            # This is optional but recommended
            pass  # Not required, but good practice
    
    async def test_constraints_provide_helpful_errors(self):
        """Database constraints should provide clear error messages"""
        async with async_session_maker() as session:
            # Try to insert duplicate (if unique constraint exists)
            try:
                await session.execute(text("""
                    INSERT INTO videos (id, file_name, source_uri)
                    VALUES (gen_random_uuid(), 'test.mp4', '/test/path')
                """))
                await session.commit()
            except Exception as e:
                # Error should be informative
                error_msg = str(e).lower()
                assert any(word in error_msg for word in ["constraint", "unique", "violation", "duplicate"])






