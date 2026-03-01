"""
ACTP Test Fixtures and Factories
=================================
Shared test data factories for all ACTP test modules.
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import List

from services.creative_testing_pipeline.models import (
    AdDeployment,
    AdDeploymentStatus,
    CampaignStatus,
    Creative,
    GenerationSource,
    OrganicPost,
    Platform,
    RoundStatus,
    RoundType,
    TestCampaign,
    TestRound,
    WinnerSelection,
)
from services.creative_testing_pipeline.config import ACTPConfig


# ─── Campaign Factory ────────────────────────────────────

def make_campaign(**overrides) -> TestCampaign:
    defaults = {
        "name": "Test Campaign",
        "offer_name": "Test Offer",
        "offer_url": "https://example.com/offer",
        "angles": ["urgency", "social_proof", "fomo"],
        "mode": "offer",
        "config": ACTPConfig().to_dict(),
    }
    defaults.update(overrides)
    return TestCampaign(**defaults)


# ─── Round Factory ────────────────────────────────────────

def make_round(campaign_id: str = "camp-1", **overrides) -> TestRound:
    defaults = {
        "campaign_id": campaign_id,
        "round_number": 1,
        "round_type": RoundType.ORGANIC,
        "status": RoundStatus.PENDING,
    }
    defaults.update(overrides)
    return TestRound(**defaults)


# ─── Creative Factory ────────────────────────────────────

def make_creative(
    campaign_id: str = "camp-1",
    round_id: str = "round-1",
    **overrides,
) -> Creative:
    defaults = {
        "campaign_id": campaign_id,
        "round_id": round_id,
        "hook": "This changed everything",
        "cta": "Try it free today",
        "angle": "productivity hack",
        "script": "I discovered something that changed how I work forever.",
        "generation_source": GenerationSource.SORA,
        "generation_metadata": {
            "brief": {"style": "ugc", "target_emotion": "curiosity"},
            "provider": "sora",
        },
    }
    defaults.update(overrides)
    return Creative(**defaults)


def make_creatives(count: int = 5, **overrides) -> List[Creative]:
    hooks = [
        "This changed everything",
        "Nobody talks about this",
        "I wish I knew this sooner",
        "Stop doing this wrong",
        "The secret they don't tell you",
    ]
    ctas = [
        "Try it free today",
        "Link in bio",
        "Comment 'yes' for more",
        "Save this for later",
        "Follow for part 2",
    ]
    return [
        make_creative(
            id=f"c{i+1}",
            hook=hooks[i % len(hooks)],
            cta=ctas[i % len(ctas)],
            angle=f"angle_{i+1}",
            **overrides,
        )
        for i in range(count)
    ]


# ─── Organic Post Factory ────────────────────────────────

def make_organic_post(
    creative_id: str = "c1",
    platform: Platform = Platform.TIKTOK,
    views: int = 1000,
    likes: int = 50,
    **overrides,
) -> OrganicPost:
    defaults = {
        "creative_id": creative_id,
        "platform": platform,
        "post_id": f"post_{creative_id}_{platform.value}",
        "post_url": f"https://example.com/{creative_id}",
        "status": "published",
        "posted_at": datetime.now(timezone.utc) - timedelta(hours=24),
        "metrics": {
            "views": views,
            "likes": likes,
            "comments": int(likes * 0.1),
            "shares": int(likes * 0.2),
            "completion_rate": 0.65,
        },
    }
    defaults.update(overrides)
    return OrganicPost(**defaults)


# ─── Ad Deployment Factory ────────────────────────────────

def make_ad_deployment(
    creative_id: str = "c1",
    round_id: str = "round-1",
    **overrides,
) -> AdDeployment:
    defaults = {
        "creative_id": creative_id,
        "round_id": round_id,
        "platform": Platform.META_ADS,
        "budget_cents": 500,
        "spend_cents": 350,
        "status": AdDeploymentStatus.ACTIVE,
        "metrics": {
            "impressions": 5000,
            "clicks": 100,
            "spend_cents": 350,
            "three_second_views": 2500,
            "thru_plays": 1000,
            "conversions": 3,
        },
    }
    defaults.update(overrides)
    return AdDeployment(**defaults)


# ─── Winner Factory ───────────────────────────────────────

def make_winner(
    round_id: str = "round-1",
    creative_id: str = "c1",
    rank: int = 1,
    score: float = 75.0,
    **overrides,
) -> WinnerSelection:
    defaults = {
        "round_id": round_id,
        "creative_id": creative_id,
        "rank": rank,
        "score": score,
        "selection_reason": f"Rank #{rank} with score {score}",
    }
    defaults.update(overrides)
    return WinnerSelection(**defaults)
