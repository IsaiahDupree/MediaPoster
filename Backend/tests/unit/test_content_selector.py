"""
Unit tests for AI Content Selection Service (NAR-005)
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from services.narrative_scheduler.content_selector import (
    ContentSelector,
    SelectionCriteria,
    ContentCandidate,
    SelectionResult
)


@pytest.fixture
def mock_openai():
    """Mock OpenAI client"""
    mock_client = Mock()
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    return mock_client


@pytest.fixture
def sample_candidate():
    """Sample content candidate"""
    return ContentCandidate(
        content_id="content-123",
        title="DIY Arduino Project Tutorial",
        description="Learn to build your first Arduino project",
        transcript="Welcome to this Arduino tutorial...",
        duration_seconds=120,
        format="video",
        platform="youtube",
        sentiment="positive",
        topics=["arduino", "electronics", "tutorial", "diy"],
        keywords=["arduino", "electronics", "beginner", "project"],
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
        last_used=None,
        previous_performance=None
    )


@pytest.fixture
def sample_criteria():
    """Sample selection criteria"""
    return SelectionCriteria(
        pillar_id="pillar-123",
        pillar_name="Pain Points",
        pillar_type="value",
        pillar_keywords=["arduino", "beginner", "struggle", "help"],
        goal_statement="Position as the go-to expert for DIY electronics",
        target_audience="Beginner makers aged 25-45",
        primary_cta="Waitlist",
        platform="tiktok",
        max_duration_seconds=180,
        min_duration_seconds=30,
        exclude_content_ids=[],
        diversity_window_days=7
    )


class TestContentSelectorCore:
    """Test core functionality"""

    def test_singleton_pattern(self):
        """Test that ContentSelector follows singleton pattern"""
        ContentSelector._instance = None

        selector1 = ContentSelector.get_instance()
        selector2 = ContentSelector.get_instance()

        assert selector1 is selector2

    @pytest.mark.asyncio
    async def test_start(self):
        """Test service start"""
        ContentSelector._instance = None
        selector = ContentSelector()

        with patch.object(selector, '_ensure_tables_exist', AsyncMock()):
            with patch.object(selector.event_bus, 'publish', AsyncMock()):
                await selector.start()


class TestContentSelection:
    """Test content selection logic"""

    @pytest.mark.asyncio
    async def test_select_content_no_candidates(self):
        """Test selection when no candidates available"""
        ContentSelector._instance = None
        selector = ContentSelector()

        slot = {
            "id": "slot-123",
            "pillar_id": "pillar-123",
            "pillar_name": "Pain Points",
            "platform": "tiktok"
        }

        with patch.object(selector, '_build_criteria', AsyncMock(return_value=Mock())):
            with patch.object(selector, '_get_candidates', AsyncMock(return_value=[])):
                result = await selector.select_content_for_slot(slot)
                assert result is None

    @pytest.mark.asyncio
    async def test_select_content_success(self, sample_candidate, sample_criteria):
        """Test successful content selection"""
        ContentSelector._instance = None
        selector = ContentSelector()

        slot = {
            "id": "slot-123",
            "pillar_id": "pillar-123",
            "pillar_name": "Pain Points"
        }

        mock_score = SelectionResult(
            content_id=sample_candidate.content_id,
            score=0.85,
            reasoning="Strong alignment with pain points pillar",
            pillar_alignment=0.8,
            goal_alignment=0.9,
            freshness_score=1.0,
            diversity_score=0.8,
            metadata={}
        )

        with patch.object(selector, '_build_criteria', AsyncMock(return_value=sample_criteria)):
            with patch.object(selector, '_get_candidates', AsyncMock(return_value=[sample_candidate])):
                with patch.object(selector, '_score_candidate', AsyncMock(return_value=mock_score)):
                    with patch.object(selector, '_log_selection', AsyncMock()):
                        with patch.object(selector.event_bus, 'publish', AsyncMock()):
                            result = await selector.select_content_for_slot(slot)

                            assert result is not None
                            assert result["content_id"] == sample_candidate.content_id
                            assert result["score"] == 0.85
                            assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_select_content_below_threshold(self, sample_candidate, sample_criteria):
        """Test selection when score is below threshold"""
        ContentSelector._instance = None
        selector = ContentSelector()
        selector.min_selection_score = 0.7

        slot = {"id": "slot-123", "pillar_id": "pillar-123"}

        mock_score = SelectionResult(
            content_id=sample_candidate.content_id,
            score=0.5,  # Below threshold
            reasoning="Weak alignment",
            pillar_alignment=0.5,
            goal_alignment=0.5,
            freshness_score=0.5,
            diversity_score=0.5,
            metadata={}
        )

        with patch.object(selector, '_build_criteria', AsyncMock(return_value=sample_criteria)):
            with patch.object(selector, '_get_candidates', AsyncMock(return_value=[sample_candidate])):
                with patch.object(selector, '_score_candidate', AsyncMock(return_value=mock_score)):
                    result = await selector.select_content_for_slot(slot)
                    assert result is None


class TestScoringLogic:
    """Test content scoring logic"""

    @pytest.mark.asyncio
    async def test_calculate_pillar_alignment(self, sample_candidate, sample_criteria):
        """Test pillar alignment calculation"""
        ContentSelector._instance = None
        selector = ContentSelector()

        score = await selector._calculate_pillar_alignment(sample_candidate, sample_criteria)

        # Should have some overlap with keywords
        assert 0.0 <= score <= 1.0
        # Should be positive since there's keyword overlap (arduino, beginner)
        assert score > 0.3

    @pytest.mark.asyncio
    async def test_calculate_goal_alignment_with_ai(self, sample_candidate, sample_criteria, mock_openai):
        """Test goal alignment with AI"""
        ContentSelector._instance = None
        selector = ContentSelector()

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="0.85"))]
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(selector, 'openai_client', mock_openai):
            score = await selector._calculate_goal_alignment(sample_candidate, sample_criteria)
            assert score == 0.85

    @pytest.mark.asyncio
    async def test_calculate_goal_alignment_ai_fallback(self, sample_candidate, sample_criteria, mock_openai):
        """Test goal alignment fallback when AI fails"""
        ContentSelector._instance = None
        selector = ContentSelector()

        # Mock AI failure
        mock_openai.chat.completions.create = AsyncMock(side_effect=Exception("API error"))

        with patch.object(selector, 'openai_client', mock_openai):
            score = await selector._calculate_goal_alignment(sample_candidate, sample_criteria)
            assert score == 0.5  # Fallback score

    def test_calculate_freshness_never_used(self, sample_candidate):
        """Test freshness score for never-used content"""
        ContentSelector._instance = None
        selector = ContentSelector()

        sample_candidate.last_used = None
        score = selector._calculate_freshness(sample_candidate)
        assert score == 1.0

    def test_calculate_freshness_recently_used(self, sample_candidate):
        """Test freshness score for recently used content"""
        ContentSelector._instance = None
        selector = ContentSelector()

        sample_candidate.last_used = datetime.now(timezone.utc) - timedelta(days=2)
        score = selector._calculate_freshness(sample_candidate)
        assert score < 0.5  # Should be low for recent use

    def test_calculate_freshness_long_ago(self, sample_candidate):
        """Test freshness score for content used long ago"""
        ContentSelector._instance = None
        selector = ContentSelector()

        sample_candidate.last_used = datetime.now(timezone.utc) - timedelta(days=35)
        score = selector._calculate_freshness(sample_candidate)
        assert score == 1.0  # Should be maximum for old content


class TestAIReasoning:
    """Test AI reasoning generation"""

    @pytest.mark.asyncio
    async def test_get_ai_reasoning_success(self, sample_candidate, sample_criteria, mock_openai):
        """Test successful AI reasoning generation"""
        ContentSelector._instance = None
        selector = ContentSelector()

        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Content addresses beginner struggles with Arduino"))
        ]
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(selector, 'openai_client', mock_openai):
            reasoning = await selector._get_ai_reasoning(sample_candidate, sample_criteria)
            assert "Arduino" in reasoning or "beginner" in reasoning.lower()

    @pytest.mark.asyncio
    async def test_get_ai_reasoning_fallback(self, sample_candidate, sample_criteria, mock_openai):
        """Test AI reasoning fallback"""
        ContentSelector._instance = None
        selector = ContentSelector()

        mock_openai.chat.completions.create = AsyncMock(side_effect=Exception("API error"))

        with patch.object(selector, 'openai_client', mock_openai):
            reasoning = await selector._get_ai_reasoning(sample_candidate, sample_criteria)
            assert "Pain Points" in reasoning  # Should use fallback


class TestCriteriaBuilding:
    """Test criteria building"""

    @pytest.mark.asyncio
    async def test_build_criteria(self):
        """Test building selection criteria from slot"""
        ContentSelector._instance = None
        selector = ContentSelector()

        slot = {
            "id": "slot-123",
            "pillar_id": "pillar-123",
            "platform": "tiktok",
            "max_duration": 180
        }

        mock_pillar = {
            "id": "pillar-123",
            "goal_id": "goal-456",
            "name": "Pain Points",
            "pillar_type": "value",
            "keywords": ["arduino", "help"]
        }

        mock_goal = {
            "id": "goal-456",
            "goal_statement": "Be the Arduino expert",
            "primary_cta": "Waitlist",
            "target_audience": "Beginners"
        }

        with patch.object(selector, '_get_pillar', AsyncMock(return_value=mock_pillar)):
            with patch.object(selector, '_get_goal', AsyncMock(return_value=mock_goal)):
                with patch.object(selector, '_get_recently_used_content', AsyncMock(return_value=[])):
                    criteria = await selector._build_criteria(slot)

                    assert criteria.pillar_id == "pillar-123"
                    assert criteria.pillar_name == "Pain Points"
                    assert criteria.goal_statement == "Be the Arduino expert"
                    assert criteria.platform == "tiktok"
                    assert criteria.max_duration_seconds == 180


class TestDatabaseOperations:
    """Test database operations"""

    @pytest.mark.asyncio
    async def test_log_selection(self, sample_candidate, sample_criteria):
        """Test logging selection to database"""
        ContentSelector._instance = None
        selector = ContentSelector()

        slot = {"id": "slot-123", "pillar_id": "pillar-123"}

        score = SelectionResult(
            content_id=sample_candidate.content_id,
            score=0.85,
            reasoning="Test reasoning",
            pillar_alignment=0.8,
            goal_alignment=0.9,
            freshness_score=1.0,
            diversity_score=0.8,
            metadata={}
        )

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_engine.connect.return_value.__exit__.return_value = None

        with patch.object(selector, 'engine', mock_engine):
            await selector._log_selection(slot, sample_candidate, score)

            # Verify database insert was called
            mock_conn.execute.assert_called_once()
            mock_conn.commit.assert_called_once()
