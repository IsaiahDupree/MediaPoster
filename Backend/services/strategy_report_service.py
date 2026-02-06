"""
Weekly Strategy Report Service
Auto-generates actionable weekly content strategy reports by combining:
- User's own performance data
- Competitor analysis learnings
- Trending hashtags/sounds/formats
- AI-powered content recommendations
"""
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from loguru import logger
from pydantic import BaseModel
import openai

from services.competitor_service import COMPETITOR_RESEARCH_DIR

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


class StrategyReport(BaseModel):
    """Weekly strategy report"""
    week_start: str
    week_end: str
    performance_summary: Dict[str, Any] = {}
    top_content: List[Dict[str, Any]] = []
    trending_recommendations: Dict[str, Any] = {}
    content_ideas: List[Dict[str, Any]] = []
    action_items: List[Dict[str, Any]] = []
    report_markdown: str = ""
    competitors_analyzed: List[str] = []
    generated_at: str = ""


class StrategyReportService:
    """
    Generates weekly content strategy reports.
    Combines competitor learnings, trends, and AI recommendations.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"
        self.storage_path = COMPETITOR_RESEARCH_DIR / "learnings" / "strategy_reports"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._supabase = None

    def _get_supabase(self):
        if self._supabase is None and HAS_SUPABASE:
            try:
                url = os.environ.get('SUPABASE_URL', 'http://127.0.0.1:54321')
                key = os.environ.get('SUPABASE_ANON_KEY', os.environ.get('SUPABASE_KEY', ''))
                if key:
                    self._supabase = create_client(url, key)
            except Exception as e:
                logger.warning(f"Supabase not available for strategy reports: {e}")
        return self._supabase

    async def generate_report(
        self,
        user_performance: Optional[Dict[str, Any]] = None,
        trending_data: Optional[Dict[str, Any]] = None,
    ) -> StrategyReport:
        """
        Generate a weekly strategy report.

        Args:
            user_performance: User's own metrics for the week
            trending_data: Current trending hashtags/sounds/formats
        """
        # Calculate week boundaries
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Gather competitor insights
        competitor_insights = self._gather_competitor_insights()

        # Gather trending hashtags from local data
        trending = trending_data or self._load_trending_data()

        # Generate the report with AI
        report = await self._generate_with_ai(
            week_start=week_start,
            week_end=week_end,
            user_performance=user_performance or {},
            competitor_insights=competitor_insights,
            trending=trending,
        )

        # Save report
        self._save_report(report)

        return report

    def _gather_competitor_insights(self) -> Dict[str, Any]:
        """Gather aggregate insights from all competitor analyses"""
        accounts_dir = COMPETITOR_RESEARCH_DIR / "accounts"
        if not accounts_dir.exists():
            return {}

        insights = {
            "accounts": [],
            "all_hooks": [],
            "all_formats": [],
            "all_themes": [],
            "all_ideas": [],
            "all_learnings": [],
        }

        for account_dir in accounts_dir.iterdir():
            if not account_dir.is_dir() or account_dir.name.startswith("."):
                continue

            analysis_file = account_dir / "analysis" / "learnings.json"
            if not analysis_file.exists():
                continue

            try:
                with open(analysis_file) as f:
                    data = json.load(f)

                username = account_dir.name
                insights["accounts"].append(username)

                for hook in data.get("top_hooks", []):
                    insights["all_hooks"].append({
                        "type": hook.get("type"),
                        "count": hook.get("count", 0),
                        "source": username,
                    })

                for fmt in data.get("top_formats", []):
                    insights["all_formats"].append({
                        "type": fmt.get("type"),
                        "count": fmt.get("count", 0),
                        "source": username,
                    })

                insights["all_themes"].extend(data.get("content_themes", []))
                insights["all_ideas"].extend(data.get("content_ideas", []))
                insights["all_learnings"].extend(data.get("key_learnings", []))

            except Exception as e:
                logger.error(f"Error loading insights for {account_dir.name}: {e}")

        return insights

    def _load_trending_data(self) -> Dict[str, Any]:
        """Load trending hashtags from local storage"""
        trending_path = COMPETITOR_RESEARCH_DIR / "learnings" / "trending_hashtags.json"
        if trending_path.exists():
            try:
                with open(trending_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading trending data: {e}")
        return {}

    async def _generate_with_ai(
        self,
        week_start: date,
        week_end: date,
        user_performance: Dict[str, Any],
        competitor_insights: Dict[str, Any],
        trending: Dict[str, Any],
    ) -> StrategyReport:
        """Generate the strategy report using AI"""
        if not self.api_key:
            logger.error("OPENAI_API_KEY not set")
            return self._generate_basic_report(week_start, week_end, competitor_insights, trending)

        try:
            client = openai.OpenAI(api_key=self.api_key)

            # Build context
            top_hashtags = [
                h.get("tag", "") for h in trending.get("hashtags", [])[:10]
            ]

            # Deduplicate themes and learnings
            unique_themes = list(set(competitor_insights.get("all_themes", [])))[:15]
            unique_learnings = list(set(competitor_insights.get("all_learnings", [])))[:10]

            # Aggregate hook types
            hook_types: Dict[str, int] = {}
            for h in competitor_insights.get("all_hooks", []):
                ht = h.get("type", "unknown")
                hook_types[ht] = hook_types.get(ht, 0) + h.get("count", 0)
            top_hook_types = sorted(hook_types.items(), key=lambda x: x[1], reverse=True)[:5]

            prompt = f"""Generate a weekly Instagram content strategy report.

WEEK: {week_start.isoformat()} to {week_end.isoformat()}

USER PERFORMANCE THIS WEEK:
{json.dumps(user_performance, indent=2) if user_performance else "Not available - provide general recommendations"}

COMPETITOR INSIGHTS ({len(competitor_insights.get('accounts', []))} accounts analyzed):
- Top hook types: {json.dumps(top_hook_types)}
- Common themes: {json.dumps(unique_themes[:10])}
- Key learnings: {json.dumps(unique_learnings[:8])}

TRENDING HASHTAGS:
{json.dumps(top_hashtags)}

Return JSON with:
{{
    "performance_summary": {{
        "headline": "one-line summary",
        "key_metrics": {{"posts": 0, "views": 0, "engagement_rate": 0}},
        "vs_last_week": "brief comparison or recommendation"
    }},
    "trending_recommendations": {{
        "hashtags": ["top 5 hashtags to use this week"],
        "formats": ["top 3 content formats trending now"],
        "topics": ["top 3 topics to cover"]
    }},
    "content_ideas": [
        {{
            "title": "specific content idea",
            "hook_type": "question|bold_statement|pain_point|etc",
            "format": "talking_head|broll|text_overlay|etc",
            "hashtags": ["3-5 hashtags"],
            "why_it_works": "brief explanation"
        }}
    ],
    "action_items": [
        {{
            "action": "specific actionable task",
            "priority": "high|medium|low",
            "category": "content|engagement|growth|optimization"
        }}
    ],
    "strategic_summary": "2-3 sentence summary of key strategic recommendations for the week"
}}

Generate 5-7 content ideas and 5-8 action items. Be specific and actionable.
Return ONLY valid JSON."""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Instagram growth strategist. Generate actionable, data-driven weekly strategy reports. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            result = json.loads(result_text)

            # Build markdown report
            markdown = self._build_markdown(
                week_start, week_end, result, competitor_insights
            )

            return StrategyReport(
                week_start=week_start.isoformat(),
                week_end=week_end.isoformat(),
                performance_summary=result.get("performance_summary", {}),
                top_content=result.get("top_content", []),
                trending_recommendations=result.get("trending_recommendations", {}),
                content_ideas=result.get("content_ideas", []),
                action_items=result.get("action_items", []),
                report_markdown=markdown,
                competitors_analyzed=competitor_insights.get("accounts", []),
                generated_at=datetime.now().isoformat(),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI strategy report: {e}")
            return self._generate_basic_report(week_start, week_end, competitor_insights, trending)
        except Exception as e:
            logger.error(f"Error generating strategy report: {e}")
            return self._generate_basic_report(week_start, week_end, competitor_insights, trending)

    def _generate_basic_report(
        self,
        week_start: date,
        week_end: date,
        competitor_insights: Dict[str, Any],
        trending: Dict[str, Any],
    ) -> StrategyReport:
        """Fallback: generate a basic report without AI"""
        top_hashtags = [h.get("tag", "") for h in trending.get("hashtags", [])[:5]]
        unique_themes = list(set(competitor_insights.get("all_themes", [])))[:5]

        return StrategyReport(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            performance_summary={"headline": "Review your analytics manually"},
            trending_recommendations={
                "hashtags": top_hashtags,
                "topics": unique_themes,
            },
            content_ideas=[
                {"title": idea, "hook_type": "general"}
                for idea in competitor_insights.get("all_ideas", [])[:5]
            ],
            action_items=[
                {"action": "Review competitor content", "priority": "high", "category": "content"},
                {"action": "Post at least 5 times this week", "priority": "high", "category": "content"},
                {"action": "Use trending hashtags in next post", "priority": "medium", "category": "optimization"},
            ],
            report_markdown="# Weekly Strategy Report\n\nAI generation unavailable. Review competitor data manually.",
            competitors_analyzed=competitor_insights.get("accounts", []),
            generated_at=datetime.now().isoformat(),
        )

    def _build_markdown(
        self,
        week_start: date,
        week_end: date,
        result: Dict[str, Any],
        competitor_insights: Dict[str, Any],
    ) -> str:
        """Build a markdown version of the strategy report"""
        perf = result.get("performance_summary", {})
        trending = result.get("trending_recommendations", {})
        ideas = result.get("content_ideas", [])
        actions = result.get("action_items", [])

        md = f"""# Weekly Instagram Strategy Report
**Week of {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}**
**Generated:** {datetime.now().strftime('%A %I:%M %p')}
**Competitors Analyzed:** {len(competitor_insights.get('accounts', []))}

---

## Summary

{perf.get('headline', 'No performance data available')}

{perf.get('vs_last_week', '')}

---

## Trending This Week

**Hashtags to use:**
"""
        for tag in trending.get("hashtags", []):
            md += f"- {tag}\n"

        md += "\n**Content formats trending:**\n"
        for fmt in trending.get("formats", []):
            md += f"- {fmt}\n"

        md += "\n**Topics to cover:**\n"
        for topic in trending.get("topics", []):
            md += f"- {topic}\n"

        md += "\n---\n\n## Content Ideas\n\n"
        for i, idea in enumerate(ideas, 1):
            md += f"""### {i}. {idea.get('title', 'Untitled')}
- **Hook type:** {idea.get('hook_type', 'N/A')}
- **Format:** {idea.get('format', 'N/A')}
- **Hashtags:** {', '.join(idea.get('hashtags', []))}
- **Why it works:** {idea.get('why_it_works', '')}

"""

        md += "---\n\n## Action Items\n\n"
        for action in actions:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                action.get("priority", "medium"), "⚪"
            )
            md += f"- [ ] {priority_emoji} **[{action.get('category', 'general')}]** {action.get('action', '')}\n"

        strategic = result.get("strategic_summary", "")
        if strategic:
            md += f"\n---\n\n## Strategic Summary\n\n{strategic}\n"

        md += f"\n---\n\n*Next report: {(week_end + timedelta(days=1)).strftime('%A, %B %d, %Y')}*\n"

        return md

    def _save_report(self, report: StrategyReport):
        """Save report to local storage"""
        try:
            # Save JSON
            json_path = self.storage_path / f"report_{report.week_start}.json"
            with open(json_path, "w") as f:
                json.dump(report.model_dump(), f, indent=2, default=str)

            # Save markdown
            md_path = self.storage_path / f"report_{report.week_start}.md"
            with open(md_path, "w") as f:
                f.write(report.report_markdown)

            # Also save as "latest"
            latest_json = self.storage_path / "latest_report.json"
            with open(latest_json, "w") as f:
                json.dump(report.model_dump(), f, indent=2, default=str)

            latest_md = self.storage_path / "latest_report.md"
            with open(latest_md, "w") as f:
                f.write(report.report_markdown)

            logger.info(f"Saved strategy report for week of {report.week_start}")

            # Persist to Supabase
            self._persist_to_supabase(report)

        except Exception as e:
            logger.error(f"Error saving strategy report: {e}")

    def _persist_to_supabase(self, report: StrategyReport):
        """Persist report to Supabase strategy_reports table."""
        sb = self._get_supabase()
        if not sb:
            return
        try:
            sb.table('strategy_reports').upsert({
                'week_start': report.week_start,
                'week_end': report.week_end,
                'performance_summary': json.dumps(report.performance_summary, default=str),
                'top_content': json.dumps(report.top_content, default=str),
                'trending_recommendations': json.dumps(report.trending_recommendations, default=str),
                'content_ideas': json.dumps(report.content_ideas, default=str),
                'action_items': json.dumps(report.action_items, default=str),
                'report_markdown': report.report_markdown,
                'competitors_analyzed': report.competitors_analyzed,
                'model_used': 'gpt-4o-mini',
            }, on_conflict='week_start').execute()
            logger.info(f"Persisted strategy report to Supabase")
        except Exception as e:
            logger.warning(f"Failed to persist strategy report to Supabase: {e}")

    def get_latest_report(self) -> Optional[StrategyReport]:
        """Load the most recent strategy report"""
        latest_path = self.storage_path / "latest_report.json"
        if not latest_path.exists():
            return None
        try:
            with open(latest_path) as f:
                data = json.load(f)
            return StrategyReport(**data)
        except Exception as e:
            logger.error(f"Error loading latest report: {e}")
            return None

    def get_report_for_week(self, week_start: str) -> Optional[StrategyReport]:
        """Load a report for a specific week"""
        report_path = self.storage_path / f"report_{week_start}.json"
        if not report_path.exists():
            return None
        try:
            with open(report_path) as f:
                data = json.load(f)
            return StrategyReport(**data)
        except Exception as e:
            logger.error(f"Error loading report for {week_start}: {e}")
            return None

    def list_reports(self) -> List[Dict[str, str]]:
        """List all generated reports"""
        reports = []
        for f in sorted(self.storage_path.glob("report_*.json"), reverse=True):
            if f.name == "latest_report.json":
                continue
            week_start = f.stem.replace("report_", "")
            reports.append({
                "week_start": week_start,
                "file": str(f),
            })
        return reports


# Singleton
_report_service: Optional[StrategyReportService] = None


def get_strategy_report_service() -> StrategyReportService:
    """Get singleton strategy report service"""
    global _report_service
    if _report_service is None:
        _report_service = StrategyReportService()
    return _report_service
