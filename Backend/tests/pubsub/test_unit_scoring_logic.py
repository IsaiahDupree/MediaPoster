"""
Unit Tests: Scoring and Selection Logic
========================================
Test pillar mix, constraints, thresholds without any broker/DB.

These tests verify:
- Pillar distribution calculations
- Constraint satisfaction checking
- Threshold-based filtering
- Video selection scoring
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from datetime import datetime, date, timedelta
from enum import Enum


@dataclass
class Pillar:
    """Content pillar definition."""
    id: str
    name: str
    target_percentage: float  # 0.0 to 1.0
    min_posts_per_week: int = 0
    max_posts_per_week: int = 10
    keywords: List[str] = field(default_factory=list)


@dataclass
class VideoCandidate:
    """Video available for scheduling."""
    id: str
    pillar_id: Optional[str] = None
    viral_score: float = 0.0
    duration_seconds: float = 60.0
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    is_published: bool = False


@dataclass
class SchedulingConstraints:
    """Scheduling constraints."""
    min_posts_per_day: int = 1
    max_posts_per_day: int = 5
    min_gap_hours: int = 2
    blackout_hours: List[int] = field(default_factory=list)  # Hours to avoid
    preferred_hours: List[int] = field(default_factory=lambda: [9, 12, 18, 21])
    min_viral_score: float = 0.0
    max_video_age_days: int = 365


class PillarDistributionCalculator:
    """Calculate and validate pillar distribution."""
    
    @staticmethod
    def calculate_distribution(videos: List[VideoCandidate], pillars: List[Pillar]) -> Dict[str, float]:
        """Calculate current distribution across pillars."""
        if not videos:
            return {p.id: 0.0 for p in pillars}
        
        counts = {p.id: 0 for p in pillars}
        for video in videos:
            if video.pillar_id in counts:
                counts[video.pillar_id] += 1
        
        total = len(videos)
        return {pid: count / total for pid, count in counts.items()}
    
    @staticmethod
    def get_deviation(actual: Dict[str, float], targets: Dict[str, float]) -> float:
        """Calculate total deviation from target distribution."""
        deviation = 0.0
        for pillar_id, target in targets.items():
            actual_pct = actual.get(pillar_id, 0.0)
            deviation += abs(target - actual_pct)
        return deviation
    
    @staticmethod
    def get_underrepresented_pillars(
        actual: Dict[str, float], 
        targets: Dict[str, float],
        threshold: float = 0.1
    ) -> List[str]:
        """Get pillars that are underrepresented by more than threshold."""
        underrepresented = []
        for pillar_id, target in targets.items():
            actual_pct = actual.get(pillar_id, 0.0)
            if target - actual_pct > threshold:
                underrepresented.append(pillar_id)
        return underrepresented


class ConstraintChecker:
    """Check if videos/schedules satisfy constraints."""
    
    def __init__(self, constraints: SchedulingConstraints):
        self.constraints = constraints
    
    def check_video(self, video: VideoCandidate) -> tuple[bool, List[str]]:
        """Check if a video satisfies constraints. Returns (passed, reasons)."""
        reasons = []
        
        # Viral score check
        if video.viral_score < self.constraints.min_viral_score:
            reasons.append(f"Viral score {video.viral_score} below minimum {self.constraints.min_viral_score}")
        
        # Age check
        age_days = (datetime.now() - video.created_at).days
        if age_days > self.constraints.max_video_age_days:
            reasons.append(f"Video age {age_days} days exceeds maximum {self.constraints.max_video_age_days}")
        
        # Already published check
        if video.is_published:
            reasons.append("Video already published")
        
        return len(reasons) == 0, reasons
    
    def check_slot_time(self, hour: int) -> tuple[bool, List[str]]:
        """Check if a time slot is valid."""
        reasons = []
        
        if hour in self.constraints.blackout_hours:
            reasons.append(f"Hour {hour} is in blackout period")
        
        return len(reasons) == 0, reasons
    
    def check_daily_limit(self, posts_today: int) -> tuple[bool, str]:
        """Check if daily posting limit allows another post."""
        if posts_today >= self.constraints.max_posts_per_day:
            return False, f"Daily limit of {self.constraints.max_posts_per_day} reached"
        return True, ""


class VideoScorer:
    """Score videos for selection priority."""
    
    def __init__(
        self,
        viral_weight: float = 0.4,
        freshness_weight: float = 0.3,
        pillar_need_weight: float = 0.3
    ):
        self.viral_weight = viral_weight
        self.freshness_weight = freshness_weight
        self.pillar_need_weight = pillar_need_weight
    
    def score(
        self,
        video: VideoCandidate,
        pillar_need_scores: Dict[str, float],  # Higher = more needed
        max_age_days: int = 30
    ) -> float:
        """Calculate selection priority score for a video."""
        # Viral component (0-1)
        viral_score = min(video.viral_score / 100, 1.0)
        
        # Freshness component (0-1, newer = higher)
        age_days = (datetime.now() - video.created_at).days
        freshness_score = max(0, 1 - (age_days / max_age_days))
        
        # Pillar need component (0-1)
        pillar_need = pillar_need_scores.get(video.pillar_id, 0.5)
        
        total = (
            viral_score * self.viral_weight +
            freshness_score * self.freshness_weight +
            pillar_need * self.pillar_need_weight
        )
        
        return round(total, 4)
    
    def rank_videos(
        self,
        videos: List[VideoCandidate],
        pillar_need_scores: Dict[str, float]
    ) -> List[tuple[VideoCandidate, float]]:
        """Rank videos by score, highest first."""
        scored = [(v, self.score(v, pillar_need_scores)) for v in videos]
        return sorted(scored, key=lambda x: x[1], reverse=True)


class TestPillarDistribution:
    """Test pillar distribution calculations."""
    
    @pytest.fixture
    def pillars(self):
        return [
            Pillar(id="education", name="Education", target_percentage=0.4),
            Pillar(id="entertainment", name="Entertainment", target_percentage=0.35),
            Pillar(id="promotion", name="Promotion", target_percentage=0.25),
        ]
    
    def test_empty_videos_returns_zero_distribution(self, pillars):
        """Empty video list should return 0% for all pillars."""
        dist = PillarDistributionCalculator.calculate_distribution([], pillars)
        assert all(v == 0.0 for v in dist.values())
    
    def test_single_pillar_100_percent(self, pillars):
        """Single pillar videos should be 100% that pillar."""
        videos = [
            VideoCandidate(id="1", pillar_id="education"),
            VideoCandidate(id="2", pillar_id="education"),
        ]
        dist = PillarDistributionCalculator.calculate_distribution(videos, pillars)
        assert dist["education"] == 1.0
        assert dist["entertainment"] == 0.0
    
    def test_even_distribution(self, pillars):
        """Even distribution across 3 pillars."""
        videos = [
            VideoCandidate(id="1", pillar_id="education"),
            VideoCandidate(id="2", pillar_id="entertainment"),
            VideoCandidate(id="3", pillar_id="promotion"),
        ]
        dist = PillarDistributionCalculator.calculate_distribution(videos, pillars)
        assert abs(dist["education"] - 0.333) < 0.01
        assert abs(dist["entertainment"] - 0.333) < 0.01
        assert abs(dist["promotion"] - 0.333) < 0.01
    
    def test_deviation_from_target(self, pillars):
        """Calculate deviation from target distribution."""
        actual = {"education": 0.5, "entertainment": 0.3, "promotion": 0.2}
        targets = {"education": 0.4, "entertainment": 0.35, "promotion": 0.25}
        
        deviation = PillarDistributionCalculator.get_deviation(actual, targets)
        # |0.5-0.4| + |0.3-0.35| + |0.2-0.25| = 0.1 + 0.05 + 0.05 = 0.2
        assert abs(deviation - 0.2) < 0.01
    
    def test_underrepresented_pillars(self, pillars):
        """Identify underrepresented pillars."""
        actual = {"education": 0.2, "entertainment": 0.6, "promotion": 0.2}
        targets = {"education": 0.4, "entertainment": 0.35, "promotion": 0.25}
        
        underrep = PillarDistributionCalculator.get_underrepresented_pillars(
            actual, targets, threshold=0.1
        )
        assert "education" in underrep  # 0.4 - 0.2 = 0.2 > 0.1
        assert "entertainment" not in underrep  # Over-represented


class TestConstraintChecker:
    """Test constraint satisfaction checking."""
    
    @pytest.fixture
    def constraints(self):
        return SchedulingConstraints(
            min_posts_per_day=1,
            max_posts_per_day=3,
            min_viral_score=50.0,
            max_video_age_days=30,
            blackout_hours=[2, 3, 4, 5],
        )
    
    def test_video_passes_all_constraints(self, constraints):
        """Video meeting all constraints should pass."""
        checker = ConstraintChecker(constraints)
        video = VideoCandidate(
            id="1",
            viral_score=75.0,
            created_at=datetime.now() - timedelta(days=7),
            is_published=False,
        )
        passed, reasons = checker.check_video(video)
        assert passed is True
        assert len(reasons) == 0
    
    def test_video_fails_viral_score(self, constraints):
        """Video with low viral score should fail."""
        checker = ConstraintChecker(constraints)
        video = VideoCandidate(id="1", viral_score=30.0)
        passed, reasons = checker.check_video(video)
        assert passed is False
        assert any("Viral score" in r for r in reasons)
    
    def test_video_fails_age(self, constraints):
        """Old video should fail."""
        checker = ConstraintChecker(constraints)
        video = VideoCandidate(
            id="1",
            viral_score=75.0,
            created_at=datetime.now() - timedelta(days=60),
        )
        passed, reasons = checker.check_video(video)
        assert passed is False
        assert any("age" in r for r in reasons)
    
    def test_video_fails_already_published(self, constraints):
        """Published video should fail."""
        checker = ConstraintChecker(constraints)
        video = VideoCandidate(id="1", viral_score=75.0, is_published=True)
        passed, reasons = checker.check_video(video)
        assert passed is False
        assert any("published" in r for r in reasons)
    
    def test_blackout_hours_rejected(self, constraints):
        """Blackout hours should be rejected."""
        checker = ConstraintChecker(constraints)
        passed, reasons = checker.check_slot_time(3)
        assert passed is False
        assert any("blackout" in r for r in reasons)
    
    def test_normal_hours_accepted(self, constraints):
        """Normal hours should be accepted."""
        checker = ConstraintChecker(constraints)
        passed, _ = checker.check_slot_time(12)
        assert passed is True
    
    def test_daily_limit_check(self, constraints):
        """Daily limit should be enforced."""
        checker = ConstraintChecker(constraints)
        
        passed, _ = checker.check_daily_limit(2)
        assert passed is True
        
        passed, reason = checker.check_daily_limit(3)
        assert passed is False
        assert "limit" in reason


class TestVideoScorer:
    """Test video scoring logic."""
    
    @pytest.fixture
    def scorer(self):
        return VideoScorer(
            viral_weight=0.4,
            freshness_weight=0.3,
            pillar_need_weight=0.3,
        )
    
    def test_high_viral_score_ranks_higher(self, scorer):
        """Higher viral score should rank higher."""
        pillar_needs = {"education": 0.5}
        
        high_viral = VideoCandidate(id="1", pillar_id="education", viral_score=90)
        low_viral = VideoCandidate(id="2", pillar_id="education", viral_score=30)
        
        high_score = scorer.score(high_viral, pillar_needs)
        low_score = scorer.score(low_viral, pillar_needs)
        
        assert high_score > low_score
    
    def test_fresher_video_ranks_higher(self, scorer):
        """Fresher videos should rank higher (all else equal)."""
        pillar_needs = {"education": 0.5}
        
        fresh = VideoCandidate(
            id="1", pillar_id="education", viral_score=70,
            created_at=datetime.now() - timedelta(days=1)
        )
        old = VideoCandidate(
            id="2", pillar_id="education", viral_score=70,
            created_at=datetime.now() - timedelta(days=25)
        )
        
        fresh_score = scorer.score(fresh, pillar_needs)
        old_score = scorer.score(old, pillar_needs)
        
        assert fresh_score > old_score
    
    def test_needed_pillar_ranks_higher(self, scorer):
        """Videos from needed pillars should rank higher."""
        pillar_needs = {
            "education": 0.9,  # Very needed
            "entertainment": 0.2,  # Not needed
        }
        
        needed = VideoCandidate(id="1", pillar_id="education", viral_score=70)
        not_needed = VideoCandidate(id="2", pillar_id="entertainment", viral_score=70)
        
        needed_score = scorer.score(needed, pillar_needs)
        not_needed_score = scorer.score(not_needed, pillar_needs)
        
        assert needed_score > not_needed_score
    
    def test_ranking_returns_sorted_list(self, scorer):
        """Ranking should return videos sorted by score descending."""
        pillar_needs = {"education": 0.5}
        
        videos = [
            VideoCandidate(id="1", pillar_id="education", viral_score=30),
            VideoCandidate(id="2", pillar_id="education", viral_score=90),
            VideoCandidate(id="3", pillar_id="education", viral_score=60),
        ]
        
        ranked = scorer.rank_videos(videos, pillar_needs)
        
        # Should be sorted by score descending
        scores = [score for _, score in ranked]
        assert scores == sorted(scores, reverse=True)
        assert ranked[0][0].id == "2"  # Highest viral score first
