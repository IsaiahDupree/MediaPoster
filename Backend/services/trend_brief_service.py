"""
Trend Brief Generation Service
AI-powered trend summaries with content ideas.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import openai


class TrendBrief(BaseModel):
    """AI-generated trend brief"""
    trend_type: str
    trend_id: str
    trend_name: str
    summary: str
    why_trending: str
    content_ideas: List[str]
    example_hooks: List[str]
    target_audience: str
    best_posting_time: str
    generated_at: datetime = None
    expires_at: datetime = None


class TrendBriefService:
    """
    Service for generating AI-powered trend briefs.
    
    Each brief includes:
    - Summary of what the trend is
    - Why it's trending now
    - Content ideas to capitalize on it
    - Example hooks to use
    - Target audience
    - Best times to post
    """
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres"
        )
        self.engine = create_engine(self.database_url)
        
        if self.api_key:
            openai.api_key = self.api_key
    
    async def generate_brief(
        self,
        trend_type: str,
        trend_id: str,
        trend_name: str,
        velocity_data: Dict[str, Any] = None
    ) -> Optional[TrendBrief]:
        """Generate an AI brief for a trend"""
        if not self.api_key:
            logger.error("OPENAI_API_KEY not configured")
            return None
        
        # Check cache first
        cached = self._get_cached_brief(trend_type, trend_id)
        if cached:
            return cached
        
        try:
            velocity_info = ""
            if velocity_data:
                velocity_info = f"""
VELOCITY DATA:
- Current usage: {velocity_data.get('current_count', 'N/A')}
- 24h growth: {velocity_data.get('velocity_1d', 0):.1f}%
- 7d growth: {velocity_data.get('velocity_7d', 0):.1f}%
- Acceleration: {velocity_data.get('acceleration', 0):.1f}%
"""

            prompt = f"""Generate a trend brief for this Instagram trend:

TREND TYPE: {trend_type}
TREND NAME: {trend_name}
{velocity_info}

Create a comprehensive brief with:
1. summary: 2-3 sentences explaining what this trend is about
2. why_trending: Why is this gaining traction right now? (cultural moment, season, event, etc.)
3. content_ideas: 5 specific video/post ideas to capitalize on this trend
4. example_hooks: 3 opening hooks to use with this trend
5. target_audience: Who should create content using this trend
6. best_posting_time: When to post for maximum reach

Return ONLY valid JSON with these exact keys."""

            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert social media trend analyst. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean JSON
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            
            brief = TrendBrief(
                trend_type=trend_type,
                trend_id=trend_id,
                trend_name=trend_name,
                summary=result.get("summary", ""),
                why_trending=result.get("why_trending", ""),
                content_ideas=result.get("content_ideas", []),
                example_hooks=result.get("example_hooks", []),
                target_audience=result.get("target_audience", ""),
                best_posting_time=result.get("best_posting_time", ""),
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
            # Cache the brief
            self._save_brief(brief)
            
            return brief
            
        except Exception as e:
            logger.error(f"Error generating trend brief: {e}")
            return None
    
    def _get_cached_brief(self, trend_type: str, trend_id: str) -> Optional[TrendBrief]:
        """Get cached brief if not expired"""
        with self.engine.connect() as conn:
            row = conn.execute(text("""
                SELECT trend_type, trend_id, trend_name, summary, why_trending,
                       content_ideas, example_posts, target_audience, best_posting_time,
                       generated_at, expires_at
                FROM trend_briefs
                WHERE trend_type = :type AND trend_id = :id
                AND expires_at > NOW()
            """), {"type": trend_type, "id": trend_id}).fetchone()
            
            if row:
                return TrendBrief(
                    trend_type=row[0],
                    trend_id=row[1],
                    trend_name=row[2],
                    summary=row[3],
                    why_trending=row[4],
                    content_ideas=row[5] or [],
                    example_hooks=row[6] or [],
                    target_audience=row[7],
                    best_posting_time=row[8],
                    generated_at=row[9],
                    expires_at=row[10]
                )
            return None
    
    def _save_brief(self, brief: TrendBrief):
        """Save brief to database"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO trend_briefs 
                (trend_type, trend_id, trend_name, summary, why_trending,
                 content_ideas, example_posts, target_audience, best_posting_time,
                 generated_at, expires_at)
                VALUES (:type, :id, :name, :summary, :why, :ideas, :hooks,
                        :audience, :time, :gen_at, :exp_at)
                ON CONFLICT (trend_type, trend_id) DO UPDATE
                SET summary = :summary, why_trending = :why, content_ideas = :ideas,
                    example_posts = :hooks, target_audience = :audience,
                    best_posting_time = :time, generated_at = :gen_at, expires_at = :exp_at
            """), {
                "type": brief.trend_type,
                "id": brief.trend_id,
                "name": brief.trend_name,
                "summary": brief.summary,
                "why": brief.why_trending,
                "ideas": json.dumps(brief.content_ideas),
                "hooks": json.dumps(brief.example_hooks),
                "audience": brief.target_audience,
                "time": brief.best_posting_time,
                "gen_at": brief.generated_at,
                "exp_at": brief.expires_at
            })
            conn.commit()
    
    def get_all_briefs(self, trend_type: str = None, limit: int = 20) -> List[TrendBrief]:
        """Get all cached briefs"""
        with self.engine.connect() as conn:
            query = """
                SELECT trend_type, trend_id, trend_name, summary, why_trending,
                       content_ideas, example_posts, target_audience, best_posting_time,
                       generated_at, expires_at
                FROM trend_briefs
                WHERE expires_at > NOW()
            """
            if trend_type:
                query += f" AND trend_type = '{trend_type}'"
            query += f" ORDER BY generated_at DESC LIMIT {limit}"
            
            rows = conn.execute(text(query)).fetchall()
            
            return [
                TrendBrief(
                    trend_type=r[0], trend_id=r[1], trend_name=r[2],
                    summary=r[3], why_trending=r[4],
                    content_ideas=r[5] or [], example_hooks=r[6] or [],
                    target_audience=r[7], best_posting_time=r[8],
                    generated_at=r[9], expires_at=r[10]
                )
                for r in rows
            ]


# Singleton
_brief_service: Optional[TrendBriefService] = None


def get_trend_brief_service() -> TrendBriefService:
    """Get singleton brief service"""
    global _brief_service
    if _brief_service is None:
        _brief_service = TrendBriefService()
    return _brief_service
