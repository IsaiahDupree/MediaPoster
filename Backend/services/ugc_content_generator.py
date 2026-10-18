"""
UGC Content Generator — Offer-Aware
=====================================
Generates UGC video scripts (talking-head + Sora AI) tailored to specific offers,
powered by live trends and the @isaiahdupree character definition.

Pipeline:
1. Load offer details from DB (title, description, CTA, landing page, brand)
2. Fetch current trends (reuse SoraScriptGenerator's TrendFetcher)
3. Generate UGC script packages via OpenAI:
   - Talking-head scripts (30s / 60s)
   - Sora AI video prompts
   - Platform-optimized captions + hashtags
   - Tracked CTA links (via OfferTracker)
4. Persist to DB for review / editing
5. Optionally auto-queue to publish pipeline

Callable from any external server via the /api/ugc-content/* endpoints.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4
from dataclasses import dataclass, field, asdict

from sqlalchemy import create_engine, text

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:54322/postgres",
)

# Character definition (shared with Sora script gen)
ISAIAH_CHARACTER = {
    "handle": "@isaiahdupree",
    "visual_description": (
        "Isaiah, a charismatic Black man in his late 20s with a warm smile, "
        "wearing a casual hoodie and gold chain, expressive and humorous"
    ),
    "brand_pillars": [
        "content creation & automation",
        "personal branding",
        "tech entrepreneurship",
        "authentic storytelling",
        "humor & relatability",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UGCScript:
    """A single generated UGC script tied to an offer."""
    id: str = field(default_factory=lambda: str(uuid4()))
    offer_id: str = ""
    offer_title: str = ""
    brand_id: str = ""

    # Script content
    title: str = ""
    hook: str = ""
    body: str = ""
    cta: str = ""
    caption: str = ""
    hashtags: List[str] = field(default_factory=list)

    # Script metadata
    format_type: str = "talking_head"  # talking_head | sora_ai | broll_overlay | screen_recording
    duration_seconds: int = 30
    sora_prompt: Optional[str] = None  # Only for sora_ai format
    suggested_audio: Optional[str] = None
    visual_notes: str = ""

    # Targeting
    platforms: List[str] = field(default_factory=lambda: ["tiktok", "instagram", "youtube_shorts"])
    target_audience: str = ""
    awareness_level: str = "problem_aware"  # unaware | problem_aware | solution_aware | product_aware

    # Offer integration
    tracked_url: Optional[str] = None  # UTM-tagged offer URL
    cta_text: str = ""
    landing_page_url: str = ""

    # Trend data
    trend_name: str = ""
    trend_source: str = ""

    # Status
    status: str = "generated"  # generated | approved | queued | published | archived
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "offer_id": self.offer_id,
            "offer_title": self.offer_title,
            "brand_id": self.brand_id,
            "title": self.title,
            "hook": self.hook,
            "body": self.body,
            "cta": self.cta,
            "caption": self.caption,
            "hashtags": self.hashtags,
            "format_type": self.format_type,
            "duration_seconds": self.duration_seconds,
            "sora_prompt": self.sora_prompt,
            "suggested_audio": self.suggested_audio,
            "visual_notes": self.visual_notes,
            "platforms": self.platforms,
            "target_audience": self.target_audience,
            "awareness_level": self.awareness_level,
            "tracked_url": self.tracked_url,
            "cta_text": self.cta_text,
            "landing_page_url": self.landing_page_url,
            "trend_name": self.trend_name,
            "trend_source": self.trend_source,
            "status": self.status,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# GENERATOR ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class UGCContentGenerator:
    """
    Generates offer-aware UGC scripts using trends + OpenAI.

    Usage:
        gen = UGCContentGenerator()

        # Generate talking-head scripts for an offer
        scripts = await gen.generate_for_offer(offer_id="...", count=5)

        # Generate Sora AI video prompts for an offer
        scripts = await gen.generate_sora_for_offer(offer_id="...", count=3)

        # Generate with manual trend descriptions
        scripts = await gen.generate_for_offer(
            offer_id="...",
            trend_descriptions=["POV trend where...", "Get ready with me..."],
        )

        # Auto-queue approved scripts to publish pipeline
        gen.queue_scripts([script_id_1, script_id_2], platform="tiktok", account_id="710")
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=api_key) if api_key and OpenAI else None
        self.engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        self._ensure_tables()
        logger.info("🎬 UGCContentGenerator initialized")

    def _ensure_tables(self):
        """Create storage table if not exists."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ugc_generated_scripts (
                        id TEXT PRIMARY KEY,
                        offer_id TEXT,
                        offer_title TEXT,
                        brand_id TEXT,
                        title TEXT NOT NULL,
                        hook TEXT,
                        body TEXT,
                        cta TEXT,
                        caption TEXT,
                        hashtags JSONB DEFAULT '[]'::jsonb,
                        format_type TEXT DEFAULT 'talking_head',
                        duration_seconds INT DEFAULT 30,
                        sora_prompt TEXT,
                        suggested_audio TEXT,
                        visual_notes TEXT,
                        platforms JSONB DEFAULT '["tiktok","instagram","youtube_shorts"]'::jsonb,
                        target_audience TEXT,
                        awareness_level TEXT DEFAULT 'problem_aware',
                        tracked_url TEXT,
                        cta_text TEXT,
                        landing_page_url TEXT,
                        trend_name TEXT,
                        trend_source TEXT,
                        status TEXT DEFAULT 'generated',
                        generated_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_ugc_scripts_offer ON ugc_generated_scripts(offer_id)"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_ugc_scripts_status ON ugc_generated_scripts(status)"
                ))
                conn.commit()
        except Exception as e:
            logger.debug(f"UGC table creation note: {e}")

    # ─────────────────────────────────────────────────────────────
    # OFFER DATA LOADING
    # ─────────────────────────────────────────────────────────────

    def _load_offer(self, offer_id: str) -> Optional[Dict[str, Any]]:
        """Load offer details from DB."""
        try:
            with self.engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT o.id, o.title, o.description, o.offer_type,
                           o.landing_page_url, o.cta_text, o.terms, o.price,
                           o.currency, o.brand_id,
                           b.name as brand_name, b.description as brand_description
                    FROM offers o
                    LEFT JOIN brands b ON o.brand_id = b.id
                    WHERE o.id = :offer_id AND o.is_active = true
                """), {"offer_id": offer_id}).fetchone()

                if not row:
                    return None

                return {
                    "id": str(row[0]),
                    "title": row[1],
                    "description": row[2] or "",
                    "offer_type": row[3] or "product",
                    "landing_page_url": row[4] or "",
                    "cta_text": row[5] or "Check it out",
                    "terms": row[6] or "",
                    "price": float(row[7]) if row[7] else None,
                    "currency": row[8] or "USD",
                    "brand_id": str(row[9]) if row[9] else "",
                    "brand_name": row[10] or "",
                    "brand_description": row[11] or "",
                }
        except Exception as e:
            logger.error(f"Failed to load offer {offer_id}: {e}")
            return None

    def _load_active_offers(self) -> List[Dict[str, Any]]:
        """Load all active offers."""
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT o.id, o.title, o.description, o.offer_type,
                           o.landing_page_url, o.cta_text, o.brand_id,
                           b.name as brand_name
                    FROM offers o
                    LEFT JOIN brands b ON o.brand_id = b.id
                    WHERE o.is_active = true
                    ORDER BY o.priority DESC, o.created_at DESC
                """)).fetchall()

                return [
                    {
                        "id": str(r[0]),
                        "title": r[1],
                        "description": r[2] or "",
                        "offer_type": r[3] or "product",
                        "landing_page_url": r[4] or "",
                        "cta_text": r[5] or "Check it out",
                        "brand_id": str(r[6]) if r[6] else "",
                        "brand_name": r[7] or "",
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Failed to load active offers: {e}")
            return []

    # ─────────────────────────────────────────────────────────────
    # TREND FETCHING (reuses existing infra)
    # ─────────────────────────────────────────────────────────────

    async def _fetch_trends(self) -> List[Dict[str, Any]]:
        """Fetch current trends from internal systems."""
        trends = []

        # Source 1: Sora script generator's TrendFetcher
        try:
            from services.sora_daily.script_generator import TrendFetcher
            fetcher = TrendFetcher()
            web_trends = await fetcher.fetch_live_trends(max_sources=2)
            trends.extend(web_trends)
        except Exception as e:
            logger.warning(f"TrendFetcher unavailable: {e}")

        # Source 2: Internal trend collector
        try:
            from services.sora_daily.trend_collector import get_trend_collector
            collector = get_trend_collector()
            internal = collector.get_unused_trends(limit=10)
            for t in internal:
                trends.append({
                    "trend_name": t.topic,
                    "description": t.topic,
                    "platform": t.source_type,
                    "source": "internal_collector",
                })
        except Exception:
            pass

        # Source 3: Trending keywords service
        try:
            from services.trending_keywords_service import TrendingKeywordsService
            kw_svc = TrendingKeywordsService()
            keywords = kw_svc.get_trending(limit=10)
            for kw in keywords:
                trends.append({
                    "trend_name": kw.get("keyword", ""),
                    "description": kw.get("context", ""),
                    "platform": "multi",
                    "source": "keyword_service",
                })
        except Exception:
            pass

        if not trends:
            trends = self._get_fallback_trends()

        return trends

    def _get_fallback_trends(self) -> List[Dict[str, Any]]:
        """Fallback trends when live fetch fails."""
        return [
            {"trend_name": "Day in the Life", "description": "Aesthetic creator day-in-the-life montage", "platform": "tiktok", "source": "fallback"},
            {"trend_name": "Get Ready With Me", "description": "GRWM while sharing tips or product recs", "platform": "instagram", "source": "fallback"},
            {"trend_name": "POV: You Discovered…", "description": "POV format revealing a product or hack", "platform": "tiktok", "source": "fallback"},
            {"trend_name": "Things I Wish I Knew", "description": "Listicle of lessons or tips", "platform": "multi", "source": "fallback"},
            {"trend_name": "Before/After Transformation", "description": "Show dramatic change from using a tool/product", "platform": "youtube_shorts", "source": "fallback"},
        ]

    # ─────────────────────────────────────────────────────────────
    # GENERATION: Talking-Head UGC Scripts
    # ─────────────────────────────────────────────────────────────

    async def generate_for_offer(
        self,
        offer_id: str,
        count: int = 5,
        formats: Optional[List[str]] = None,
        trend_descriptions: Optional[List[str]] = None,
        platforms: Optional[List[str]] = None,
        duration: int = 30,
    ) -> List[UGCScript]:
        """
        Generate UGC scripts for a specific offer.

        Args:
            offer_id: Offer UUID from the offers table
            count: Number of scripts to generate
            formats: List of formats (talking_head, sora_ai, broll_overlay). Default: mix
            trend_descriptions: Optional manual trend descriptions to use
            platforms: Target platforms. Default: tiktok, instagram, youtube_shorts
            duration: Target duration in seconds (30 or 60)

        Returns:
            List of generated UGCScript objects (persisted to DB)
        """
        # Load offer
        offer = self._load_offer(offer_id)
        if not offer:
            logger.error(f"Offer {offer_id} not found or inactive")
            return []

        # Fetch trends
        if trend_descriptions:
            trends = [
                {"trend_name": f"Manual Trend {i+1}", "description": d, "platform": "multi", "source": "manual"}
                for i, d in enumerate(trend_descriptions)
            ]
        else:
            trends = await self._fetch_trends()

        formats = formats or ["talking_head", "sora_ai"]
        platforms = platforms or ["tiktok", "instagram", "youtube_shorts"]

        # Create tracked offer URL
        tracked_url = offer["landing_page_url"]
        try:
            from services.offer_tracker import get_offer_tracker
            tracker = get_offer_tracker()
            tracked_url = await tracker.create_tracked_link(
                offer_url=offer["landing_page_url"],
                campaign=f"ugc_{offer['title'].lower().replace(' ', '_')[:30]}",
                source="ugc_generator",
            )
        except Exception as e:
            logger.warning(f"Could not create tracked link: {e}")

        # Generate via OpenAI
        scripts = await self._generate_scripts(
            offer=offer,
            trends=trends,
            count=count,
            formats=formats,
            platforms=platforms,
            duration=duration,
            tracked_url=tracked_url,
        )

        # Persist
        for script in scripts:
            self._save_script(script)

        logger.info(f"🎬 Generated {len(scripts)} UGC scripts for offer '{offer['title']}'")
        return scripts

    async def generate_for_all_offers(
        self,
        count_per_offer: int = 3,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, List[UGCScript]]:
        """Generate UGC scripts for ALL active offers."""
        offers = self._load_active_offers()
        if not offers:
            logger.warning("No active offers found")
            return {}

        results = {}
        for offer in offers:
            scripts = await self.generate_for_offer(
                offer_id=offer["id"],
                count=count_per_offer,
                formats=formats,
            )
            results[offer["id"]] = scripts

        return results

    async def _generate_scripts(
        self,
        offer: Dict[str, Any],
        trends: List[Dict[str, Any]],
        count: int,
        formats: List[str],
        platforms: List[str],
        duration: int,
        tracked_url: str,
    ) -> List[UGCScript]:
        """Core OpenAI generation."""
        if not self.openai_client:
            logger.error("OpenAI client required for UGC generation")
            return []

        trends_json = json.dumps(trends[:10], indent=2, default=str)
        character_json = json.dumps(ISAIAH_CHARACTER, indent=2)
        formats_str = ", ".join(formats)

        prompt = f"""You are a UGC script writer for the creator @isaiahdupree.

CHARACTER:
{character_json}

OFFER TO PROMOTE:
- Title: {offer['title']}
- Description: {offer['description']}
- Type: {offer['offer_type']}
- CTA: {offer['cta_text']}
- Landing Page: {offer['landing_page_url']}
- Brand: {offer.get('brand_name', 'N/A')}
- Price: {offer.get('price', 'N/A')} {offer.get('currency', '')}

CURRENT TRENDS:
{trends_json}

TASK:
Generate {count} UGC video scripts that naturally promote the offer while tapping into current trends.
Each script should feel authentic, NOT like an ad. The offer promotion should be woven into genuine value.

FORMATS TO USE: {formats_str}
TARGET DURATION: {duration} seconds per script
TARGET PLATFORMS: {json.dumps(platforms)}

Return a JSON object:
{{
  "scripts": [
    {{
      "title": "Catchy script title",
      "format_type": "talking_head" or "sora_ai" or "broll_overlay",
      "hook": "First 3 seconds — attention-grabbing opener (under 15 words)",
      "body": "Main content (15-25 seconds). Share genuine value. Weave in the offer naturally.",
      "cta": "Last 5 seconds — natural call to action mentioning the offer",
      "caption": "Full social media caption with emoji and line breaks",
      "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
      "sora_prompt": "ONLY for sora_ai format: Detailed Sora video prompt with @isaiahdupree, camera movements, lighting, wardrobe (casual hoodie, gold chain). End with 'Portrait 9:16, cinematic 4K.' NULL for other formats.",
      "suggested_audio": "Trending song/sound name or null",
      "visual_notes": "Brief notes on visuals, transitions, text overlays",
      "target_audience": "Who this appeals to",
      "awareness_level": "unaware|problem_aware|solution_aware|product_aware",
      "trend_name": "Which trend this taps into",
      "duration_seconds": {duration}
    }}
  ]
}}

RULES:
- Scripts must feel like genuine creator content, NOT ads
- The offer should be the solution to a real problem presented in the video
- Hooks must stop the scroll — use curiosity, bold claims, or relatable pain points
- Each script should tap into a DIFFERENT trend
- Mix awareness levels: some for cold audiences, some for warm
- Captions should include the tracked link: {tracked_url}
- For sora_ai format: prompts must start with "@isaiahdupree" and include wardrobe + camera details
- For talking_head: write actual dialogue with timing markers [0:00-0:03], [0:03-0:25], [0:25-0:{duration}]"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You write authentic UGC video scripts that promote products naturally. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.85,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            raw_scripts = result.get("scripts", [])

            scripts = []
            for raw in raw_scripts:
                script = UGCScript(
                    offer_id=offer["id"],
                    offer_title=offer["title"],
                    brand_id=offer.get("brand_id", ""),
                    title=raw.get("title", "Untitled"),
                    hook=raw.get("hook", ""),
                    body=raw.get("body", ""),
                    cta=raw.get("cta", ""),
                    caption=raw.get("caption", ""),
                    hashtags=raw.get("hashtags", []),
                    format_type=raw.get("format_type", "talking_head"),
                    duration_seconds=raw.get("duration_seconds", duration),
                    sora_prompt=raw.get("sora_prompt"),
                    suggested_audio=raw.get("suggested_audio"),
                    visual_notes=raw.get("visual_notes", ""),
                    platforms=platforms,
                    target_audience=raw.get("target_audience", ""),
                    awareness_level=raw.get("awareness_level", "problem_aware"),
                    tracked_url=tracked_url,
                    cta_text=offer["cta_text"],
                    landing_page_url=offer["landing_page_url"],
                    trend_name=raw.get("trend_name", ""),
                    trend_source="ugc_generator",
                )
                scripts.append(script)

            return scripts

        except Exception as e:
            logger.error(f"UGC script generation failed: {e}")
            return []

    # ─────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────

    def _save_script(self, script: UGCScript):
        """Persist a UGC script to the database."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO ugc_generated_scripts
                        (id, offer_id, offer_title, brand_id, title, hook, body, cta,
                         caption, hashtags, format_type, duration_seconds, sora_prompt,
                         suggested_audio, visual_notes, platforms, target_audience,
                         awareness_level, tracked_url, cta_text, landing_page_url,
                         trend_name, trend_source, status, generated_at)
                    VALUES
                        (:id, :offer_id, :offer_title, :brand_id, :title, :hook, :body, :cta,
                         :caption, :hashtags, :format_type, :duration_seconds, :sora_prompt,
                         :suggested_audio, :visual_notes, :platforms, :target_audience,
                         :awareness_level, :tracked_url, :cta_text, :landing_page_url,
                         :trend_name, :trend_source, :status, :generated_at)
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        updated_at = NOW()
                """), {
                    "id": script.id,
                    "offer_id": script.offer_id,
                    "offer_title": script.offer_title,
                    "brand_id": script.brand_id,
                    "title": script.title,
                    "hook": script.hook,
                    "body": script.body,
                    "cta": script.cta,
                    "caption": script.caption,
                    "hashtags": json.dumps(script.hashtags),
                    "format_type": script.format_type,
                    "duration_seconds": script.duration_seconds,
                    "sora_prompt": script.sora_prompt,
                    "suggested_audio": script.suggested_audio,
                    "visual_notes": script.visual_notes,
                    "platforms": json.dumps(script.platforms),
                    "target_audience": script.target_audience,
                    "awareness_level": script.awareness_level,
                    "tracked_url": script.tracked_url,
                    "cta_text": script.cta_text,
                    "landing_page_url": script.landing_page_url,
                    "trend_name": script.trend_name,
                    "trend_source": script.trend_source,
                    "status": script.status,
                    "generated_at": script.generated_at,
                })
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save UGC script {script.id}: {e}")

    # ─────────────────────────────────────────────────────────────
    # RETRIEVAL + STATUS MANAGEMENT
    # ─────────────────────────────────────────────────────────────

    def get_scripts(
        self,
        offer_id: Optional[str] = None,
        status: Optional[str] = None,
        format_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[UGCScript]:
        """Retrieve generated UGC scripts with filters."""
        try:
            query = "SELECT * FROM ugc_generated_scripts WHERE 1=1"
            params: Dict[str, Any] = {"limit": limit}

            if offer_id:
                query += " AND offer_id = :offer_id"
                params["offer_id"] = offer_id
            if status:
                query += " AND status = :status"
                params["status"] = status
            if format_type:
                query += " AND format_type = :format_type"
                params["format_type"] = format_type

            query += " ORDER BY generated_at DESC LIMIT :limit"

            with self.engine.connect() as conn:
                rows = conn.execute(text(query), params).fetchall()
                return [self._row_to_script(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to get UGC scripts: {e}")
            return []

    def get_script_by_id(self, script_id: str) -> Optional[UGCScript]:
        """Get a single script by ID."""
        try:
            with self.engine.connect() as conn:
                row = conn.execute(text(
                    "SELECT * FROM ugc_generated_scripts WHERE id = :id"
                ), {"id": script_id}).fetchone()
                return self._row_to_script(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get script {script_id}: {e}")
            return None

    def update_script_status(self, script_id: str, status: str) -> bool:
        """Update script status (generated → approved → queued → published)."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    UPDATE ugc_generated_scripts
                    SET status = :status, updated_at = NOW()
                    WHERE id = :id
                    RETURNING id
                """), {"id": script_id, "status": status})
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update script status: {e}")
            return False

    def update_script(self, script_id: str, **kwargs) -> bool:
        """Update script fields (caption, hook, body, etc.)."""
        allowed = {
            "title", "hook", "body", "cta", "caption", "hashtags",
            "sora_prompt", "visual_notes", "suggested_audio", "status",
            "platforms", "target_audience", "awareness_level",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not updates:
            return False

        # Serialize JSON fields
        for json_field in ("hashtags", "platforms"):
            if json_field in updates and isinstance(updates[json_field], list):
                updates[json_field] = json.dumps(updates[json_field])

        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = script_id

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    f"UPDATE ugc_generated_scripts SET {set_clause}, updated_at = NOW() WHERE id = :id RETURNING id"
                ), updates)
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update script {script_id}: {e}")
            return False

    def delete_script(self, script_id: str) -> bool:
        """Delete a script."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "DELETE FROM ugc_generated_scripts WHERE id = :id RETURNING id"
                ), {"id": script_id})
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete script: {e}")
            return False

    # ─────────────────────────────────────────────────────────────
    # QUEUE INTEGRATION — push approved scripts to publish pipeline
    # ─────────────────────────────────────────────────────────────

    def queue_script_for_publishing(
        self,
        script_id: str,
        platform: str,
        account_id: str,
        account_username: str = "",
        video_url: str = "",
        scheduled_for: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Push an approved UGC script into the video publishing queue.

        Requires the script to have status 'approved' and a video_url
        (the recorded/rendered video file).
        """
        script = self.get_script_by_id(script_id)
        if not script:
            logger.error(f"Script {script_id} not found")
            return None

        if script.status not in ("approved", "generated"):
            logger.warning(f"Script {script_id} status is '{script.status}', expected 'approved'")

        try:
            from services.video_publishing_controller import get_publishing_controller
            controller = get_publishing_controller()

            item = controller.enqueue_video(
                video_url=video_url,
                caption=script.caption,
                platform=platform,
                account_id=account_id,
                title=script.title,
                account_username=account_username,
                hashtags=script.hashtags,
                priority=3,
                scheduled_for=scheduled_for,
                metadata={
                    "ugc_script_id": script.id,
                    "offer_id": script.offer_id,
                    "format_type": script.format_type,
                    "tracked_url": script.tracked_url,
                },
            )

            # Mark script as queued
            self.update_script_status(script_id, "queued")

            return item.to_dict()

        except Exception as e:
            logger.error(f"Failed to queue script {script_id}: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get UGC generation stats."""
        try:
            with self.engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'generated') as generated,
                        COUNT(*) FILTER (WHERE status = 'approved') as approved,
                        COUNT(*) FILTER (WHERE status = 'queued') as queued,
                        COUNT(*) FILTER (WHERE status = 'published') as published,
                        COUNT(DISTINCT offer_id) as offers_covered,
                        COUNT(DISTINCT format_type) as format_types
                    FROM ugc_generated_scripts
                """)).fetchone()
                return {
                    "total": row[0],
                    "by_status": {
                        "generated": row[1],
                        "approved": row[2],
                        "queued": row[3],
                        "published": row[4],
                    },
                    "offers_covered": row[5],
                    "format_types": row[6],
                }
        except Exception as e:
            logger.error(f"Failed to get UGC stats: {e}")
            return {"total": 0, "by_status": {}, "offers_covered": 0, "format_types": 0}

    # ─────────────────────────────────────────────────────────────
    # ROW MAPPING
    # ─────────────────────────────────────────────────────────────

    def _row_to_script(self, row) -> UGCScript:
        """Convert DB row to UGCScript."""
        hashtags = row[9] if isinstance(row[9], list) else json.loads(row[9] or "[]")
        platforms = row[15] if isinstance(row[15], list) else json.loads(row[15] or "[]")
        return UGCScript(
            id=row[0],
            offer_id=row[1] or "",
            offer_title=row[2] or "",
            brand_id=row[3] or "",
            title=row[4] or "",
            hook=row[5] or "",
            body=row[6] or "",
            cta=row[7] or "",
            caption=row[8] or "",
            hashtags=hashtags,
            format_type=row[10] or "talking_head",
            duration_seconds=row[11] or 30,
            sora_prompt=row[12],
            suggested_audio=row[13],
            visual_notes=row[14] or "",
            platforms=platforms,
            target_audience=row[16] or "",
            awareness_level=row[17] or "problem_aware",
            tracked_url=row[18],
            cta_text=row[19] or "",
            landing_page_url=row[20] or "",
            trend_name=row[21] or "",
            trend_source=row[22] or "",
            status=row[23] or "generated",
            generated_at=row[24] if row[24] else datetime.now(timezone.utc),
        )


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON
# ─────────────────────────────────────────────────────────────────────────────

_generator_instance: Optional[UGCContentGenerator] = None


def get_ugc_generator() -> UGCContentGenerator:
    """Get or create singleton UGCContentGenerator."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = UGCContentGenerator()
    return _generator_instance
