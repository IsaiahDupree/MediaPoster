"""
Tests for Scheduling Service (PRD2)
Verifies horizon planning, gap constraints, and schedule generation
Target: ~30-40 tests
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from services.prd2.scheduling_service import SchedulingService
from models.supabase_models import MediaAsset, PostingSchedule, Platform, SourceType, MediaType

class TestSchedulingService:
    """Tests for scheduling algorithm"""

    @pytest.fixture
    def service(self):
        return SchedulingService()

    def create_assets(self, count):
        """Helper to create dummy assets"""
        return [
            MediaAsset(
                owner_id=uuid4(),
                source_type=SourceType.LOCAL_UPLOAD,
                storage_path=f"path_{i}",
                media_type=MediaType.VIDEO
            ) for i in range(count)
        ]

    # ============================================
    # Algorithm Logic Tests - Low Volume (Sparse)
    # ============================================

    def test_schedule_sparse_volume(self, service):
        """
        Few assets (e.g., 5) over 60 days.
        Ideal spacing = 1440h / 5 = 288h.
        Clamped max = 24h.
        Expect spacing of ~24h.
        """
        assets = self.create_assets(5)
        schedule = service.generate_schedule(assets)
        
        assert len(schedule) == 5
        
        # Check gaps
        for i in range(len(schedule) - 1):
            gap = schedule[i+1].scheduled_at - schedule[i].scheduled_at
            # Allowing microsecond variance
            assert abs(gap.total_seconds() - 86400) < 1.0  # 24h

    def test_schedule_very_low_volume(self, service):
        """1 asset should be scheduled ~24h from start"""
        assets = self.create_assets(1)
        schedule = service.generate_schedule(assets)
        
        start = datetime.utcnow() # approx
        gap = schedule[0].scheduled_at - start
        # Since start captured inside function is slightly later, check range
        # roughly 24h
        assert 86000 < gap.total_seconds() < 86500

    # ============================================
    # Algorithm Logic Tests - High Volume (Dense)
    # ============================================

    def test_schedule_dense_volume(self, service):
        """
        Many assets (e.g., 2000) over 60 days.
        Ideal spacing = 1440h / 2000 = 0.72h.
        Clamped min = 2h.
        Expect spacing of ~2h.
        Expect some assets dropped (break horizon).
        """
        count = 1000  # 1000 * 2h = 2000h > 1440h (horizon)
        assets = self.create_assets(count)
        schedule = service.generate_schedule(assets)
        
        # Horizon is 1440 hours. At 2h spacing, max fits is 720.
        # Actually generate loop breaks at offset > horizon.
        # 720 * 2 = 1440. So exactly 720 fits?
        # Loop 1..720. 720*2 = 1440 (ok). 721*2 = 1442 (break).
        assert len(schedule) == 720
        
        # Check gap
        gap = schedule[1].scheduled_at - schedule[0].scheduled_at
        assert abs(gap.total_seconds() - 7200) < 1.0 # 2h

    def test_schedule_max_density(self, service):
        """Boundary test for exactly 720 assets (2h spacing fills horizon)"""
        assets = self.create_assets(720)
        schedule = service.generate_schedule(assets)
        assert len(schedule) == 720
        assert abs((schedule[-1].scheduled_at - schedule[-2].scheduled_at).total_seconds() - 7200) < 1

    # ============================================
    # Algorithm Logic Tests - Mid Volume
    # ============================================

    def test_schedule_mid_volume(self, service):
        """
        Assets that fit perfectly without clamping.
        E.g., 144 assets.
        Ideal = 1440h / 144 = 10h.
        10h is within [2, 24].
        Expect 10h spacing.
        """
        assets = self.create_assets(144)
        schedule = service.generate_schedule(assets)
        
        assert len(schedule) == 144
        gap = schedule[1].scheduled_at - schedule[0].scheduled_at
        assert abs(gap.total_seconds() - 36000) < 1.0 # 10h

    # ============================================
    # Structural/Object Tests
    # ============================================

    def test_generated_objects(self, service):
        """Verify content of generated schedule objects"""
        assets = self.create_assets(1)
        schedule = service.generate_schedule(assets)[0]
        
        assert isinstance(schedule, PostingSchedule)
        assert schedule.media_id == assets[0].id
        assert schedule.status == "pending"
        # Platform hint check
        assert schedule.platform == Platform.TIKTOK

    def test_empty_input(self, service):
        """Test empty asset list"""
        assert service.generate_schedule([]) == []

    # ============================================
    # Merging Logic Tests
    # ============================================

    def test_merge_append_strategy(self, service):
        """Test merging new assets appends to existing schedule"""
        assets = self.create_assets(5)
        initial_schedule = service.generate_schedule(assets)
        last_time = initial_schedule[-1].scheduled_at
        
        new_assets = self.create_assets(2)
        new_schedule = service.merge_with_existing(new_assets, initial_schedule)
        
        # Check first new item is after last old item
        first_new_time = new_schedule[0].scheduled_at
        assert first_new_time > last_time
        
        # Since it calls generate with new list of 2:
        # 1440 / 2 = 720h -> clamp 24h.
        # So it should start 24h after last_time.
        gap = first_new_time - last_time
        assert abs(gap.total_seconds() - 86400) < 1.0

    def test_merge_with_empty_existing(self, service):
        """Test merge with no existing schedule behaves like generate"""
        assets = self.create_assets(5)
        schedule = service.merge_with_existing(assets, [])
        assert len(schedule) == 5

    # ============================================
    # Platform Logic Tests
    # ============================================

    def test_specific_platform_hint(self, service):
        """Test platform hint is respected"""
        asset = MediaAsset(
            owner_id=uuid4(), source_type="local_upload", storage_path="",
            media_type="video", platform_hint=Platform.YOUTUBE_SHORTS
        )
        schedule = service.generate_schedule([asset])[0]
        assert schedule.platform == Platform.YOUTUBE_SHORTS

    def test_multi_platform_hint_defaults(self, service):
        """Test MULTI platform defaults to TIKTOK (impl detail)"""
        asset = MediaAsset(
            owner_id=uuid4(), source_type="local_upload", storage_path="",
            media_type="video", platform_hint=Platform.MULTI
        )
        schedule = service.generate_schedule([asset])[0]
        assert schedule.platform == Platform.TIKTOK
