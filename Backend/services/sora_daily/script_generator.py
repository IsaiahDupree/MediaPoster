"""
Dynamic Sora Script Generator
===============================
Fetches live social media trends and generates complete Sora script packages
for @isaiahdupree on demand.

Pipeline:
1. Fetch trends from external sources (web trend reports) OR accept manual input
2. Combine with character definition + brand pillars
3. Use OpenAI to generate full script packages (Sora prompts, captions, hashtags, audio)
4. Persist to database for browsing, editing, and queuing
5. Feed into SoraScheduler / SoraWorker for actual generation

Trigger modes:
- API on-demand: POST /sora-daily/scripts/generate
- Scheduled: Cron-triggered weekly/monthly refresh
- Manual: Provide your own trend descriptions
"""

import os
import json
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4
from dataclasses import dataclass, field, asdict
from loguru import logger
from sqlalchemy import create_engine, text

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from services.sora_daily.trend_prompts import ISAIAH_CHARACTER, TrendPrompt


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class ScriptPackage:
    """A complete generated script package — one or more Sora prompts + metadata."""
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    trend_name: str = ""
    trend_source: str = ""
    format_type: str = "single"  # single | series
    character: str = "@isaiahdupree"
    month: str = ""

    # Content
    parts: List[Dict[str, Any]] = field(default_factory=list)
    # Each part: {sora_prompt, caption, hashtags, suggested_audio, duration_seconds}

    # Metadata
    platforms: List[str] = field(default_factory=lambda: ["tiktok", "instagram", "youtube_shorts"])
    status: str = "generated"  # generated | approved | queued | used | archived
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_trends_raw: str = ""  # The raw trend data that informed this script

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "trend_name": self.trend_name,
            "trend_source": self.trend_source,
            "format_type": self.format_type,
            "character": self.character,
            "month": self.month,
            "parts": self.parts,
            "platforms": self.platforms,
            "status": self.status,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }


# =============================================================================
# TREND FETCHER — live external data
# =============================================================================

class TrendFetcher:
    """
    Fetches current social media trends from external web sources.
    Uses httpx to pull trend report pages and OpenAI to extract structured data.
    """

    # Well-known trend report URLs (rotated/checked monthly)
    TREND_SOURCES = [
        {
            "name": "NapoleonCat TikTok Trends",
            "url": "https://napoleoncat.com/blog/tiktok-trends/",
            "platform": "tiktok",
        },
        {
            "name": "Later TikTok Trends",
            "url": "https://later.com/blog/tiktok-trends/",
            "platform": "tiktok",
        },
        {
            "name": "Sprout Social Trends",
            "url": "https://sproutsocial.com/insights/social-media-trends/",
            "platform": "multi",
        },
    ]

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=api_key) if api_key and OpenAI else None

    async def fetch_live_trends(self, max_sources: int = 2) -> List[Dict[str, Any]]:
        """
        Fetch and extract structured trends from web sources.

        Returns list of:
            {"trend_name": str, "description": str, "platform": str, "source": str}
        """
        raw_texts = await self._scrape_sources(max_sources)
        if not raw_texts:
            logger.warning("No trend data fetched from web sources")
            return []

        return await self._extract_trends_from_text(raw_texts)

    async def _scrape_sources(self, max_sources: int) -> List[Dict[str, str]]:
        """Fetch HTML/text from trend report URLs."""
        results = []
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for source in self.TREND_SOURCES[:max_sources]:
                try:
                    resp = await client.get(source["url"], headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) MediaPoster/1.0"
                    })
                    if resp.status_code == 200:
                        # Take first 8000 chars of body text (enough for trend extraction)
                        body = resp.text[:8000]
                        results.append({
                            "source_name": source["name"],
                            "platform": source["platform"],
                            "text": body,
                        })
                        logger.info(f"📡 Fetched trends from {source['name']}")
                except Exception as e:
                    logger.warning(f"Failed to fetch {source['name']}: {e}")
        return results

    async def _extract_trends_from_text(self, raw_texts: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Use OpenAI to extract structured trend data from raw web text."""
        if not self.openai_client:
            logger.warning("OpenAI client not available — returning empty trends")
            return []

        combined = "\n\n---\n\n".join(
            f"Source: {t['source_name']} ({t['platform']})\n{t['text'][:3000]}"
            for t in raw_texts
        )

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You extract structured social media trends from web articles.

Return a JSON object:
{
  "trends": [
    {
      "trend_name": "short name of the trend",
      "description": "2-3 sentence description of how creators use this trend",
      "platform": "tiktok|instagram|youtube|multi",
      "format": "single|series",
      "suggested_audio": "song or sound name if mentioned, else null",
      "virality": "high|medium|low"
    }
  ]
}

Extract 5-10 trends. Focus on trends that are:
- Currently active (this month)
- Adaptable to a tech/personal brand creator
- Visually interesting for AI video generation
- Not tied to a single specific audio that won't work in AI video"""
                    },
                    {"role": "user", "content": combined}
                ],
                temperature=0.5,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            trends = result.get("trends", [])
            # Annotate with source
            for t in trends:
                t["source"] = "web_scrape"
                t["fetched_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"📈 Extracted {len(trends)} trends from web data")
            return trends
        except Exception as e:
            logger.error(f"Trend extraction failed: {e}")
            return []


# =============================================================================
# SCRIPT GENERATOR ENGINE
# =============================================================================

class SoraScriptGenerator:
    """
    The main engine: takes trend data and produces complete Sora script packages.

    Usage:
        gen = SoraScriptGenerator()

        # From live web trends
        scripts = await gen.generate_from_live_trends(count=5)

        # From manual trend descriptions
        scripts = await gen.generate_from_descriptions([
            "Reality TV edit trend where creators...",
            "AI sky writing manifestation trend..."
        ])

        # From internal trend collector
        scripts = await gen.generate_from_collected_trends()
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=api_key) if api_key and OpenAI else None
        self.trend_fetcher = TrendFetcher()
        self.engine = create_engine(DATABASE_URL)
        self._ensure_tables()
        logger.info("🎬 SoraScriptGenerator initialized")

    def _ensure_tables(self):
        """Create script storage tables if they don't exist."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS sora_generated_scripts (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        trend_name TEXT,
                        trend_source TEXT,
                        format_type TEXT DEFAULT 'single',
                        character TEXT DEFAULT '@isaiahdupree',
                        month TEXT,
                        parts JSONB DEFAULT '[]'::jsonb,
                        platforms JSONB DEFAULT '["tiktok","instagram","youtube_shorts"]'::jsonb,
                        status TEXT DEFAULT 'generated',
                        source_trends_raw TEXT,
                        generated_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_sora_scripts_month
                    ON sora_generated_scripts(month)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_sora_scripts_status
                    ON sora_generated_scripts(status)
                """))
                conn.commit()
        except Exception as e:
            logger.debug(f"Table creation note: {e}")

    # ─────────────────────────────────────────────────────────────
    # PUBLIC API: Generate from different sources
    # ─────────────────────────────────────────────────────────────

    async def generate_from_live_trends(
        self,
        count: int = 5,
        include_series: bool = True,
    ) -> List[ScriptPackage]:
        """
        Full pipeline: fetch live web trends → generate scripts → persist.
        """
        logger.info("🌐 Fetching live trends from web sources...")
        trends = await self.trend_fetcher.fetch_live_trends()

        if not trends:
            logger.warning("No live trends found — using fallback trends")
            trends = self._get_fallback_trends()

        return await self._generate_scripts_from_trends(trends, count, include_series)

    async def generate_from_descriptions(
        self,
        descriptions: List[str],
        include_series: bool = True,
    ) -> List[ScriptPackage]:
        """
        Generate scripts from manually provided trend descriptions.
        """
        trends = [
            {
                "trend_name": f"Custom Trend {i+1}",
                "description": desc,
                "platform": "multi",
                "format": "single",
                "source": "manual",
            }
            for i, desc in enumerate(descriptions)
        ]
        return await self._generate_scripts_from_trends(trends, len(descriptions), include_series)

    async def generate_from_collected_trends(
        self,
        count: int = 5,
        include_series: bool = True,
    ) -> List[ScriptPackage]:
        """
        Generate scripts from the internal TrendCollector's stored trends.
        """
        try:
            from services.sora_daily.trend_collector import get_trend_collector
            collector = get_trend_collector()
            raw_trends = collector.get_unused_trends(limit=count * 2)
            trends = [
                {
                    "trend_name": t.topic,
                    "description": t.topic,
                    "platform": t.source_type,
                    "format": "single",
                    "source": "internal_collector",
                    "relevance_score": t.relevance_score,
                }
                for t in raw_trends
            ]
        except Exception as e:
            logger.warning(f"Internal trend collector unavailable: {e}")
            trends = self._get_fallback_trends()

        return await self._generate_scripts_from_trends(trends, count, include_series)

    # ─────────────────────────────────────────────────────────────
    # CORE: AI script generation
    # ─────────────────────────────────────────────────────────────

    async def _generate_scripts_from_trends(
        self,
        trends: List[Dict],
        count: int,
        include_series: bool,
    ) -> List[ScriptPackage]:
        """Core method: take structured trends and produce ScriptPackages."""
        if not self.openai_client:
            logger.error("OpenAI client required for script generation")
            return []

        month = datetime.now(timezone.utc).strftime("%Y-%m")
        scripts: List[ScriptPackage] = []

        # Ask AI to generate complete script packages for each trend
        trends_json = json.dumps(trends[:count * 2], indent=2, default=str)
        character_json = json.dumps(ISAIAH_CHARACTER, indent=2)

        series_instruction = ""
        if include_series:
            series_instruction = (
                "For trends that suit a narrative arc, create a 3-part series "
                "(format_type='series' with 3 parts). Otherwise use format_type='single'."
            )

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a Sora AI video script writer for the character @isaiahdupree.

CHARACTER DEFINITION:
{character_json}

YOUR JOB:
Given a list of current social media trends, generate {count} complete Sora video script packages. Each script should tap into one of the trends while staying on-brand.

{series_instruction}

Return a JSON object:
{{
  "scripts": [
    {{
      "title": "Short catchy title",
      "trend_name": "Name of the trend it's based on",
      "trend_source": "Where the trend is from",
      "format_type": "single" or "series",
      "platforms": ["tiktok", "instagram", "youtube_shorts"],
      "parts": [
        {{
          "part_number": 1,
          "sora_prompt": "Detailed Sora video generation prompt. Include @isaiahdupree, specific camera movements, lighting, mood, setting, wardrobe. End with 'Portrait 9:16, cinematic 4K.'",
          "caption": "Social media caption with emoji",
          "hashtags": ["#tag1", "#tag2"],
          "suggested_audio": "Song or sound name, or null",
          "duration_seconds": 12
        }}
      ]
    }}
  ]
}}

IMPORTANT RULES:
- Every sora_prompt MUST start with "@isaiahdupree"
- Every sora_prompt MUST include: wardrobe (casual hoodie, gold chain), camera movement, lighting, mood
- Every sora_prompt MUST end with "Portrait 9:16, cinematic 4K."
- Captions should be engaging, use emoji, feel authentic (not corporate)
- For series: each part should work standalone but tell a story together
- Mix formats: some singles, some series (if include_series is true)
- Stay on brand: tech, automation, content creation, humor, authenticity"""
                    },
                    {
                        "role": "user",
                        "content": f"Here are the current trends:\n\n{trends_json}\n\nGenerate {count} Sora script packages."
                    }
                ],
                temperature=0.85,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            raw_scripts = result.get("scripts", [])

            for raw in raw_scripts:
                pkg = ScriptPackage(
                    title=raw.get("title", "Untitled Script"),
                    trend_name=raw.get("trend_name", ""),
                    trend_source=raw.get("trend_source", ""),
                    format_type=raw.get("format_type", "single"),
                    character="@isaiahdupree",
                    month=month,
                    parts=raw.get("parts", []),
                    platforms=raw.get("platforms", ["tiktok", "instagram", "youtube_shorts"]),
                    source_trends_raw=trends_json[:2000],
                )
                self._save_script(pkg)
                scripts.append(pkg)

            logger.info(f"🎬 Generated {len(scripts)} script packages from {len(trends)} trends")

        except Exception as e:
            logger.error(f"Script generation failed: {e}")

        return scripts

    # ─────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────

    def _save_script(self, pkg: ScriptPackage):
        """Persist a script package to the database."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO sora_generated_scripts
                        (id, title, trend_name, trend_source, format_type,
                         character, month, parts, platforms, status,
                         source_trends_raw, generated_at)
                    VALUES
                        (:id, :title, :trend_name, :trend_source, :format_type,
                         :character, :month, :parts, :platforms, :status,
                         :source_trends_raw, :generated_at)
                    ON CONFLICT (id) DO UPDATE SET
                        parts = EXCLUDED.parts,
                        status = EXCLUDED.status,
                        updated_at = NOW()
                """), {
                    "id": pkg.id,
                    "title": pkg.title,
                    "trend_name": pkg.trend_name,
                    "trend_source": pkg.trend_source,
                    "format_type": pkg.format_type,
                    "character": pkg.character,
                    "month": pkg.month,
                    "parts": json.dumps(pkg.parts),
                    "platforms": json.dumps(pkg.platforms),
                    "status": pkg.status,
                    "source_trends_raw": pkg.source_trends_raw,
                    "generated_at": pkg.generated_at,
                })
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save script {pkg.id}: {e}")

    def get_scripts(
        self,
        month: Optional[str] = None,
        status: Optional[str] = None,
        format_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[ScriptPackage]:
        """Retrieve saved scripts with optional filters."""
        try:
            query = "SELECT * FROM sora_generated_scripts WHERE 1=1"
            params: Dict[str, Any] = {"limit": limit}

            if month:
                query += " AND month = :month"
                params["month"] = month
            if status:
                query += " AND status = :status"
                params["status"] = status
            if format_type:
                query += " AND format_type = :format_type"
                params["format_type"] = format_type

            query += " ORDER BY generated_at DESC LIMIT :limit"

            with self.engine.connect() as conn:
                rows = conn.execute(text(query), params).fetchall()
                return [self._row_to_package(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to get scripts: {e}")
            return []

    def get_script_by_id(self, script_id: str) -> Optional[ScriptPackage]:
        """Get a single script by ID."""
        try:
            with self.engine.connect() as conn:
                row = conn.execute(text(
                    "SELECT * FROM sora_generated_scripts WHERE id = :id"
                ), {"id": script_id}).fetchone()
                return self._row_to_package(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get script {script_id}: {e}")
            return None

    def update_script_status(self, script_id: str, status: str) -> bool:
        """Update a script's status (generated → approved → queued → used)."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    UPDATE sora_generated_scripts
                    SET status = :status, updated_at = NOW()
                    WHERE id = :id
                    RETURNING id
                """), {"id": script_id, "status": status})
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update script status: {e}")
            return False

    def delete_script(self, script_id: str) -> bool:
        """Delete a script."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "DELETE FROM sora_generated_scripts WHERE id = :id RETURNING id"
                ), {"id": script_id})
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete script: {e}")
            return False

    def _row_to_package(self, row) -> ScriptPackage:
        """Convert a DB row to a ScriptPackage."""
        parts = row[7] if isinstance(row[7], list) else json.loads(row[7] or "[]")
        platforms = row[8] if isinstance(row[8], list) else json.loads(row[8] or "[]")
        return ScriptPackage(
            id=row[0],
            title=row[1],
            trend_name=row[2] or "",
            trend_source=row[3] or "",
            format_type=row[4] or "single",
            character=row[5] or "@isaiahdupree",
            month=row[6] or "",
            parts=parts,
            platforms=platforms,
            status=row[9] or "generated",
            source_trends_raw=row[10] or "",
            generated_at=row[11] if row[11] else datetime.now(timezone.utc),
        )

    # ─────────────────────────────────────────────────────────────
    # FALLBACK TRENDS
    # ─────────────────────────────────────────────────────────────

    def _get_fallback_trends(self) -> List[Dict[str, Any]]:
        """Fallback trends when web fetching fails."""
        return [
            {
                "trend_name": "Day in the Life",
                "description": "Creators film aesthetic day-in-the-life montages with cinematic transitions",
                "platform": "tiktok",
                "format": "single",
                "source": "fallback",
            },
            {
                "trend_name": "AI-Generated Content Showcase",
                "description": "Creators showcase AI tools and what they can build, often with before/after reveals",
                "platform": "multi",
                "format": "series",
                "source": "fallback",
            },
            {
                "trend_name": "Motivational Monologue",
                "description": "Cinematic shots with motivational voiceover about building and creating",
                "platform": "instagram",
                "format": "single",
                "source": "fallback",
            },
            {
                "trend_name": "Tech Setup Tour",
                "description": "Aesthetic workspace tours showing desk setup, monitors, and tech gadgets",
                "platform": "youtube_shorts",
                "format": "single",
                "source": "fallback",
            },
            {
                "trend_name": "Relatable Creator Struggles",
                "description": "Humorous takes on common creator and developer problems with comedic timing",
                "platform": "tiktok",
                "format": "single",
                "source": "fallback",
            },
        ]


# =============================================================================
# SINGLETON
# =============================================================================

_generator_instance: Optional[SoraScriptGenerator] = None


def get_script_generator() -> SoraScriptGenerator:
    """Get singleton instance."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = SoraScriptGenerator()
    return _generator_instance
