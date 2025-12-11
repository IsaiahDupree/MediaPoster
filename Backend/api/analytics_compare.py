"""
Analytics Comparison API
Compare accounts on same platform or across different platforms
Includes audience segmentation comparison
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

router = APIRouter(prefix="/api/analytics-compare", tags=["Analytics Compare"])


class CompareMode(str, Enum):
    CROSS_PLATFORM = "platforms"
    SAME_PLATFORM = "accounts"
    TIME_PERIODS = "time"


class AudienceDemographics(BaseModel):
    """Audience demographic breakdown"""
    age_distribution: Dict[str, float]  # e.g., {"18-24": 25.5, "25-34": 40.2}
    gender_distribution: Dict[str, float]  # e.g., {"male": 45, "female": 52, "other": 3}
    top_countries: List[Dict[str, Any]]  # [{"country": "US", "percent": 42}]
    top_cities: List[Dict[str, Any]]  # [{"city": "New York", "percent": 8}]


class AccountMetrics(BaseModel):
    """Metrics for a single account"""
    account_id: str
    platform: str
    username: str
    display_name: str
    period: str
    
    # Follower metrics
    followers: int
    follower_growth: int
    follower_growth_percent: float
    
    # Content metrics
    posts: int
    total_reach: int
    total_impressions: int
    total_engagement: int
    engagement_rate: float
    
    # Averages
    avg_reach_per_post: int
    avg_engagement_per_post: int
    avg_likes_per_post: int
    avg_comments_per_post: int
    avg_shares_per_post: int
    
    # Content insights
    top_post_type: str
    best_posting_time: str
    best_posting_day: str
    
    # Audience
    audience_demographics: AudienceDemographics


class ComparisonInsight(BaseModel):
    """AI-generated insight from comparison"""
    type: str  # "winner", "opportunity", "trend", "warning"
    title: str
    description: str
    metric: str
    accounts_involved: List[str]


class ComparisonRecommendation(BaseModel):
    """Actionable recommendation from comparison"""
    priority: str  # "high", "medium", "low"
    title: str
    description: str
    action: str
    target_account: Optional[str]


class ComparisonResult(BaseModel):
    """Complete comparison result"""
    mode: CompareMode
    period: str
    accounts: List[AccountMetrics]
    insights: List[ComparisonInsight]
    recommendations: List[ComparisonRecommendation]
    audience_overlap: Optional[Dict[str, Any]] = None


class TimePeriodComparison(BaseModel):
    """Compare same account across time periods"""
    account_id: str
    periods: List[AccountMetrics]
    trends: Dict[str, str]  # metric -> "up", "down", "stable"
    growth_forecast: Dict[str, float]


# Helper functions

def calculate_engagement_rate(likes: int, comments: int, shares: int, reach: int) -> float:
    """Calculate engagement rate"""
    if reach == 0:
        return 0.0
    return ((likes + comments + shares) / reach) * 100


def get_mock_account_metrics(account_id: str, platform: str, period_days: int = 30) -> AccountMetrics:
    """Generate mock metrics for demo purposes"""
    import random
    
    base_followers = random.randint(1000, 100000)
    engagement_base = {
        "instagram": 5.0,
        "tiktok": 8.0,
        "youtube": 3.0,
        "facebook": 2.0,
        "linkedin": 4.0,
        "twitter": 2.5,
    }
    
    followers = base_followers
    growth = int(followers * random.uniform(0.02, 0.15))
    posts = random.randint(10, 50)
    reach = followers * random.randint(2, 6)
    engagement = int(reach * random.uniform(0.03, 0.12))
    
    return AccountMetrics(
        account_id=account_id,
        platform=platform,
        username=f"user_{account_id[:8]}",
        display_name=f"Account {account_id[:8]}",
        period=f"Last {period_days} days",
        followers=followers,
        follower_growth=growth,
        follower_growth_percent=(growth / followers) * 100,
        posts=posts,
        total_reach=reach,
        total_impressions=int(reach * 1.5),
        total_engagement=engagement,
        engagement_rate=engagement_base.get(platform, 3.0) + random.uniform(-1, 3),
        avg_reach_per_post=reach // posts,
        avg_engagement_per_post=engagement // posts,
        avg_likes_per_post=int(engagement * 0.7 / posts),
        avg_comments_per_post=int(engagement * 0.2 / posts),
        avg_shares_per_post=int(engagement * 0.1 / posts),
        top_post_type=random.choice(["Reels", "Carousel", "Single Image", "Video", "Story"]),
        best_posting_time=random.choice(["7:00 PM", "12:00 PM", "9:00 AM", "6:00 PM"]),
        best_posting_day=random.choice(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]),
        audience_demographics=AudienceDemographics(
            age_distribution={
                "13-17": random.uniform(2, 8),
                "18-24": random.uniform(15, 35),
                "25-34": random.uniform(25, 45),
                "35-44": random.uniform(10, 25),
                "45-54": random.uniform(5, 15),
                "55+": random.uniform(2, 10),
            },
            gender_distribution={
                "male": random.uniform(35, 55),
                "female": random.uniform(40, 60),
                "other": random.uniform(1, 5),
            },
            top_countries=[
                {"country": "United States", "percent": random.uniform(30, 50)},
                {"country": "United Kingdom", "percent": random.uniform(10, 20)},
                {"country": "Canada", "percent": random.uniform(5, 15)},
                {"country": "Germany", "percent": random.uniform(3, 10)},
                {"country": "Australia", "percent": random.uniform(2, 8)},
            ],
            top_cities=[
                {"city": "New York", "percent": random.uniform(5, 12)},
                {"city": "Los Angeles", "percent": random.uniform(4, 10)},
                {"city": "London", "percent": random.uniform(3, 8)},
                {"city": "Toronto", "percent": random.uniform(2, 6)},
                {"city": "Chicago", "percent": random.uniform(2, 5)},
            ],
        ),
    )


def generate_insights(accounts: List[AccountMetrics]) -> List[ComparisonInsight]:
    """Generate AI insights from account comparison"""
    insights = []
    
    if len(accounts) < 2:
        return insights
    
    # Find best engagement
    best_engagement = max(accounts, key=lambda a: a.engagement_rate)
    insights.append(ComparisonInsight(
        type="winner",
        title="Highest Engagement Rate",
        description=f"{best_engagement.display_name} on {best_engagement.platform} leads with {best_engagement.engagement_rate:.1f}% engagement rate",
        metric="engagement_rate",
        accounts_involved=[best_engagement.account_id],
    ))
    
    # Find fastest growing
    fastest_growth = max(accounts, key=lambda a: a.follower_growth_percent)
    insights.append(ComparisonInsight(
        type="trend",
        title="Fastest Growing Account",
        description=f"{fastest_growth.display_name} is growing at +{fastest_growth.follower_growth_percent:.1f}% this period",
        metric="follower_growth_percent",
        accounts_involved=[fastest_growth.account_id],
    ))
    
    # Find best reach
    best_reach = max(accounts, key=lambda a: a.avg_reach_per_post)
    insights.append(ComparisonInsight(
        type="winner",
        title="Best Reach per Post",
        description=f"{best_reach.display_name} averages {best_reach.avg_reach_per_post:,} reach per post",
        metric="avg_reach_per_post",
        accounts_involved=[best_reach.account_id],
    ))
    
    # Find underperformers
    avg_engagement = sum(a.engagement_rate for a in accounts) / len(accounts)
    underperformers = [a for a in accounts if a.engagement_rate < avg_engagement * 0.7]
    for account in underperformers:
        insights.append(ComparisonInsight(
            type="warning",
            title="Below Average Engagement",
            description=f"{account.display_name} has {account.engagement_rate:.1f}% engagement, below the average of {avg_engagement:.1f}%",
            metric="engagement_rate",
            accounts_involved=[account.account_id],
        ))
    
    return insights


def generate_recommendations(accounts: List[AccountMetrics]) -> List[ComparisonRecommendation]:
    """Generate actionable recommendations from comparison"""
    recommendations = []
    
    if len(accounts) < 2:
        return recommendations
    
    # Cross-pollinate content strategies
    best_engagement = max(accounts, key=lambda a: a.engagement_rate)
    for account in accounts:
        if account.account_id != best_engagement.account_id:
            recommendations.append(ComparisonRecommendation(
                priority="high",
                title=f"Adopt {best_engagement.top_post_type} format",
                description=f"{best_engagement.display_name} performs well with {best_engagement.top_post_type}. Try this format on {account.display_name}.",
                action=f"Create {best_engagement.top_post_type} content for {account.platform}",
                target_account=account.account_id,
            ))
            break
    
    # Posting time recommendations
    posting_times = {a.best_posting_time for a in accounts}
    if len(posting_times) < len(accounts):
        common_time = max(set(a.best_posting_time for a in accounts), key=lambda t: sum(1 for a in accounts if a.best_posting_time == t))
        recommendations.append(ComparisonRecommendation(
            priority="medium",
            title=f"Synchronized posting at {common_time}",
            description=f"Multiple accounts perform best at {common_time}. Consider synchronized cross-platform posting.",
            action="Set up cross-platform scheduled posts",
            target_account=None,
        ))
    
    # Audience overlap recommendation
    recommendations.append(ComparisonRecommendation(
        priority="medium",
        title="Leverage audience overlap",
        description="Your audiences share similar demographics (25-34 age group). Repurpose content across platforms.",
        action="Create platform-optimized versions of top content",
        target_account=None,
    ))
    
    # Growth opportunity
    lowest_growth = min(accounts, key=lambda a: a.follower_growth_percent)
    recommendations.append(ComparisonRecommendation(
        priority="high",
        title=f"Boost growth on {lowest_growth.platform}",
        description=f"{lowest_growth.display_name} is growing slowest at +{lowest_growth.follower_growth_percent:.1f}%. Increase posting frequency or try new content types.",
        action="Increase post frequency and experiment with formats",
        target_account=lowest_growth.account_id,
    ))
    
    return recommendations


def calculate_audience_overlap(accounts: List[AccountMetrics]) -> Dict[str, Any]:
    """Calculate audience overlap between accounts"""
    if len(accounts) < 2:
        return {}
    
    # Calculate demographic similarities
    age_similarity = {}
    for age_group in ["18-24", "25-34", "35-44"]:
        values = [a.audience_demographics.age_distribution.get(age_group, 0) for a in accounts]
        if values:
            avg = sum(values) / len(values)
            variance = sum((v - avg) ** 2 for v in values) / len(values)
            similarity = max(0, 100 - (variance * 2))  # Higher variance = lower similarity
            age_similarity[age_group] = round(similarity, 1)
    
    # Calculate country overlap
    all_countries = set()
    for a in accounts:
        for c in a.audience_demographics.top_countries:
            all_countries.add(c["country"])
    
    country_overlap = []
    for country in list(all_countries)[:5]:
        values = []
        for a in accounts:
            for c in a.audience_demographics.top_countries:
                if c["country"] == country:
                    values.append({"account": a.account_id, "percent": c["percent"]})
                    break
        if values:
            country_overlap.append({"country": country, "accounts": values})
    
    return {
        "age_similarity": age_similarity,
        "country_overlap": country_overlap,
        "overall_similarity": round(sum(age_similarity.values()) / len(age_similarity), 1) if age_similarity else 0,
    }


# API Endpoints

@router.get("/accounts")
async def list_connected_accounts():
    """List all connected accounts available for comparison"""
    # In production, fetch from database
    return [
        {"id": "ig1", "platform": "instagram", "username": "yourbrand", "display_name": "Your Brand", "followers": 12500},
        {"id": "ig2", "platform": "instagram", "username": "yourbrand_personal", "display_name": "Personal", "followers": 3200},
        {"id": "tt1", "platform": "tiktok", "username": "yourbrand", "display_name": "Your Brand TikTok", "followers": 45000},
        {"id": "yt1", "platform": "youtube", "username": "YourBrandChannel", "display_name": "Your Brand", "followers": 8500},
        {"id": "li1", "platform": "linkedin", "username": "your-brand", "display_name": "Your Brand LLC", "followers": 2100},
        {"id": "fb1", "platform": "facebook", "username": "yourbrand", "display_name": "Your Brand Page", "followers": 15000},
    ]


@router.post("/compare", response_model=ComparisonResult)
async def compare_accounts(
    account_ids: List[str],
    mode: CompareMode = CompareMode.CROSS_PLATFORM,
    period: str = "30d",
):
    """
    Compare multiple accounts
    
    Args:
        account_ids: List of account IDs to compare (2-4)
        mode: Comparison mode (platforms, accounts, time)
        period: Time period (7d, 30d, 90d, 1y)
    """
    if len(account_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 accounts required for comparison")
    if len(account_ids) > 4:
        raise HTTPException(status_code=400, detail="Maximum 4 accounts for comparison")
    
    period_days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(period, 30)
    
    # Fetch metrics for each account
    # In production, fetch from database/platform APIs
    accounts_data = await list_connected_accounts()
    account_map = {a["id"]: a for a in accounts_data}
    
    metrics = []
    for account_id in account_ids:
        if account_id in account_map:
            account_info = account_map[account_id]
            metrics.append(get_mock_account_metrics(
                account_id,
                account_info["platform"],
                period_days
            ))
    
    # Generate insights and recommendations
    insights = generate_insights(metrics)
    recommendations = generate_recommendations(metrics)
    audience_overlap = calculate_audience_overlap(metrics)
    
    return ComparisonResult(
        mode=mode,
        period=f"Last {period_days} days",
        accounts=metrics,
        insights=insights,
        recommendations=recommendations,
        audience_overlap=audience_overlap,
    )


@router.get("/compare-time/{account_id}", response_model=TimePeriodComparison)
async def compare_time_periods(
    account_id: str,
    periods: List[str] = Query(default=["30d", "60d", "90d"]),
):
    """
    Compare same account across different time periods
    
    Args:
        account_id: Account to analyze
        periods: List of time periods to compare
    """
    accounts_data = await list_connected_accounts()
    account_info = next((a for a in accounts_data if a["id"] == account_id), None)
    
    if not account_info:
        raise HTTPException(status_code=404, detail="Account not found")
    
    period_metrics = []
    for period in periods:
        period_days = {"7d": 7, "30d": 30, "60d": 60, "90d": 90, "1y": 365}.get(period, 30)
        metrics = get_mock_account_metrics(account_id, account_info["platform"], period_days)
        metrics.period = period
        period_metrics.append(metrics)
    
    # Calculate trends
    trends = {}
    if len(period_metrics) >= 2:
        latest = period_metrics[0]
        previous = period_metrics[1]
        
        trends["engagement_rate"] = "up" if latest.engagement_rate > previous.engagement_rate else "down"
        trends["followers"] = "up" if latest.followers > previous.followers else "down"
        trends["avg_reach_per_post"] = "up" if latest.avg_reach_per_post > previous.avg_reach_per_post else "down"
    
    # Growth forecast (simple projection)
    growth_forecast = {}
    if period_metrics:
        latest = period_metrics[0]
        growth_forecast["followers_30d"] = latest.followers * (1 + latest.follower_growth_percent / 100)
        growth_forecast["followers_90d"] = latest.followers * (1 + latest.follower_growth_percent / 100) ** 3
    
    return TimePeriodComparison(
        account_id=account_id,
        periods=period_metrics,
        trends=trends,
        growth_forecast=growth_forecast,
    )


@router.get("/audience-comparison")
async def compare_audiences(
    account_ids: List[str] = Query(...),
):
    """
    Deep audience comparison between accounts
    
    Returns detailed demographic overlaps and differences
    """
    if len(account_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 accounts required")
    
    accounts_data = await list_connected_accounts()
    account_map = {a["id"]: a for a in accounts_data}
    
    metrics = []
    for account_id in account_ids:
        if account_id in account_map:
            account_info = account_map[account_id]
            metrics.append(get_mock_account_metrics(account_id, account_info["platform"]))
    
    overlap = calculate_audience_overlap(metrics)
    
    # Add detailed comparison
    comparison = {
        "overlap": overlap,
        "by_account": {},
        "insights": [],
    }
    
    for m in metrics:
        comparison["by_account"][m.account_id] = {
            "platform": m.platform,
            "username": m.username,
            "demographics": m.audience_demographics.dict(),
        }
    
    # Generate audience insights
    if overlap.get("overall_similarity", 0) > 70:
        comparison["insights"].append({
            "type": "overlap",
            "message": "High audience overlap detected. Content can be effectively repurposed across these platforms.",
        })
    else:
        comparison["insights"].append({
            "type": "diversity",
            "message": "Diverse audiences across platforms. Consider tailoring content for each audience.",
        })
    
    return comparison


@router.get("/platforms-summary")
async def get_platforms_summary():
    """
    Get quick summary comparison of all connected platforms
    """
    accounts_data = await list_connected_accounts()
    
    summaries = []
    for account in accounts_data:
        metrics = get_mock_account_metrics(account["id"], account["platform"])
        summaries.append({
            "id": account["id"],
            "platform": account["platform"],
            "username": account["username"],
            "followers": metrics.followers,
            "engagement_rate": round(metrics.engagement_rate, 1),
            "growth_percent": round(metrics.follower_growth_percent, 1),
            "best_time": metrics.best_posting_time,
            "top_format": metrics.top_post_type,
        })
    
    # Sort by engagement rate
    summaries.sort(key=lambda x: x["engagement_rate"], reverse=True)
    
    return {
        "accounts": summaries,
        "best_engagement": summaries[0] if summaries else None,
        "fastest_growing": max(summaries, key=lambda x: x["growth_percent"]) if summaries else None,
        "total_followers": sum(s["followers"] for s in summaries),
    }
