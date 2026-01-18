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
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.blotato_account_id = "4151"  # Twitter account ID from Blotato
        
        # Tweets per day configuration
        self.tweets_per_day = 60
        self.products_count = 3  # Everreach, BlankLogo, Apple App Kit
        self.tweets_per_product = self.tweets_per_day // self.products_count  # 20 each
        
        logger.info(f"TwitterCampaignService initialized - {self.tweets_per_day} tweets/day")
    
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
        """Generate a single tweet using AI."""
        
        user_style = user_style or self.get_user_style()
        
        stage_desc = AWARENESS_STAGE_DESCRIPTIONS.get(awareness_stage, '')
        type_desc = CONTENT_TYPE_DESCRIPTIONS.get(content_type, '')
        
        style_prompt = user_style.get('generated_style_prompt') or f"""
Writing Style:
- Tone: {', '.join(user_style.get('tone_keywords', ['casual', 'direct']))}
- {user_style.get('style_description', 'Casual and direct')}
- Avoid words: {', '.join(user_style.get('avoid_words', []))}
- Use lowercase when it feels natural
- No hashtags unless absolutely necessary
- No emojis unless they add real value
- Sound like a real person, not a brand
"""
        
        prompt = f"""Generate a single Twitter post (max 280 chars) for:

PRODUCT: {product.name}
- Description: {product.description}
- Website: {product.website_url}
- Tagline: {product.tagline}
- Key Features: {', '.join(product.key_features[:3])}
- Target Audience: {product.target_audience}

AWARENESS STAGE: {awareness_stage.value}
{stage_desc}

CONTENT TYPE: {content_type.value}
{type_desc}

{style_prompt}

IMPORTANT RULES:
1. MUST be under 280 characters
2. Sound authentic, like a real person tweeting
3. Don't be salesy or corporate
4. Can include the product URL ({product.website_url}) if it's a CTA type, but not required
5. Make it engaging and likely to get replies/retweets
6. Match the awareness stage - don't pitch to unaware audiences
7. Be specific, not generic

Generate ONLY the tweet text, nothing else."""

        response = self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a social media expert who writes authentic, engaging tweets that don't sound like marketing. You understand the customer awareness journey and tailor messaging appropriately."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.9  # Higher creativity
        )
        
        tweet = response.choices[0].message.content.strip()
        
        # Remove quotes if AI wrapped it
        if tweet.startswith('"') and tweet.endswith('"'):
            tweet = tweet[1:-1]
        
        # Ensure under 280 chars
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        
        return tweet
    
    def generate_batch_tweets(
        self,
        product: Product,
        count: int = 20,
        user_style: Optional[Dict] = None
    ) -> List[Dict]:
        """Generate a batch of tweets cycling through stages and types."""
        
        user_style = user_style or self.get_user_style()
        tweets = []
        
        stages = list(AwarenessStage)
        types = list(ContentType)
        
        for i in range(count):
            stage = stages[i % len(stages)]
            content_type = types[i % len(types)]
            
            try:
                tweet_text = self.generate_tweet(product, stage, content_type, user_style)
                tweets.append({
                    'product_id': product.id,
                    'product_slug': product.slug,
                    'awareness_stage': stage.value,
                    'content_type': content_type.value,
                    'tweet_text': tweet_text
                })
                logger.info(f"Generated tweet {i+1}/{count} for {product.slug}: {stage.value}/{content_type.value}")
            except Exception as e:
                logger.error(f"Failed to generate tweet: {e}")
        
        return tweets
    
    # =========================================================================
    # SCHEDULING
    # =========================================================================
    
    def schedule_tweets(
        self,
        tweets: List[Dict],
        start_time: Optional[datetime] = None,
        interval_minutes: int = 24  # ~60 tweets spread over 24 hours = ~24 min apart
    ) -> List[str]:
        """Schedule tweets for posting."""
        
        start_time = start_time or datetime.now(timezone.utc)
        scheduled_ids = []
        
        with self.engine.connect() as conn:
            for i, tweet in enumerate(tweets):
                scheduled_time = start_time + timedelta(minutes=interval_minutes * i)
                
                result = conn.execute(text("""
                    INSERT INTO scheduled_tweets
                    (product_id, awareness_stage, content_type, tweet_text, 
                     scheduled_time, blotato_account_id, status)
                    VALUES
                    (:product_id, :awareness_stage, :content_type, :tweet_text,
                     :scheduled_time, :blotato_account_id, 'scheduled')
                    RETURNING id
                """), {
                    "product_id": tweet['product_id'],
                    "awareness_stage": tweet['awareness_stage'],
                    "content_type": tweet['content_type'],
                    "tweet_text": tweet['tweet_text'],
                    "scheduled_time": scheduled_time,
                    "blotato_account_id": self.blotato_account_id
                })
                
                row = result.fetchone()
                if row:
                    scheduled_ids.append(str(row[0]))
            
            conn.commit()
        
        logger.info(f"Scheduled {len(scheduled_ids)} tweets starting at {start_time}")
        return scheduled_ids
    
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
        """Post a single tweet via Blotato, with Safari fallback."""
        from modules.publishing.blotato_client import BlotatoClient
        
        # Try Blotato first
        try:
            client = BlotatoClient()
            
            result = client.create_post(
                account_id=tweet['blotato_account_id'],
                platform='twitter',
                text=tweet['tweet_text'],
                media_urls=[]
            )
            
            if result:
                self._record_posted_tweet(tweet, result)
                self._mark_tweet_posted(tweet['id'], result)
                return {'success': True, 'result': result, 'method': 'blotato'}
                
        except Exception as e:
            logger.warning(f"Blotato failed, trying Safari fallback: {e}")
        
        # Fallback to Safari automation
        try:
            from automation.safari_twitter_poster import SafariTwitterPoster
            
            poster = SafariTwitterPoster()
            result = poster.post_tweet(tweet['tweet_text'])
            
            if result.get('success'):
                self._record_posted_tweet(tweet, {
                    'post_submission_id': f"safari_{int(datetime.now().timestamp())}",
                    'platform_url': result.get('url')
                })
                self._mark_tweet_posted(tweet['id'], result)
                return {'success': True, 'result': result, 'method': 'safari'}
            else:
                self._mark_tweet_failed(tweet['id'], result.get('error', 'Safari posting failed'))
                return {'success': False, 'error': result.get('error'), 'method': 'safari'}
                
        except Exception as e:
            logger.error(f"Failed to post tweet {tweet['id']}: {e}")
            self._mark_tweet_failed(tweet['id'], str(e))
            return {'success': False, 'error': str(e)}
    
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
        """Generate and schedule 60 tweets for the day."""
        logger.info("=" * 60)
        logger.info("Starting Daily Twitter Campaign")
        logger.info("=" * 60)
        
        # Reset daily counts
        self.reset_daily_counts()
        
        products = self.get_products()
        user_style = self.get_user_style()
        
        all_tweets = []
        
        for product in products:
            logger.info(f"\n📦 Generating tweets for {product.name}...")
            tweets = self.generate_batch_tweets(
                product=product,
                count=self.tweets_per_product,
                user_style=user_style
            )
            all_tweets.extend(tweets)
        
        # Shuffle to mix products
        random.shuffle(all_tweets)
        
        # Schedule tweets
        scheduled_ids = self.schedule_tweets(
            tweets=all_tweets,
            start_time=datetime.now(timezone.utc),
            interval_minutes=24  # ~1 tweet every 24 minutes
        )
        
        logger.info(f"\n✅ Scheduled {len(scheduled_ids)} tweets for today")
        
        return {
            'total_scheduled': len(scheduled_ids),
            'products': [p.name for p in products],
            'scheduled_ids': scheduled_ids[:10]  # First 10 for reference
        }
    
    async def process_due_tweets(self) -> Dict:
        """Process all tweets that are due for posting."""
        due_tweets = self.get_due_tweets()
        
        if not due_tweets:
            return {'processed': 0, 'success': 0, 'failed': 0}
        
        logger.info(f"Processing {len(due_tweets)} due tweets...")
        
        success_count = 0
        failed_count = 0
        
        for tweet in due_tweets:
            result = await self.post_tweet(tweet)
            if result['success']:
                success_count += 1
                logger.info(f"✅ Posted tweet: {tweet['tweet_text'][:50]}...")
            else:
                failed_count += 1
                logger.error(f"❌ Failed: {result.get('error')}")
        
        return {
            'processed': len(due_tweets),
            'success': success_count,
            'failed': failed_count
        }


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
