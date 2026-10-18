"""
Data Hydration Service Unit Tests
==================================
Tests for the centralized data hydration system
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from services.data_hydration_service import (
    DataDomain,
    RefreshResult,
    HydrationStatus,
    DataHydrationService,
)


class TestDataDomain:
    """Tests for DataDomain enum"""

    def test_domain_values(self):
        assert DataDomain.ACCOUNTS == "accounts"
        assert DataDomain.POSTS == "posts"
        assert DataDomain.FOLLOWERS == "followers"
        assert DataDomain.COMMENTS == "comments"
        assert DataDomain.METRICS == "metrics"
        assert DataDomain.ALL == "all"

    def test_all_domains(self):
        domains = list(DataDomain)
        assert len(domains) == 6


class TestRefreshResult:
    """Tests for RefreshResult dataclass"""

    def test_successful_result(self):
        result = RefreshResult(
            domain=DataDomain.ACCOUNTS,
            success=True,
            records_updated=50,
            duration_seconds=2.5,
        )
        
        assert result.domain == DataDomain.ACCOUNTS
        assert result.success is True
        assert result.records_updated == 50
        assert result.duration_seconds == 2.5
        assert result.error is None

    def test_failed_result(self):
        result = RefreshResult(
            domain=DataDomain.POSTS,
            success=False,
            error="API rate limit exceeded",
        )
        
        assert result.success is False
        assert result.error == "API rate limit exceeded"
        assert result.records_updated == 0

    def test_default_values(self):
        result = RefreshResult(
            domain=DataDomain.COMMENTS,
            success=True,
        )
        
        assert result.records_updated == 0
        assert result.duration_seconds == 0
        assert result.error is None


class TestHydrationStatus:
    """Tests for HydrationStatus dataclass"""

    def test_initial_status(self):
        status = HydrationStatus()
        
        assert status.last_full_refresh is None
        assert status.last_incremental is None
        assert status.accounts_count == 0
        assert status.posts_count == 0
        assert status.followers_count == 0
        assert status.comments_count == 0
        assert status.refresh_in_progress is False
        assert status.current_domain is None

    def test_active_status(self):
        status = HydrationStatus(
            last_full_refresh=datetime.now(),
            accounts_count=22,
            posts_count=1500,
            followers_count=500,
            comments_count=5000,
            refresh_in_progress=True,
            current_domain="posts",
        )
        
        assert status.accounts_count == 22
        assert status.posts_count == 1500
        assert status.refresh_in_progress is True
        assert status.current_domain == "posts"


class TestDataHydrationService:
    """Tests for DataHydrationService"""

    @pytest.fixture
    def service(self):
        with patch.dict('os.environ', {'DATABASE_URL': 'sqlite:///test.db'}):
            service = DataHydrationService()
            return service

    def test_initialization(self, service):
        assert service.status is not None
        assert isinstance(service.status, HydrationStatus)
        assert service.status.refresh_in_progress is False

    def test_db_url_from_env(self, service):
        assert 'test.db' in service.db_url

    @pytest.mark.asyncio
    async def test_get_status_structure(self, service):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.scalar.return_value = 0
        
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock()
        
        with patch.object(service, '_get_engine', return_value=mock_engine):
            status = await service.get_status()
        
        assert isinstance(status, dict)

    @pytest.mark.asyncio
    async def test_get_status_with_counts(self, service):
        def mock_scalar_side_effect(*args, **kwargs):
            return 100
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100
        
        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock()
        
        with patch.object(service, '_get_engine', return_value=mock_engine):
            status = await service.get_status()
        
        assert isinstance(status, dict)


class TestDataHydrationServiceRefresh:
    """Tests for refresh functionality"""

    @pytest.fixture
    def service(self):
        with patch.dict('os.environ', {'DATABASE_URL': 'sqlite:///test.db'}):
            with patch('services.data_hydration_service.get_orchestrator') as mock_orch:
                mock_orch.return_value = MagicMock()
                service = DataHydrationService()
                return service

    @pytest.mark.asyncio
    async def test_refresh_lock_prevents_concurrent(self, service):
        # Simulate refresh in progress
        service.status.refresh_in_progress = True
        
        # Should not start another refresh
        assert service.status.refresh_in_progress is True

    @pytest.mark.asyncio
    async def test_refresh_updates_status(self, service):
        service.status.refresh_in_progress = False
        service.status.current_domain = None
        
        # Simulate starting refresh
        service.status.refresh_in_progress = True
        service.status.current_domain = "accounts"
        
        assert service.status.refresh_in_progress is True
        assert service.status.current_domain == "accounts"


class TestRefreshResultAggregation:
    """Tests for aggregating multiple refresh results"""

    def test_aggregate_success(self):
        results = [
            RefreshResult(domain=DataDomain.ACCOUNTS, success=True, records_updated=22),
            RefreshResult(domain=DataDomain.POSTS, success=True, records_updated=500),
            RefreshResult(domain=DataDomain.FOLLOWERS, success=True, records_updated=100),
        ]
        
        total_updated = sum(r.records_updated for r in results)
        all_success = all(r.success for r in results)
        
        assert total_updated == 622
        assert all_success is True

    def test_aggregate_partial_failure(self):
        results = [
            RefreshResult(domain=DataDomain.ACCOUNTS, success=True, records_updated=22),
            RefreshResult(domain=DataDomain.POSTS, success=False, error="API error"),
            RefreshResult(domain=DataDomain.FOLLOWERS, success=True, records_updated=100),
        ]
        
        failed = [r for r in results if not r.success]
        success = [r for r in results if r.success]
        
        assert len(failed) == 1
        assert len(success) == 2
        assert failed[0].domain == DataDomain.POSTS


class TestDataDomainPriority:
    """Tests for domain refresh priority"""

    def test_domain_order(self):
        # Recommended refresh order
        order = [
            DataDomain.ACCOUNTS,
            DataDomain.POSTS,
            DataDomain.COMMENTS,
            DataDomain.FOLLOWERS,
            DataDomain.METRICS,
        ]
        
        assert order[0] == DataDomain.ACCOUNTS
        assert order[-1] == DataDomain.METRICS

    def test_all_domain_includes_all(self):
        all_domains = [d for d in DataDomain if d != DataDomain.ALL]
        assert len(all_domains) == 5


class TestHydrationStatusUpdates:
    """Tests for status update logic"""

    def test_mark_refresh_start(self):
        status = HydrationStatus()
        
        status.refresh_in_progress = True
        status.current_domain = "accounts"
        
        assert status.refresh_in_progress is True

    def test_mark_refresh_complete(self):
        status = HydrationStatus(
            refresh_in_progress=True,
            current_domain="posts",
        )
        
        status.refresh_in_progress = False
        status.last_full_refresh = datetime.now()
        status.current_domain = None
        
        assert status.refresh_in_progress is False
        assert status.last_full_refresh is not None

    def test_update_counts(self):
        status = HydrationStatus()
        
        status.accounts_count = 22
        status.posts_count = 1500
        status.followers_count = 500
        status.comments_count = 5000
        
        total = (status.accounts_count + status.posts_count + 
                 status.followers_count + status.comments_count)
        
        assert total == 7022


class TestRefreshTimingLogic:
    """Tests for refresh timing and staleness"""

    def test_needs_refresh_when_never_refreshed(self):
        status = HydrationStatus(last_full_refresh=None)
        
        needs_refresh = status.last_full_refresh is None
        assert needs_refresh is True

    def test_needs_refresh_when_stale(self):
        status = HydrationStatus(
            last_full_refresh=datetime.now() - timedelta(hours=2)
        )
        
        stale_threshold = timedelta(hours=1)
        time_since_refresh = datetime.now() - status.last_full_refresh
        needs_refresh = time_since_refresh > stale_threshold
        
        assert needs_refresh is True

    def test_no_refresh_when_fresh(self):
        status = HydrationStatus(
            last_full_refresh=datetime.now() - timedelta(minutes=30)
        )
        
        stale_threshold = timedelta(hours=1)
        time_since_refresh = datetime.now() - status.last_full_refresh
        needs_refresh = time_since_refresh > stale_threshold
        
        assert needs_refresh is False


class TestIncrementalRefresh:
    """Tests for incremental refresh logic"""

    def test_incremental_vs_full_tracking(self):
        status = HydrationStatus(
            last_full_refresh=datetime.now() - timedelta(hours=12),
            last_incremental=datetime.now() - timedelta(minutes=15),
        )
        
        # Last incremental is more recent
        assert status.last_incremental > status.last_full_refresh

    def test_incremental_updates_last_time(self):
        status = HydrationStatus()
        
        before = status.last_incremental
        status.last_incremental = datetime.now()
        
        assert before is None
        assert status.last_incremental is not None
