"""
ACTP Configuration
==================
All configurable thresholds, budgets, wait times, and platform settings.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OrganicTestConfig:
    """Configuration for organic testing rounds."""
    platforms: List[str] = field(default_factory=lambda: ["youtube_shorts", "tiktok"])
    creatives_per_round: int = 5
    wait_hours: int = 24
    min_views_for_decision: int = 100
    collection_intervals_hours: List[int] = field(default_factory=lambda: [6, 12, 24, 48])


@dataclass
class AdTestConfig:
    """Configuration for ad testing rounds."""
    platforms: List[str] = field(default_factory=lambda: ["meta", "tiktok_ads"])
    budget_per_creative_cents: int = 500  # $5
    wait_hours: int = 48
    min_impressions_for_decision: int = 1000
    objective: str = "CONVERSIONS"


@dataclass
class ScalingConfig:
    """Configuration for budget scaling."""
    budget_tiers_cents: List[int] = field(default_factory=lambda: [500, 2000, 5000, 10000])
    scale_threshold_ctr: float = 1.5  # % CTR to scale up
    pause_threshold_ctr: float = 0.5  # % CTR to pause
    min_impressions_before_action: int = 100


@dataclass
class VideoGenerationConfig:
    """Configuration for video generation."""
    providers: List[str] = field(default_factory=lambda: ["sora", "veo3", "nano_banana"])
    default_provider: str = "sora"
    default_duration_seconds: int = 15
    aspect_ratio: str = "9:16"
    variations_per_angle: int = 3
    sora_model: str = "sora-2"
    sora_size: str = "720x1280"


@dataclass
class IterationConfig:
    """Configuration for iteration rounds."""
    max_rounds: int = 10
    strategies: List[str] = field(default_factory=lambda: ["hook_swap", "cta_swap", "ai_remix"])
    winner_count: int = 3
    diversity_threshold: float = 0.3  # Minimum diversity between variations


@dataclass
class ScoringWeights:
    """Weights for scoring algorithms."""
    # Organic scoring weights
    organic_engagement_rate: float = 0.3
    organic_view_velocity: float = 0.3
    organic_completion_rate: float = 0.25
    organic_comment_sentiment: float = 0.15

    # Ad scoring weights
    ad_ctr: float = 0.25
    ad_cpc_efficiency: float = 0.2
    ad_hook_rate: float = 0.25
    ad_hold_rate: float = 0.2
    ad_conversion_rate: float = 0.1


@dataclass
class ACTPConfig:
    """Master configuration for the Ad Creative Testing Pipeline."""
    organic_test: OrganicTestConfig = field(default_factory=OrganicTestConfig)
    ad_test: AdTestConfig = field(default_factory=AdTestConfig)
    scaling: ScalingConfig = field(default_factory=ScalingConfig)
    video_generation: VideoGenerationConfig = field(default_factory=VideoGenerationConfig)
    iteration: IterationConfig = field(default_factory=IterationConfig)
    scoring: ScoringWeights = field(default_factory=ScoringWeights)

    @classmethod
    def from_dict(cls, data: dict) -> "ACTPConfig":
        """Create config from dictionary, merging with defaults."""
        config = cls()
        if "organic_test" in data:
            for k, v in data["organic_test"].items():
                if hasattr(config.organic_test, k):
                    setattr(config.organic_test, k, v)
        if "ad_test" in data:
            for k, v in data["ad_test"].items():
                if hasattr(config.ad_test, k):
                    setattr(config.ad_test, k, v)
        if "scaling" in data:
            for k, v in data["scaling"].items():
                if hasattr(config.scaling, k):
                    setattr(config.scaling, k, v)
        if "video_generation" in data:
            for k, v in data["video_generation"].items():
                if hasattr(config.video_generation, k):
                    setattr(config.video_generation, k, v)
        if "iteration" in data:
            for k, v in data["iteration"].items():
                if hasattr(config.iteration, k):
                    setattr(config.iteration, k, v)
        if "scoring" in data:
            for k, v in data["scoring"].items():
                if hasattr(config.scoring, k):
                    setattr(config.scoring, k, v)
        return config

    def to_dict(self) -> dict:
        """Serialize config to dictionary."""
        from dataclasses import asdict
        return asdict(self)
