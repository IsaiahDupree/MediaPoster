"""
Content Gap Analysis Service
Identifies content themes competitors cover that the user doesn't,
and provides opportunity scores and recommended content ideas.
"""
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from pydantic import BaseModel
import openai

from services.competitor_service import COMPETITOR_RESEARCH_DIR


class GapTheme(BaseModel):
    """A content gap - theme competitors cover but user doesn't"""
    theme: str
    competitor_avg_views: int = 0
    competitor_post_count: int = 0
    opportunity_score: float = 0.0
    suggested_content: str = ""
    competitors_using: List[str] = []


class OverlapTheme(BaseModel):
    """A theme both user and competitors cover"""
    theme: str
    user_avg_views: int = 0
    competitor_avg_views: int = 0
    delta_pct: float = 0.0  # positive = user outperforms


class GapAnalysisResult(BaseModel):
    """Complete content gap analysis result"""
    competitor_usernames: List[str]
    gap_themes: List[GapTheme]
    overlap_themes: List[OverlapTheme]
    unique_themes: List[str]  # themes only user covers
    gap_coverage_score: float  # 0-100
    ai_analysis: str = ""
    analyzed_at: str = ""


class ContentGapService:
    """
    Analyzes content gaps between user and competitors.
    Uses AI to identify themes, compare coverage, and recommend actions.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"
        self.storage_path = COMPETITOR_RESEARCH_DIR / "learnings"
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def analyze_gaps(
        self,
        user_themes: Optional[List[str]] = None,
        user_captions: Optional[List[str]] = None,
        competitor_usernames: Optional[List[str]] = None,
    ) -> GapAnalysisResult:
        """
        Run a full content gap analysis.
        
        Args:
            user_themes: Explicit list of themes the user covers
            user_captions: User's own captions to extract themes from
            competitor_usernames: Specific competitors (default: all tracked)
        """
        # Gather competitor data
        competitor_data = self._gather_competitor_themes(competitor_usernames)

        if not competitor_data:
            logger.warning("No competitor data available for gap analysis")
            return GapAnalysisResult(
                competitor_usernames=[],
                gap_themes=[],
                overlap_themes=[],
                unique_themes=[],
                gap_coverage_score=0,
                analyzed_at=datetime.now().isoformat(),
            )

        # Get user themes from captions or explicit list
        user_theme_set = set(user_themes or [])

        # Use AI to analyze gaps
        result = await self._ai_gap_analysis(
            user_themes=list(user_theme_set),
            user_captions=user_captions or [],
            competitor_data=competitor_data,
        )

        # Save results
        self._save_results(result)

        return result

    def _gather_competitor_themes(
        self, usernames: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Gather theme data from all competitor analysis files"""
        accounts_dir = COMPETITOR_RESEARCH_DIR / "accounts"
        if not accounts_dir.exists():
            return {}

        competitor_data = {}

        for account_dir in accounts_dir.iterdir():
            if not account_dir.is_dir() or account_dir.name.startswith("."):
                continue

            username = account_dir.name
            if usernames and username not in usernames:
                continue

            # Load analysis
            analysis_file = account_dir / "analysis" / "learnings.json"
            if not analysis_file.exists():
                continue

            try:
                with open(analysis_file) as f:
                    data = json.load(f)

                competitor_data[username] = {
                    "themes": data.get("content_themes", []),
                    "top_hooks": data.get("top_hooks", []),
                    "top_formats": data.get("top_formats", []),
                    "avg_engagement": data.get("avg_engagement_rate", 0),
                    "total_content": data.get("total_content_analyzed", 0),
                    "key_learnings": data.get("key_learnings", []),
                    "content_ideas": data.get("content_ideas", []),
                }
            except Exception as e:
                logger.error(f"Error loading analysis for @{username}: {e}")

        return competitor_data

    async def _ai_gap_analysis(
        self,
        user_themes: List[str],
        user_captions: List[str],
        competitor_data: Dict[str, Dict[str, Any]],
    ) -> GapAnalysisResult:
        """Use AI to perform deep gap analysis"""
        if not self.api_key:
            logger.error("OPENAI_API_KEY not set - running basic gap analysis")
            return self._basic_gap_analysis(user_themes, competitor_data)

        # Build competitor summary for the prompt
        comp_summaries = []
        all_competitor_themes = set()
        for username, data in competitor_data.items():
            themes = data.get("themes", [])
            all_competitor_themes.update(themes)
            comp_summaries.append({
                "username": username,
                "themes": themes,
                "avg_engagement": data.get("avg_engagement", 0),
                "content_count": data.get("total_content", 0),
                "top_hooks": [h.get("type") for h in data.get("top_hooks", [])[:3]],
            })

        try:
            client = openai.OpenAI(api_key=self.api_key)

            prompt = f"""Analyze content gaps between a creator and their competitors.

USER'S THEMES: {json.dumps(user_themes) if user_themes else "Unknown - infer from captions below"}

USER'S RECENT CAPTIONS (sample):
{json.dumps(user_captions[:10]) if user_captions else "Not provided"}

COMPETITOR DATA:
{json.dumps(comp_summaries, indent=2)}

Analyze and return JSON with:
{{
    "gap_themes": [
        {{
            "theme": "theme name",
            "competitor_avg_views": 0,
            "competitor_post_count": 0,
            "opportunity_score": 0-100,
            "suggested_content": "specific content idea to fill this gap",
            "competitors_using": ["username1", "username2"]
        }}
    ],
    "overlap_themes": [
        {{
            "theme": "theme both cover",
            "delta_pct": 0
        }}
    ],
    "unique_themes": ["themes only the user covers"],
    "gap_coverage_score": 0-100,
    "ai_analysis": "2-3 sentence strategic summary of the biggest opportunities"
}}

Focus on ACTIONABLE gaps. Rank by opportunity_score (combination of competitor engagement + gap size).
Return ONLY valid JSON."""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert content strategist specializing in Instagram competitive analysis. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            result = json.loads(result_text)

            return GapAnalysisResult(
                competitor_usernames=list(competitor_data.keys()),
                gap_themes=[GapTheme(**g) for g in result.get("gap_themes", [])],
                overlap_themes=[OverlapTheme(**o) for o in result.get("overlap_themes", [])],
                unique_themes=result.get("unique_themes", []),
                gap_coverage_score=result.get("gap_coverage_score", 0),
                ai_analysis=result.get("ai_analysis", ""),
                analyzed_at=datetime.now().isoformat(),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI gap analysis response: {e}")
            return self._basic_gap_analysis(user_themes, competitor_data)
        except Exception as e:
            logger.error(f"Error in AI gap analysis: {e}")
            return self._basic_gap_analysis(user_themes, competitor_data)

    def _basic_gap_analysis(
        self,
        user_themes: List[str],
        competitor_data: Dict[str, Dict[str, Any]],
    ) -> GapAnalysisResult:
        """Fallback: basic set-difference gap analysis without AI"""
        user_set = set(t.lower() for t in user_themes)

        # Collect all competitor themes
        theme_accounts: Dict[str, List[str]] = {}
        for username, data in competitor_data.items():
            for theme in data.get("themes", []):
                tl = theme.lower()
                if tl not in theme_accounts:
                    theme_accounts[tl] = []
                theme_accounts[tl].append(username)

        # Gaps: competitor themes not in user themes
        gaps = []
        for theme, accounts in theme_accounts.items():
            if theme not in user_set:
                gaps.append(GapTheme(
                    theme=theme,
                    competitor_post_count=len(accounts),
                    opportunity_score=len(accounts) * 25,
                    competitors_using=accounts,
                    suggested_content=f"Create content about '{theme}'",
                ))

        gaps.sort(key=lambda g: g.opportunity_score, reverse=True)

        # Overlaps
        overlaps = [
            OverlapTheme(theme=t)
            for t in user_set
            if t in theme_accounts
        ]

        # Unique to user
        unique = [t for t in user_set if t not in theme_accounts]

        # Coverage score
        total_competitor_themes = len(theme_accounts)
        covered = len(overlaps)
        coverage = (covered / max(1, total_competitor_themes)) * 100

        return GapAnalysisResult(
            competitor_usernames=list(competitor_data.keys()),
            gap_themes=gaps[:20],
            overlap_themes=overlaps,
            unique_themes=unique,
            gap_coverage_score=round(coverage, 1),
            ai_analysis="Basic gap analysis (AI unavailable). Review gap themes ranked by competitor coverage.",
            analyzed_at=datetime.now().isoformat(),
        )

    def _save_results(self, result: GapAnalysisResult):
        """Save gap analysis results to local storage"""
        try:
            output_path = self.storage_path / "content_gap_analysis.json"
            with open(output_path, "w") as f:
                json.dump(result.model_dump(), f, indent=2, default=str)
            logger.info(f"Saved gap analysis to {output_path}")
        except Exception as e:
            logger.error(f"Error saving gap analysis: {e}")

    def get_latest_analysis(self) -> Optional[GapAnalysisResult]:
        """Load the most recent gap analysis from storage"""
        output_path = self.storage_path / "content_gap_analysis.json"
        if not output_path.exists():
            return None
        try:
            with open(output_path) as f:
                data = json.load(f)
            return GapAnalysisResult(**data)
        except Exception as e:
            logger.error(f"Error loading gap analysis: {e}")
            return None


# Singleton
_gap_service: Optional[ContentGapService] = None


def get_content_gap_service() -> ContentGapService:
    """Get singleton content gap service"""
    global _gap_service
    if _gap_service is None:
        _gap_service = ContentGapService()
    return _gap_service
