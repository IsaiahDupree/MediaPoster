"""
Twitter Campaign Automation Service
Generates and schedules 60 tweets/day across multiple products
using the 5 stages of customer awareness.
"""
import os
import json
import random
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Literal
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from uuid import UUID

from openai import OpenAI
from sqlalchemy import create_engine, text
from loguru import logger

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


class AwarenessStage(str, Enum):
    UNAWARE = "unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    PRODUCT_AWARE = "product_aware"
    MOST_AWARE = "most_aware"


class ContentType(str, Enum):
    HOOK = "hook"
    AUTHORITY = "authority"
    STORY = "story"
    EMOTIONAL = "emotional"
    CTA = "cta"


@dataclass
class Product:
    id: str
    name: str
    slug: str
    description: str
    website_url: str
    tagline: str
    key_features: List[str]
    target_audience: str
    voice_style: str


@dataclass
class TweetTemplate:
    id: str
    product_id: str
    awareness_stage: AwarenessStage
    content_type: ContentType
    template_text: str
    variables: Dict
    performance_score: float
    times_used: int


AWARENESS_STAGE_DESCRIPTIONS = {
    AwarenessStage.UNAWARE: """
        The audience doesn't know they have a problem.
        Focus on: Relatable situations, "have you ever..." questions, pattern interrupts
        Goal: Make them realize something they do is inefficient or could be better
    """,
    AwarenessStage.PROBLEM_AWARE: """
        The audience knows they have a problem but not the solution.
        Focus on: Agitate the pain, share struggles, validate their frustration
        Goal: Make them actively seek a solution
    """,
    AwarenessStage.SOLUTION_AWARE: """
        The audience knows solutions exist, comparing options.
        Focus on: Why YOUR solution is different/better, comparisons, social proof
        Goal: Position as the best choice
    """,
    AwarenessStage.PRODUCT_AWARE: """
        The audience knows your product, needs convincing.
        Focus on: Features, benefits, testimonials, case studies, overcome objections
        Goal: Remove barriers to action
    """,
    AwarenessStage.MOST_AWARE: """
        The audience is ready to buy, just needs a push.
        Focus on: Urgency, special offers, direct CTAs, reminders
        Goal: Get them to act NOW
    """
}

CONTENT_TYPE_DESCRIPTIONS = {
    ContentType.HOOK: """
        Pattern interrupt, curiosity gap, bold statement, contrarian take.
        Purpose: Stop the scroll, make them want to read more.
        Style: Short, punchy, unexpected, sometimes controversial.
    """,
    ContentType.AUTHORITY: """
        Share expertise, insights, lessons learned, behind-the-scenes.
        Purpose: Build trust and credibility.
        Style: Educational, confident, backed by experience.
    """,
    ContentType.STORY: """
        Personal anecdotes, customer stories, journey narratives.
        Purpose: Create connection through shared experience.
        Style: Vulnerable, relatable, narrative arc.
    """,
    ContentType.EMOTIONAL: """
        Tap into feelings, aspirations, fears, desires.
        Purpose: Create an emotional bond with the reader.
        Style: Empathetic, inspiring, sometimes provocative.
    """,
    ContentType.CTA: """
        Direct call to action, clear next step, urgency.
        Purpose: Drive specific action (sign up, try, buy).
        Style: Clear, direct, benefit-focused, urgency when appropriate.
    """
}


class TwitterCampaignService:
    """
    Manages automated Twitter campaigns with:
    - AI-generated tweets based on awareness stages
    - User voice/style matching
    - Scheduled posting via Blotato
    - Analytics tracking and optimization
    """
    
    def __init__(self, interval_minutes: int = 120):
        self.engine = create_engine(DATABASE_URL)
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.blotato_account_id = "4151"  # Twitter account ID from Blotato

        # REQ-TWITTER-001: Configurable posting interval (default 2 hours)
        self.interval_minutes = interval_minutes

        # Tweets per day configuration
        self.tweets_per_day = 60
        self.products_count = 3  # Everreach, BlankLogo, Apple App Kit
        self.tweets_per_product = self.tweets_per_day // self.products_count  # 20 each

        # Setup event subscriptions for orchestrator integration
        self._setup_event_subscriptions()

        logger.info(f"TwitterCampaignService initialized - {self.tweets_per_day} tweets/day, interval={self.interval_minutes}min")

    def _setup_event_subscriptions(self) -> None:
        """Subscribe to orchestrator events for campaign scheduling."""
        try:
            from services.event_bus import EventBus
            event_bus = EventBus.get_instance()
            event_bus.subscribe("twitter.campaign.schedule_requested", self._handle_schedule_request)
            logger.info("📫 TwitterCampaignService subscribed to twitter.campaign.schedule_requested")
        except Exception as e:
            logger.warning(f"⚠️ Could not setup event subscriptions: {e}")

    async def _handle_schedule_request(self, event) -> None:
        """
        Handle twitter.campaign.schedule_requested from orchestrator.

        Expected payload:
        {
            "pipeline_id": str,
            "theme": str,
            "count": int (default 12),
            "interval_minutes": int (default 120),
            "offer_url": Optional[str]
        }
        """
        try:
            from services.event_bus import EventBus

            payload = event.payload
            pipeline_id = payload.get("pipeline_id")
            theme = payload.get("theme")
            count = payload.get("count", 12)
            interval_minutes = payload.get("interval_minutes", self.interval_minutes)
            offer_url = payload.get("offer_url")

            logger.info(f"🐦 [TwitterCampaign] Scheduling {count} tweets for pipeline {pipeline_id}")

            # Schedule tweets
            if offer_url:
                # Use offer-focused tweet generation
                scheduled_ids = self.schedule_offer_tweets(
                    offer_url=offer_url,
                    offer_description=theme,
                    count=count,
                    interval_minutes=interval_minutes,
                    campaign_name=pipeline_id
                )
            else:
                # Use theme-based campaign
                campaign_id = self.schedule_campaign(
                    theme=theme,
                    count=count,
                    interval_minutes=interval_minutes
                )
                scheduled_ids = [campaign_id]

            logger.info(f"✅ [TwitterCampaign] Scheduled {len(scheduled_ids)} tweets")

            # Emit completion event
            event_bus = EventBus.get_instance()
            await event_bus.publish(
                "twitter.campaign.scheduled",
                {
                    "pipeline_id": pipeline_id,
                    "tweets_scheduled": count,
                    "scheduled_ids": scheduled_ids
                },
                correlation_id=getattr(event, 'correlation_id', None),
                source="TwitterCampaignService"
            )

        except Exception as e:
            logger.error(f"❌ [TwitterCampaign] Error handling schedule request: {e}")
            # Emit failure event
            try:
                from services.event_bus import EventBus
                event_bus = EventBus.get_instance()
                await event_bus.publish(
                    "twitter.campaign.failed",
                    {
                        "pipeline_id": payload.get("pipeline_id"),
                        "error": str(e)
                    },
                    source="TwitterCampaignService"
                )
            except:
                pass

    # =========================================================================
    # PRODUCT MANAGEMENT
    # =========================================================================
    
    def get_products(self) -> List[Product]:
        """Get all campaign products from database."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, name, slug, description, website_url, tagline,
                       key_features, target_audience, voice_style
                FROM campaign_products
                ORDER BY created_at
            """))
            
            products = []
            for row in result.fetchall():
                features = row[6] if isinstance(row[6], list) else json.loads(row[6] or '[]')
                products.append(Product(
                    id=str(row[0]),
                    name=row[1],
                    slug=row[2],
                    description=row[3] or '',
                    website_url=row[4] or '',
                    tagline=row[5] or '',
                    key_features=features,
                    target_audience=row[7] or '',
                    voice_style=row[8] or ''
                ))
            
            return products
    
    def get_product_by_slug(self, slug: str) -> Optional[Product]:
        """Get a specific product by slug."""
        products = self.get_products()
        return next((p for p in products if p.slug == slug), None)
    
    # =========================================================================
    # USER STYLE MANAGEMENT
    # =========================================================================
    
    def get_user_style(self, user_id: str = 'default') -> Dict:
        """Get user's writing style from database."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT sample_tweets, tone_keywords, avoid_words, 
                       style_description, generated_style_prompt
                FROM user_writing_styles
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            
            row = result.fetchone()
            if row:
                return {
                    'sample_tweets': row[0] if isinstance(row[0], list) else json.loads(row[0] or '[]'),
                    'tone_keywords': row[1] if isinstance(row[1], list) else json.loads(row[1] or '[]'),
                    'avoid_words': row[2] if isinstance(row[2], list) else json.loads(row[2] or '[]'),
                    'style_description': row[3] or '',
                    'generated_style_prompt': row[4] or ''
                }
            
            return {
                'sample_tweets': [],
                'tone_keywords': ['direct', 'casual', 'confident', 'authentic'],
                'avoid_words': ['utilize', 'leverage', 'synergy'],
                'style_description': 'Casual, direct, lowercase preferred, no corporate speak',
                'generated_style_prompt': ''
            }
    
    def update_user_style(self, user_id: str, style_data: Dict):
        """Update user's writing style."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO user_writing_styles 
                (user_id, sample_tweets, tone_keywords, avoid_words, style_description, generated_style_prompt)
                VALUES (:user_id, :sample_tweets, :tone_keywords, :avoid_words, :style_description, :generated_style_prompt)
                ON CONFLICT (user_id) DO UPDATE SET
                    sample_tweets = EXCLUDED.sample_tweets,
                    tone_keywords = EXCLUDED.tone_keywords,
                    avoid_words = EXCLUDED.avoid_words,
                    style_description = EXCLUDED.style_description,
                    generated_style_prompt = EXCLUDED.generated_style_prompt,
                    last_updated = NOW()
            """), {
                "user_id": user_id,
                "sample_tweets": json.dumps(style_data.get('sample_tweets', [])),
                "tone_keywords": json.dumps(style_data.get('tone_keywords', [])),
                "avoid_words": json.dumps(style_data.get('avoid_words', [])),
                "style_description": style_data.get('style_description', ''),
                "generated_style_prompt": style_data.get('generated_style_prompt', '')
            })
            conn.commit()
    
    # =========================================================================
    # CAMPAIGN CYCLE MANAGEMENT
    # =========================================================================
    
    def get_campaign_cycle(self, product_id: str) -> Dict:
        """Get current campaign cycle state for a product."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT current_awareness_stage, current_content_type,
                       stage_tweet_count, type_tweet_count, total_tweets_today,
                       last_tweet_at
                FROM campaign_cycles
                WHERE product_id = :product_id
            """), {"product_id": product_id})
            
            row = result.fetchone()
            if row:
                return {
                    'awareness_stage': row[0],
                    'content_type': row[1],
                    'stage_tweet_count': row[2] or 0,
                    'type_tweet_count': row[3] or 0,
                    'total_tweets_today': row[4] or 0,
                    'last_tweet_at': row[5]
                }
            
            return {
                'awareness_stage': 'unaware',
                'content_type': 'hook',
                'stage_tweet_count': 0,
                'type_tweet_count': 0,
                'total_tweets_today': 0,
                'last_tweet_at': None
            }
    
    def advance_cycle(self, product_id: str):
        """Advance the campaign cycle (rotate stage/type as needed)."""
        cycle = self.get_campaign_cycle(product_id)
        
        # Rotate content type every tweet
        new_content_type = self._rotate_content_type(cycle['content_type'])
        
        # Rotate awareness stage every 5 tweets (one full content type cycle)
        new_stage = cycle['awareness_stage']
        stage_tweet_count = cycle['stage_tweet_count'] + 1
        
        if stage_tweet_count >= 5:
            new_stage = self._rotate_awareness_stage(cycle['awareness_stage'])
            stage_tweet_count = 0
        
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE campaign_cycles
                SET current_awareness_stage = :stage,
                    current_content_type = :content_type,
                    stage_tweet_count = :stage_count,
                    type_tweet_count = type_tweet_count + 1,
                    total_tweets_today = total_tweets_today + 1,
                    last_tweet_at = NOW(),
                    updated_at = NOW()
                WHERE product_id = :product_id
            """), {
                "product_id": product_id,
                "stage": new_stage,
                "content_type": new_content_type,
                "stage_count": stage_tweet_count
            })
            conn.commit()
    
    def reset_daily_counts(self):
        """Reset daily tweet counts (call at midnight)."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE campaign_cycles
                SET total_tweets_today = 0,
                    updated_at = NOW()
            """))
            conn.commit()
    
    def _rotate_awareness_stage(self, current: str) -> str:
        stages = ['unaware', 'problem_aware', 'solution_aware', 'product_aware', 'most_aware']
        idx = stages.index(current) if current in stages else 0
        return stages[(idx + 1) % len(stages)]
    
    def _rotate_content_type(self, current: str) -> str:
        types = ['hook', 'authority', 'story', 'emotional', 'cta']
        idx = types.index(current) if current in types else 0
        return types[(idx + 1) % len(types)]
    
    # =========================================================================
    # AI TWEET GENERATION
    # =========================================================================
    
    def generate_tweet(
        self,
        product: Product,
        awareness_stage: AwarenessStage,
        content_type: ContentType,
        user_style: Optional[Dict] = None
    ) -> str:
        raise RuntimeError("script_hub_required: legacy Twitter copy generation is disabled; use ScriptHub.")
    
    def generate_batch_tweets(
        self,
        product: Product,
        count: int = 20,
        user_style: Optional[Dict] = None
    ) -> List[Dict]:
        raise RuntimeError("script_hub_required: legacy Twitter copy generation is disabled; use ScriptHub.")
    
    # =========================================================================
    # SCHEDULING
    # =========================================================================
    
    def schedule_tweets(
        self,
        tweets: List[Dict],
        start_time: Optional[datetime] = None,
        interval_minutes: int = 24  # ~60 tweets spread over 24 hours = ~24 min apart
    ) -> List[str]:
        raise RuntimeError("airtime_required: legacy Twitter scheduling is disabled; use Airtime.")
    
    def get_due_tweets(self) -> List[Dict]:
        """Get tweets that are due for posting."""
        now = datetime.now(timezone.utc)
        
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE scheduled_tweets
                SET status = 'publishing', updated_at = NOW()
                WHERE id IN (
                    SELECT id FROM scheduled_tweets
                    WHERE status = 'scheduled'
                      AND scheduled_time <= :now
                    ORDER BY scheduled_time ASC
                    LIMIT 10
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, product_id, awareness_stage, content_type, 
                          tweet_text, blotato_account_id
            """), {"now": now})
            
            tweets = []
            for row in result.fetchall():
                tweets.append({
                    'id': str(row[0]),
                    'product_id': str(row[1]),
                    'awareness_stage': row[2],
                    'content_type': row[3],
                    'tweet_text': row[4],
                    'blotato_account_id': row[5]
                })
            
            conn.commit()
            return tweets
    
    # =========================================================================
    # POSTING
    # =========================================================================
    
    async def post_tweet(self, tweet: Dict) -> Dict:
        return {"success": False, "error": "airtime_required"}
    
    def _record_posted_tweet(self, tweet: Dict, result: Dict):
        """Record a posted tweet for analytics tracking."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO posted_tweets
                (scheduled_tweet_id, product_id, awareness_stage, content_type,
                 tweet_text, blotato_account_id, blotato_submission_id, 
                 platform_post_id, platform_url, posted_at)
                VALUES
                (:scheduled_tweet_id, :product_id, :awareness_stage, :content_type,
                 :tweet_text, :blotato_account_id, :submission_id,
                 :platform_post_id, :platform_url, NOW())
            """), {
                "scheduled_tweet_id": tweet['id'],
                "product_id": tweet['product_id'],
                "awareness_stage": tweet['awareness_stage'],
                "content_type": tweet['content_type'],
                "tweet_text": tweet['tweet_text'],
                "blotato_account_id": tweet['blotato_account_id'],
                "submission_id": result.get('post_submission_id'),
                "platform_post_id": result.get('post_submission_id'),
                "platform_url": result.get('platform_url')
            })
            conn.commit()
    
    def _mark_tweet_posted(self, tweet_id: str, result: Dict):
        """Mark a scheduled tweet as posted."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE scheduled_tweets
                SET status = 'posted', updated_at = NOW()
                WHERE id = :id
            """), {"id": tweet_id})
            conn.commit()
    
    def _mark_tweet_failed(self, tweet_id: str, error: str):
        """Mark a scheduled tweet as failed."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE scheduled_tweets
                SET status = 'failed', 
                    error_message = :error,
                    retry_count = retry_count + 1,
                    updated_at = NOW()
                WHERE id = :id
            """), {"id": tweet_id, "error": error})
            conn.commit()
    
    # =========================================================================
    # ANALYTICS
    # =========================================================================
    
    def get_posted_tweets(
        self,
        product_slug: Optional[str] = None,
        days: int = 7,
        limit: int = 100
    ) -> List[Dict]:
        """Get posted tweets with analytics."""
        with self.engine.connect() as conn:
            query = """
                SELECT pt.id, pt.tweet_text, pt.awareness_stage, pt.content_type,
                       pt.platform_url, pt.posted_at, pt.impressions, pt.engagements,
                       pt.likes, pt.retweets, pt.replies, pt.engagement_rate,
                       pt.performance_score, cp.slug as product_slug
                FROM posted_tweets pt
                JOIN campaign_products cp ON pt.product_id = cp.id
                WHERE pt.posted_at > NOW() - INTERVAL ':days days'
            """
            
            params = {"days": days, "limit": limit}
            
            if product_slug:
                query += " AND cp.slug = :slug"
                params["slug"] = product_slug
            
            query += " ORDER BY pt.posted_at DESC LIMIT :limit"
            
            result = conn.execute(text(query), params)
            
            tweets = []
            for row in result.fetchall():
                tweets.append({
                    'id': str(row[0]),
                    'tweet_text': row[1],
                    'awareness_stage': row[2],
                    'content_type': row[3],
                    'platform_url': row[4],
                    'posted_at': str(row[5]) if row[5] else None,
                    'impressions': row[6] or 0,
                    'engagements': row[7] or 0,
                    'likes': row[8] or 0,
                    'retweets': row[9] or 0,
                    'replies': row[10] or 0,
                    'engagement_rate': row[11] or 0,
                    'performance_score': row[12] or 0,
                    'product_slug': row[13]
                })
            
            return tweets
    
    def get_performance_summary(self, product_slug: Optional[str] = None) -> Dict:
        """Get performance summary by awareness stage and content type."""
        with self.engine.connect() as conn:
            # By awareness stage
            stage_query = """
                SELECT awareness_stage, 
                       COUNT(*) as count,
                       AVG(engagement_rate) as avg_engagement,
                       SUM(impressions) as total_impressions
                FROM posted_tweets pt
                JOIN campaign_products cp ON pt.product_id = cp.id
                WHERE pt.posted_at > NOW() - INTERVAL '30 days'
            """
            
            if product_slug:
                stage_query += " AND cp.slug = :slug"
            
            stage_query += " GROUP BY awareness_stage ORDER BY avg_engagement DESC"
            
            params = {"slug": product_slug} if product_slug else {}
            stage_result = conn.execute(text(stage_query), params)
            
            by_stage = {}
            for row in stage_result.fetchall():
                by_stage[row[0]] = {
                    'count': row[1],
                    'avg_engagement': float(row[2] or 0),
                    'total_impressions': row[3] or 0
                }
            
            # By content type
            type_query = """
                SELECT content_type,
                       COUNT(*) as count,
                       AVG(engagement_rate) as avg_engagement,
                       SUM(impressions) as total_impressions
                FROM posted_tweets pt
                JOIN campaign_products cp ON pt.product_id = cp.id
                WHERE pt.posted_at > NOW() - INTERVAL '30 days'
            """
            
            if product_slug:
                type_query += " AND cp.slug = :slug"
            
            type_query += " GROUP BY content_type ORDER BY avg_engagement DESC"
            
            type_result = conn.execute(text(type_query), params)
            
            by_type = {}
            for row in type_result.fetchall():
                by_type[row[0]] = {
                    'count': row[1],
                    'avg_engagement': float(row[2] or 0),
                    'total_impressions': row[3] or 0
                }
            
            return {
                'by_awareness_stage': by_stage,
                'by_content_type': by_type
            }
    
    def record_analytics_checkback(self, tweet_id: str, period: str, metrics: Dict):
        """Record analytics checkback for a tweet."""
        with self.engine.connect() as conn:
            # Insert checkback record
            conn.execute(text("""
                INSERT INTO analytics_checkbacks
                (posted_tweet_id, check_period, impressions, engagements,
                 likes, retweets, replies, engagement_rate)
                VALUES
                (:tweet_id, :period, :impressions, :engagements,
                 :likes, :retweets, :replies, :engagement_rate)
            """), {
                "tweet_id": tweet_id,
                "period": period,
                "impressions": metrics.get('impressions', 0),
                "engagements": metrics.get('engagements', 0),
                "likes": metrics.get('likes', 0),
                "retweets": metrics.get('retweets', 0),
                "replies": metrics.get('replies', 0),
                "engagement_rate": metrics.get('engagement_rate', 0)
            })
            
            # Update posted_tweets with latest metrics
            conn.execute(text("""
                UPDATE posted_tweets
                SET impressions = :impressions,
                    engagements = :engagements,
                    likes = :likes,
                    retweets = :retweets,
                    replies = :replies,
                    engagement_rate = :engagement_rate,
                    last_analytics_check = NOW(),
                    analytics_check_count = analytics_check_count + 1,
                    updated_at = NOW()
                WHERE id = :tweet_id
            """), {
                "tweet_id": tweet_id,
                **metrics
            })
            
            conn.commit()
    
    # =========================================================================
    # MAIN CAMPAIGN RUNNER
    # =========================================================================
    
    async def run_daily_campaign(self):
        raise RuntimeError("script_hub_required: legacy Twitter copy generation is disabled; use ScriptHub.")
    
    # =========================================================================
    # REQ-TWITTER-002: OFFER-FOCUSED TWEET GENERATION WITH UTM
    # =========================================================================
    
    def generate_utm_link(
        self,
        base_url: str,
        campaign: str = "twitter",
        source: str = "twitter",
        medium: str = "social",
        content: Optional[str] = None
    ) -> str:
        """
        Generate a UTM-tracked link for offer tracking.
        
        Args:
            base_url: The offer URL to track
            campaign: Campaign name (e.g., "jan2026_promo")
            source: Traffic source (default "twitter")
            medium: Marketing medium (default "social")
            content: Optional content identifier for A/B testing
            
        Returns:
            URL with UTM parameters appended
        """
        from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
        
        # Parse existing URL
        parsed = urlparse(base_url)
        existing_params = parse_qs(parsed.query)
        
        # Add UTM parameters
        utm_params = {
            "utm_source": source,
            "utm_medium": medium,
            "utm_campaign": campaign
        }
        if content:
            utm_params["utm_content"] = content
        
        # Merge with existing params
        existing_params.update(utm_params)
        
        # Flatten the params dict
        flat_params = {k: v[0] if isinstance(v, list) else v for k, v in existing_params.items()}
        
        # Rebuild URL
        new_query = urlencode(flat_params)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
    
    def generate_offer_tweet(
        self,
        offer_url: str,
        offer_description: str,
        cta_text: str = "Check it out",
        campaign_name: Optional[str] = None,
        content_id: Optional[str] = None
    ) -> Dict:
        raise RuntimeError("script_hub_required: legacy Twitter copy generation is disabled; use ScriptHub.")
    
    def schedule_offer_tweets(
        self,
        offer_url: str,
        offer_description: str,
        count: int = 12,
        interval_minutes: int = 120,
        start_time: Optional[datetime] = None,
        campaign_name: Optional[str] = None
    ) -> List[str]:
        raise RuntimeError("airtime_required: legacy Twitter scheduling is disabled; use Airtime.")
    
    async def process_due_tweets(self) -> Dict:
        return {"processed": 0, "success": 0, "failed": 0, "error": "airtime_required"}

    # ARCH-004: Schedule campaign with tweet generation
    def schedule_campaign(
        self,
        theme: str,
        count: int = 12,
        interval_minutes: Optional[int] = None,
        start_time: Optional[datetime] = None
    ) -> str:
        raise RuntimeError("script_hub_required: legacy Twitter copy generation is disabled; use ScriptHub.")


# Singleton instance
_campaign_service = None

def get_campaign_service() -> TwitterCampaignService:
    global _campaign_service
    if _campaign_service is None:
        _campaign_service = TwitterCampaignService()
    return _campaign_service


# CLI interface
if __name__ == "__main__":
    import sys
    
    service = get_campaign_service()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "generate":
            # Generate and schedule daily tweets
            import asyncio
            result = asyncio.run(service.run_daily_campaign())
            print(json.dumps(result, indent=2))
            
        elif command == "process":
            # Process due tweets
            import asyncio
            result = asyncio.run(service.process_due_tweets())
            print(json.dumps(result, indent=2))
            
        elif command == "products":
            # List products
            products = service.get_products()
            for p in products:
                print(f"\n{p.name} ({p.slug})")
                print(f"  URL: {p.website_url}")
                print(f"  Tagline: {p.tagline}")
                
        elif command == "stats":
            # Show performance stats
            summary = service.get_performance_summary()
            print(json.dumps(summary, indent=2))
            
        else:
            print(f"Unknown command: {command}")
            print("Commands: generate, process, products, stats")
    else:
        print("Twitter Campaign Service")
        print("Commands: generate, process, products, stats")
