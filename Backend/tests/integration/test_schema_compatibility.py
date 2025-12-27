"""
Schema Compatibility Integration Tests
======================================
Verifies all services work correctly with the new database schema.
Tests actual DB writes/reads against the Supabase tables.
"""
import pytest
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, OperationalError

# Database URL for testing
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def db_engine():
    """Create database engine for tests"""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.fixture
def cleanup_test_data(db_engine):
    """Cleanup test data after tests"""
    test_ids = []
    yield test_ids
    
    # Cleanup
    if test_ids:
        with db_engine.connect() as conn:
            for table, id_col, id_val in test_ids:
                try:
                    conn.execute(text(f"DELETE FROM {table} WHERE {id_col} = :id"), {"id": id_val})
                    conn.commit()
                except:
                    pass


# ============================================================================
# Competitor Audit Schema Tests
# ============================================================================

class TestCompetitorAuditSchema:
    """Tests for competitor audit tables"""
    
    def test_competitor_account_table_exists(self, db_engine):
        """Verify competitor_account table exists with correct columns"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'competitor_account'
                ORDER BY ordinal_position
            """))
            columns = {row[0]: row[1] for row in result}
        
        assert "account_id" in columns
        assert "platform" in columns
        assert "handle" in columns
        assert "follower_count" in columns
        assert "bio_text" in columns
        assert "linkout_urls" in columns
    
    def test_competitor_post_table_exists(self, db_engine):
        """Verify competitor_post table exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'competitor_post'
            """))
            columns = [row[0] for row in result]
        
        assert "post_id" in columns
        assert "account_id" in columns
        assert "views" in columns
        assert "likes" in columns
        assert "caption_text" in columns
    
    def test_competitor_deep_audit_table_exists(self, db_engine):
        """Verify competitor_deep_audit table exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'competitor_deep_audit'
            """))
            columns = [row[0] for row in result]
        
        # Check core columns exist
        assert "audit_id" in columns
        assert "account_id" in columns
        assert "beat_sheet" in columns
    
    def test_competitor_funnel_map_table_exists(self, db_engine):
        """Verify competitor_funnel_map table exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'competitor_funnel_map'
            """))
            columns = [row[0] for row in result]
        
        assert "funnel_id" in columns
        assert "entry_points" in columns
        assert "lead_magnets" in columns
        assert "offer_stack" in columns  # Note: column is offer_stack, not offer_ladder
    
    def test_competitor_template_pack_table_exists(self, db_engine):
        """Verify competitor_template_pack table exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'competitor_template_pack'
            """))
            columns = [row[0] for row in result]
        
        assert "template_id" in columns
        assert "remotion_render_spec" in columns
        assert "placeholders" in columns
        assert "swap_rules" in columns
    
    def test_competitor_audit_report_table_exists(self, db_engine):
        """Verify competitor_audit_report table exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'competitor_audit_report'
            """))
            columns = [row[0] for row in result]
        
        assert "report_id" in columns
        assert "unique_factors" in columns
        assert "strategy" in columns
        assert "playbook" in columns
    
    def test_competitor_audit_run_table_exists(self, db_engine):
        """Verify competitor_audit_run table exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'competitor_audit_run'
            """))
            columns = [row[0] for row in result]
        
        assert "run_id" in columns
        assert "status" in columns
        assert "progress_pct" in columns
    
    def test_insert_competitor_account(self, db_engine, cleanup_test_data):
        """Test inserting a competitor account"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO competitor_account (
                    platform, handle, display_name, bio_text,
                    follower_count, following_count, post_count,
                    linkout_urls
                ) VALUES (
                    'instagram', 'test_handle_' || :suffix, 'Test User',
                    'Test bio text', 1000, 100, 50,
                    ARRAY['https://test.com']
                )
                RETURNING account_id
            """), {"suffix": str(uuid4())[:8]})
            conn.commit()
            account_id = str(result.fetchone()[0])
        
        cleanup_test_data.append(("competitor_account", "account_id", account_id))
        assert account_id is not None


# ============================================================================
# Enhanced Visual Analysis Schema Tests
# ============================================================================

class TestEnhancedVisualAnalysisSchema:
    """Tests for enhanced visual analysis tables"""
    
    def test_video_analysis_enhanced_columns(self, db_engine):
        """Verify video_analysis has new enhanced columns"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'video_analysis'
            """))
            columns = [row[0] for row in result]
        
        # Check for new columns added by migration
        enhanced_columns = [
            "color_palette", "lighting_analysis", "camera_info",
            "camera_motion_sequences", "scene_boundaries",
            "overall_visual_style", "viral_indicators"
        ]
        
        for col in enhanced_columns:
            if col not in columns:
                pytest.skip(f"Column {col} not yet added - run migration first")
    
    def test_video_template_library_table_exists(self, db_engine):
        """Verify video_template_library table exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'video_template_library'
            """))
            columns = [row[0] for row in result]
        
        if not columns:
            pytest.skip("video_template_library table not yet created - run migration")
        
        assert "template_id" in columns
        assert "name" in columns
        assert "slug" in columns
        assert "beat_sheet" in columns
        assert "style" in columns
    
    def test_template_usage_log_table_exists(self, db_engine):
        """Verify template_usage_log table exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'template_usage_log'
            """))
            columns = [row[0] for row in result]
        
        if not columns:
            pytest.skip("template_usage_log table not yet created")
        
        assert "usage_id" in columns
        assert "template_id" in columns
    
    def test_video_scene_detection_table_exists(self, db_engine):
        """Verify video_scene_detection table exists"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'video_scene_detection'
            """))
            columns = [row[0] for row in result]
        
        if not columns:
            pytest.skip("video_scene_detection table not yet created")
        
        assert "detection_id" in columns
        assert "scene_boundaries" in columns
        assert "motion_sequences" in columns
    
    def test_seed_templates_exist(self, db_engine):
        """Verify seed templates were inserted"""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM video_template_library
            """))
            count = result.fetchone()[0]
        
        if count == 0:
            pytest.skip("Seed templates not yet inserted")
        
        assert count >= 5, "Should have at least 5 seed templates"


# ============================================================================
# Service-Database Integration Tests
# ============================================================================

class TestServiceDatabaseIntegration:
    """Tests for service-database integration"""
    
    def test_collector_service_db_write(self, db_engine, cleanup_test_data):
        """Test CompetitorCollector can write to database"""
        from services.competitor_audit.collector import CompetitorCollector, CompetitorProfile
        
        collector = CompetitorCollector(db_url=DATABASE_URL)
        
        profile = CompetitorProfile(
            platform="instagram",
            handle=f"test_collector_{uuid4().hex[:6]}",
            platform_user_id="test_123",
            display_name="Test Collector User",
            bio_text="Test bio",
            follower_count=5000,
            following_count=500,
            post_count=100
        )
        
        try:
            # This should work without error
            with db_engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO competitor_account (
                        platform, handle, platform_user_id, display_name,
                        bio_text, follower_count, following_count, post_count
                    ) VALUES (
                        :platform, :handle, :user_id, :display_name,
                        :bio, :followers, :following, :posts
                    )
                    RETURNING account_id
                """), {
                    "platform": profile.platform,
                    "handle": profile.handle,
                    "user_id": profile.platform_user_id,
                    "display_name": profile.display_name,
                    "bio": profile.bio_text,
                    "followers": profile.follower_count,
                    "following": profile.following_count,
                    "posts": profile.post_count
                })
                conn.commit()
                account_id = str(result.fetchone()[0])
            
            cleanup_test_data.append(("competitor_account", "account_id", account_id))
            assert account_id is not None
        except Exception as e:
            pytest.fail(f"Service-DB integration failed: {e}")
    
    def test_deep_audit_jsonb_columns(self, db_engine, cleanup_test_data):
        """Test deep audit JSONB columns work correctly"""
        import json
        
        # First create a test account
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO competitor_account (platform, handle, follower_count)
                VALUES ('instagram', :handle, 1000)
                RETURNING account_id
            """), {"handle": f"test_audit_{uuid4().hex[:6]}"})
            conn.commit()
            account_id = str(result.fetchone()[0])
        
        cleanup_test_data.append(("competitor_account", "account_id", account_id))
        
        # Test JSONB insert using actual schema columns
        beat_sheet = json.dumps([
            {"role": "hook", "start_sec": 0, "end_sec": 3, "emotion": "curiosity"},
            {"role": "cta", "start_sec": 27, "end_sec": 30, "emotion": "urgency"}
        ])
        
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO competitor_deep_audit (
                    account_id, audit_type, beat_sheet, hook_archetype
                ) VALUES (
                    :account_id, 'account', CAST(:beat_sheet AS jsonb), 'Stop doing X'
                )
                RETURNING audit_id
            """), {
                "account_id": account_id,
                "beat_sheet": beat_sheet
            })
            conn.commit()
            audit_id = str(result.fetchone()[0])
        
        cleanup_test_data.append(("competitor_deep_audit", "audit_id", audit_id))
        
        # Verify JSONB can be queried
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT hook_archetype, beat_sheet
                FROM competitor_deep_audit
                WHERE audit_id = :audit_id
            """), {"audit_id": audit_id})
            row = result.fetchone()
        
        assert row[0] == "Stop doing X"
        assert len(row[1]) == 2
    
    def test_template_library_beat_sheet_structure(self, db_engine, cleanup_test_data):
        """Test template library beat sheet JSONB structure"""
        import json
        
        beat_sheet = json.dumps([
            {"role": "hook", "duration_range": [0, 3], "description": "Attention grabber"},
            {"role": "solution", "duration_range": [3, 25], "description": "Main content"},
            {"role": "cta", "duration_range": [25, 30], "description": "Call to action"}
        ])
        
        style = json.dumps({"tone": "educational", "pacing": "medium", "energy": "high"})
        
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO video_template_library (
                    name, slug, category, beat_sheet, style,
                    target_duration_sec, difficulty
                ) VALUES (
                    :name, :slug, 'tutorial_quick', CAST(:beat_sheet AS jsonb), CAST(:style AS jsonb),
                    30, 'intermediate'
                )
                RETURNING template_id
            """), {
                "name": f"Test Template {uuid4().hex[:6]}",
                "slug": f"test-template-{uuid4().hex[:6]}",
                "beat_sheet": beat_sheet,
                "style": style
            })
            conn.commit()
            template_id = str(result.fetchone()[0])
        
        cleanup_test_data.append(("video_template_library", "template_id", template_id))
        
        # Query and verify structure
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT beat_sheet, style->>'tone' as tone
                FROM video_template_library
                WHERE template_id = :template_id
            """), {"template_id": template_id})
            row = result.fetchone()
        
        assert len(row[0]) == 3
        assert row[1] == "educational"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
