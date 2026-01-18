"""
Trends Agent Service
=====================
Comprehensive trend detection, lingo extraction, and content-ready output generation.

The agent runs 5 machines in a loop:
1. Ingest: pull posts/reels/tiktoks + metrics
2. Normalize: convert to unified "post event" schema
3. Detect: identify emerging clusters using velocity vs baseline
4. Translate: extract lingo + meaning + examples
5. Deliver: output briefs, hooks, captions, angles

Output format: trend_v1 objects with ready-to-post content.
"""
import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import Counter
import re

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
from openai import OpenAI

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


class ClusterType(str, Enum):
    PHRASE = "phrase"
    FORMAT = "format"
    SOUND = "sound"
    TOPIC = "topic"
    HASHTAG = "hashtag"
    MEME = "meme"


class TrendStage(str, Enum):
    EMERGING = "emerging"      # Just detected, high velocity
    RISING = "rising"          # Sustained growth
    PEAK = "peak"              # Maximum adoption
    DECLINING = "declining"    # Past peak
    EXPIRED = "expired"        # No longer relevant


@dataclass
class TrendSignals:
    """Performance signals for a trend"""
    velocity_1h: float = 0.0      # New mentions per hour
    velocity_24h: float = 0.0     # New mentions per day
    engagement_rate_p50: float = 0.0  # Median engagement rate
    creator_diversity: int = 0     # Unique creators using it
    spread: int = 0               # Number of niches using it
    freshness: float = 1.0        # Decay factor (1.0 = fresh)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LingoData:
    """Extracted lingo from the trend"""
    key_phrases: List[str] = field(default_factory=list)
    usage_notes: str = ""
    variants: List[str] = field(default_factory=list)
    related_phrases: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ContextData:
    """Contextual meaning and usage patterns"""
    meaning: str = ""
    typical_structure: List[str] = field(default_factory=list)
    do_not_use_if: List[str] = field(default_factory=list)
    best_for: List[str] = field(default_factory=list)
    tone: str = "casual"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ContentReady:
    """Ready-to-use content outputs"""
    hooks: List[str] = field(default_factory=list)
    caption_templates: List[str] = field(default_factory=list)
    angles: List[str] = field(default_factory=list)
    cta_options: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TrendV1:
    """
    The unified trend object format.
    This is what we sell - timely interpretation + ready-to-post outputs.
    """
    trend_id: str
    detected_at: datetime
    platforms: List[str]
    cluster_type: ClusterType
    trend_name: str
    stage: TrendStage
    
    # Sub-objects
    lingo: LingoData
    context: ContextData
    signals: TrendSignals
    content_ready: ContentReady
    
    # Metadata
    niche: str = "general"
    brand_safe: bool = True
    confidence: float = 0.0
    source_post_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "trend_id": self.trend_id,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "platforms": self.platforms,
            "cluster_type": self.cluster_type.value if isinstance(self.cluster_type, ClusterType) else self.cluster_type,
            "trend_name": self.trend_name,
            "stage": self.stage.value if isinstance(self.stage, TrendStage) else self.stage,
            "lingo": self.lingo.to_dict() if self.lingo else {},
            "context": self.context.to_dict() if self.context else {},
            "signals": self.signals.to_dict() if self.signals else {},
            "content_ready": self.content_ready.to_dict() if self.content_ready else {},
            "niche": self.niche,
            "brand_safe": self.brand_safe,
            "confidence": self.confidence,
            "source_post_count": self.source_post_count,
        }


class TrendsAgent:
    """
    The main Trends Agent service.
    
    Tools available:
    - fetch_recent_posts(platform, niche, window)
    - embed_text(text) → vector
    - cluster_embeddings(vectors)
    - compute_velocity(cluster, baseline)
    - extract_phrases(posts+comments)
    - summarize_context(cluster)
    - generate_outputs(brand_voice, niche, platform_constraints)
    - policy_check(output)
    """
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or DATABASE_URL
        self.engine = create_engine(self.db_url)
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        
    # =========================================================================
    # TOOL 1: FETCH RECENT POSTS
    # =========================================================================
    
    async def fetch_recent_posts(
        self,
        platform: str = "all",
        niche: str = "general",
        window_hours: int = 24,
        limit: int = 500
    ) -> List[Dict]:
        """
        Fetch recent posts from our ingested data.
        Returns normalized post events.
        """
        logger.info(f"📥 [TrendsAgent] Fetching posts: platform={platform}, niche={niche}, window={window_hours}h")
        
        posts = []
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        
        with self.engine.connect() as conn:
            # Fetch from posted_content table (our tracked content)
            query = text("""
                SELECT 
                    pc.id, pc.platform, pc.caption, pc.posted_at,
                    pc.views, pc.likes, pc.comments, pc.shares,
                    pc.url, pc.media_type
                FROM posted_content pc
                WHERE pc.posted_at >= :cutoff
                AND (:platform = 'all' OR pc.platform = :platform)
                ORDER BY pc.posted_at DESC
                LIMIT :limit
            """)
            
            try:
                result = conn.execute(query, {
                    "cutoff": cutoff,
                    "platform": platform,
                    "limit": limit
                })
                
                for row in result:
                    posts.append({
                        "id": str(row[0]),
                        "platform": row[1],
                        "caption": row[2] or "",
                        "posted_at": row[3].isoformat() if row[3] else None,
                        "views": row[4] or 0,
                        "likes": row[5] or 0,
                        "comments": row[6] or 0,
                        "shares": row[7] or 0,
                        "url": row[8],
                        "media_type": row[9],
                    })
            except Exception as e:
                logger.warning(f"Posted content query failed: {e}")
            
            # Also fetch from trend_items if available
            try:
                trend_query = text("""
                    SELECT 
                        id, source, entity_type, entity_key, display_name,
                        metrics, velocity, volume, context, timestamp_bucket
                    FROM trend_items
                    WHERE timestamp_bucket >= :cutoff
                    AND (:platform = 'all' OR source = :platform)
                    ORDER BY velocity DESC NULLS LAST
                    LIMIT :limit
                """)
                
                result = conn.execute(trend_query, {
                    "cutoff": cutoff,
                    "platform": platform,
                    "limit": limit
                })
                
                for row in result:
                    posts.append({
                        "id": str(row[0]),
                        "platform": row[1],
                        "entity_type": row[2],
                        "entity_key": row[3],
                        "display_name": row[4],
                        "metrics": row[5] or {},
                        "velocity": float(row[6]) if row[6] else 0,
                        "volume": row[7] or 0,
                        "context": row[8] or {},
                        "timestamp": row[9].isoformat() if row[9] else None,
                    })
            except Exception as e:
                logger.debug(f"Trend items query failed (table may not exist): {e}")
        
        logger.info(f"📦 [TrendsAgent] Fetched {len(posts)} posts")
        return posts
    
    # =========================================================================
    # TOOL 2: EXTRACT PHRASES (N-GRAMS)
    # =========================================================================
    
    def extract_phrases(
        self,
        texts: List[str],
        min_ngram: int = 2,
        max_ngram: int = 6,
        min_frequency: int = 3
    ) -> List[Dict]:
        """
        Extract trending phrases (n-grams) from text corpus.
        Returns phrases with frequency and uniqueness scores.
        """
        logger.info(f"🔤 [TrendsAgent] Extracting phrases from {len(texts)} texts")
        
        # Normalize texts
        normalized = []
        for text in texts:
            if not text:
                continue
            # Lowercase, remove URLs, normalize whitespace
            clean = re.sub(r'https?://\S+', '', text.lower())
            clean = re.sub(r'@\w+', '', clean)  # Remove mentions
            clean = re.sub(r'\s+', ' ', clean).strip()
            normalized.append(clean)
        
        # Extract n-grams
        ngram_counts = Counter()
        
        for text in normalized:
            words = text.split()
            for n in range(min_ngram, min(max_ngram + 1, len(words) + 1)):
                for i in range(len(words) - n + 1):
                    ngram = ' '.join(words[i:i+n])
                    # Filter out low-quality n-grams
                    if len(ngram) > 5 and not ngram.startswith('#'):
                        ngram_counts[ngram] += 1
        
        # Filter by frequency and return top phrases
        phrases = []
        for phrase, count in ngram_counts.most_common(100):
            if count >= min_frequency:
                phrases.append({
                    "phrase": phrase,
                    "frequency": count,
                    "word_count": len(phrase.split()),
                    "uniqueness": count / len(texts) if texts else 0
                })
        
        logger.info(f"✅ [TrendsAgent] Extracted {len(phrases)} phrases")
        return phrases[:50]  # Top 50
    
    # =========================================================================
    # TOOL 3: COMPUTE VELOCITY
    # =========================================================================
    
    def compute_velocity(
        self,
        current_count: int,
        baseline_count: int,
        hours_elapsed: int = 24
    ) -> TrendSignals:
        """
        Compute velocity signals for a trend cluster.
        A trend isn't "popular" - it's "growing faster than normal."
        """
        # Avoid division by zero
        if baseline_count == 0:
            baseline_count = 1
        
        # Velocity = rate of change
        velocity_24h = current_count - baseline_count
        velocity_1h = velocity_24h / max(hours_elapsed, 1)
        
        # Growth rate
        growth_rate = (current_count - baseline_count) / baseline_count
        
        return TrendSignals(
            velocity_1h=round(velocity_1h, 2),
            velocity_24h=velocity_24h,
            engagement_rate_p50=0.05,  # Placeholder - would compute from actual data
            creator_diversity=min(current_count, 100),  # Placeholder
            spread=5,  # Placeholder
            freshness=1.0 - (hours_elapsed / 168)  # Decay over 1 week
        )
    
    # =========================================================================
    # TOOL 4: SUMMARIZE CONTEXT (AI)
    # =========================================================================
    
    async def summarize_context(
        self,
        phrase: str,
        examples: List[str],
        niche: str = "general"
    ) -> Tuple[LingoData, ContextData]:
        """
        Use AI to extract lingo meaning and context.
        This is "what people mean when they say X."
        """
        logger.info(f"🧠 [TrendsAgent] Summarizing context for: {phrase}")
        
        if not self.openai_client:
            # Fallback without AI
            return (
                LingoData(
                    key_phrases=[phrase],
                    usage_notes="Used in social media content",
                    variants=[],
                ),
                ContextData(
                    meaning="A trending phrase or format",
                    typical_structure=["setup", "reveal"],
                    do_not_use_if=["sensitive topics"],
                )
            )
        
        examples_text = "\n".join([f"- {ex[:200]}" for ex in examples[:10]])
        
        prompt = f"""Analyze this trending social media phrase/format: "{phrase}"

Example usages:
{examples_text}

Niche: {niche}

Provide analysis as JSON:
{{
  "lingo": {{
    "key_phrases": ["list of 3-5 key phrases/variants"],
    "usage_notes": "How creators typically use this (1-2 sentences)",
    "variants": ["common variations of this phrase"]
  }},
  "context": {{
    "meaning": "What this phrase/format actually means (1-2 sentences)",
    "typical_structure": ["setup element", "pivot/reveal", "tag/punchline"],
    "do_not_use_if": ["situations where this would be inappropriate"],
    "best_for": ["content types this works well for"],
    "tone": "casual/professional/humorous/inspirational"
  }}
}}

Respond with ONLY valid JSON."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a social media trend analyst. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            # Clean markdown if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            data = json.loads(content)
            
            lingo = LingoData(
                key_phrases=data.get("lingo", {}).get("key_phrases", [phrase]),
                usage_notes=data.get("lingo", {}).get("usage_notes", ""),
                variants=data.get("lingo", {}).get("variants", []),
            )
            
            context = ContextData(
                meaning=data.get("context", {}).get("meaning", ""),
                typical_structure=data.get("context", {}).get("typical_structure", []),
                do_not_use_if=data.get("context", {}).get("do_not_use_if", []),
                best_for=data.get("context", {}).get("best_for", []),
                tone=data.get("context", {}).get("tone", "casual"),
            )
            
            return lingo, context
            
        except Exception as e:
            logger.error(f"AI context summarization failed: {e}")
            return (
                LingoData(key_phrases=[phrase]),
                ContextData(meaning="Unable to analyze")
            )
    
    # =========================================================================
    # TOOL 5: GENERATE OUTPUTS (AI)
    # =========================================================================
    
    async def generate_outputs(
        self,
        trend_name: str,
        lingo: LingoData,
        context: ContextData,
        niche: str = "general",
        brand_voice: str = "engaging",
        platform: str = "tiktok"
    ) -> ContentReady:
        """
        Generate ready-to-post content outputs.
        This is what people integrate into their content engine.
        """
        logger.info(f"✨ [TrendsAgent] Generating outputs for: {trend_name}")
        
        if not self.openai_client:
            return ContentReady(
                hooks=[f"Wait for it... {trend_name}", f"You won't believe {trend_name}"],
                caption_templates=[f"{trend_name} and suddenly everything makes sense"],
                angles=["before/after", "hot take", "tutorial"],
                cta_options=["Save this for later", "Follow for more"],
            )
        
        prompt = f"""Generate content-ready outputs for this trend:

Trend: "{trend_name}"
Meaning: {context.meaning}
Structure: {context.typical_structure}
Niche: {niche}
Brand Voice: {brand_voice}
Platform: {platform}

Generate as JSON:
{{
  "hooks": ["3 attention-grabbing hooks (first 3 seconds, max 10 words each)"],
  "caption_templates": ["3 fill-in-the-blank caption templates using {{placeholder}} format"],
  "angles": ["4 unique content angles/approaches"],
  "cta_options": ["3 call-to-action options"]
}}

Make hooks punchy and scroll-stopping. Templates should be easy to customize.
Respond with ONLY valid JSON."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a viral content creator. Generate punchy, platform-native content. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.9
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            data = json.loads(content)
            
            return ContentReady(
                hooks=data.get("hooks", [])[:5],
                caption_templates=data.get("caption_templates", [])[:5],
                angles=data.get("angles", [])[:5],
                cta_options=data.get("cta_options", [])[:3],
            )
            
        except Exception as e:
            logger.error(f"AI output generation failed: {e}")
            return ContentReady(
                hooks=[f"{trend_name}... wait for it"],
                caption_templates=[f"{trend_name} {{your_take}}"],
                angles=["story", "tutorial", "reaction"],
            )
    
    # =========================================================================
    # TOOL 6: POLICY CHECK
    # =========================================================================
    
    def policy_check(self, content: str) -> Tuple[bool, List[str]]:
        """
        Check content for brand safety issues.
        Returns (is_safe, list_of_flags).
        """
        flags = []
        content_lower = content.lower()
        
        # Check for sensitive topics
        sensitive_patterns = [
            (r'\b(death|died|kill|suicide)\b', "mortality_reference"),
            (r'\b(hate|racist|sexist)\b', "hate_speech"),
            (r'\b(nude|porn|xxx)\b', "adult_content"),
            (r'\b(drug|cocaine|meth)\b', "drug_reference"),
            (r'\b(shooting|terror|bomb)\b', "violence"),
        ]
        
        for pattern, flag in sensitive_patterns:
            if re.search(pattern, content_lower):
                flags.append(flag)
        
        return (len(flags) == 0, flags)
    
    # =========================================================================
    # MAIN PIPELINE: DETECT TRENDS
    # =========================================================================
    
    async def detect_trends(
        self,
        platform: str = "all",
        niche: str = "general",
        window_hours: int = 24,
        min_velocity: float = 10,
        limit: int = 10
    ) -> List[TrendV1]:
        """
        Main trend detection pipeline.
        Returns a list of TrendV1 objects sorted by relevance.
        """
        logger.info(f"🔍 [TrendsAgent] Starting trend detection: platform={platform}, niche={niche}")
        
        # Step 1: Fetch recent posts
        posts = await self.fetch_recent_posts(platform, niche, window_hours)
        
        if not posts:
            logger.warning("[TrendsAgent] No posts found")
            return []
        
        # Step 2: Extract phrases
        captions = [p.get("caption", "") for p in posts if p.get("caption")]
        phrases = self.extract_phrases(captions)
        
        if not phrases:
            logger.warning("[TrendsAgent] No phrases extracted")
            return []
        
        # Step 3: Build trend objects
        trends = []
        
        for phrase_data in phrases[:limit]:
            phrase = phrase_data["phrase"]
            frequency = phrase_data["frequency"]
            
            # Compute velocity (simplified - baseline = frequency / 2)
            signals = self.compute_velocity(
                current_count=frequency,
                baseline_count=max(frequency // 2, 1),
                hours_elapsed=window_hours
            )
            
            # Skip low velocity trends
            if signals.velocity_24h < min_velocity:
                continue
            
            # Get example usages
            examples = [
                p.get("caption", "")
                for p in posts
                if phrase.lower() in p.get("caption", "").lower()
            ][:10]
            
            # Step 4: Summarize context (AI)
            lingo, context = await self.summarize_context(phrase, examples, niche)
            
            # Step 5: Generate outputs (AI)
            content_ready = await self.generate_outputs(
                trend_name=phrase,
                lingo=lingo,
                context=context,
                niche=niche,
                platform=platform
            )
            
            # Step 6: Policy check
            is_safe, flags = self.policy_check(phrase)
            
            # Determine stage based on velocity
            if signals.velocity_1h > 50:
                stage = TrendStage.EMERGING
            elif signals.velocity_24h > 100:
                stage = TrendStage.RISING
            else:
                stage = TrendStage.PEAK
            
            # Build TrendV1 object
            trend = TrendV1(
                trend_id=f"tr_{uuid.uuid4().hex[:8]}",
                detected_at=datetime.utcnow(),
                platforms=[platform] if platform != "all" else ["tiktok", "instagram"],
                cluster_type=ClusterType.PHRASE,
                trend_name=phrase,
                stage=stage,
                lingo=lingo,
                context=context,
                signals=signals,
                content_ready=content_ready,
                niche=niche,
                brand_safe=is_safe,
                confidence=min(frequency / 100, 1.0),
                source_post_count=len(examples),
            )
            
            trends.append(trend)
        
        # Sort by velocity
        trends.sort(key=lambda t: t.signals.velocity_24h, reverse=True)
        
        logger.info(f"✅ [TrendsAgent] Detected {len(trends)} trends")
        return trends[:limit]
    
    # =========================================================================
    # SAVE TRENDS TO DATABASE
    # =========================================================================
    
    async def save_trend(self, trend: TrendV1) -> str:
        """Save a trend to the database as a trend_opportunity."""
        with self.engine.connect() as conn:
            try:
                conn.execute(text("""
                    INSERT INTO trend_opportunities (
                        id, title, description, opportunity_score,
                        velocity_score, relevance_to_brand, content_fit,
                        priority, why, recommended_actions, window_end,
                        status, created_at
                    ) VALUES (
                        :id, :title, :description, :score,
                        :velocity, :relevance, :content_fit,
                        :priority, :why, :actions, :window_end,
                        'new', NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        opportunity_score = :score,
                        velocity_score = :velocity,
                        updated_at = NOW()
                """), {
                    "id": trend.trend_id,
                    "title": trend.trend_name,
                    "description": trend.context.meaning,
                    "score": trend.confidence * 100,
                    "velocity": trend.signals.velocity_24h,
                    "relevance": 50,
                    "content_fit": 50,
                    "priority": "high" if trend.stage == TrendStage.EMERGING else "medium",
                    "why": json.dumps(trend.lingo.to_dict()),
                    "actions": json.dumps(trend.content_ready.to_dict()),
                    "window_end": datetime.utcnow() + timedelta(hours=48),
                })
                conn.commit()
                logger.info(f"💾 [TrendsAgent] Saved trend: {trend.trend_id}")
                return trend.trend_id
            except Exception as e:
                logger.error(f"Failed to save trend: {e}")
                return None


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_trends_agent: Optional[TrendsAgent] = None

def get_trends_agent() -> TrendsAgent:
    global _trends_agent
    if _trends_agent is None:
        _trends_agent = TrendsAgent()
    return _trends_agent
