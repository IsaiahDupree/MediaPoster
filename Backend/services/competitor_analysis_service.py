"""
Competitor Content Analysis Service
AI-powered analysis of competitor content to extract learnings and patterns.
"""
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from pydantic import BaseModel
import openai

from services.competitor_service import (
    get_competitor_service, 
    CompetitorContent,
    COMPETITOR_RESEARCH_DIR
)
from services.keyword_extraction_service import get_keyword_service

# Optional Supabase persistence
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


class ContentAnalysis(BaseModel):
    """AI-generated analysis of a piece of content"""
    content_id: str
    hook: Optional[str] = None
    hook_type: Optional[str] = None  # question, statement, controversial, etc.
    format_type: Optional[str] = None  # talking_head, broll, text_overlay, etc.
    content_themes: List[str] = []
    target_audience: Optional[str] = None
    emotional_triggers: List[str] = []
    cta_type: Optional[str] = None
    estimated_production_effort: Optional[str] = None  # low, medium, high
    why_it_works: Optional[str] = None
    replication_tips: List[str] = []


class AccountLearnings(BaseModel):
    """Aggregated learnings from a competitor account"""
    username: str
    total_content_analyzed: int
    avg_engagement_rate: float
    top_hooks: List[Dict[str, Any]]
    top_formats: List[Dict[str, Any]]
    content_themes: List[str]
    posting_patterns: Dict[str, Any]
    key_learnings: List[str]
    content_ideas: List[str]
    generated_at: str


class CompetitorAnalysisService:
    """
    Service for AI-powered analysis of competitor content.
    Uses OpenAI to extract patterns, hooks, and learnings.
    """
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"  # Fast and cost-effective
        self.competitor_service = get_competitor_service()
        self.keyword_service = get_keyword_service()
        self._supabase: Optional[Client] = None
        
        if self.api_key:
            openai.api_key = self.api_key
        else:
            logger.warning("OPENAI_API_KEY not set - analysis will fail")
    
    def _get_supabase(self) -> Optional[Client]:
        """Get or create Supabase client for persistence."""
        if self._supabase is None and HAS_SUPABASE:
            try:
                url = os.environ.get('SUPABASE_URL', 'http://127.0.0.1:54321')
                key = os.environ.get('SUPABASE_ANON_KEY', os.environ.get('SUPABASE_KEY', ''))
                if key:
                    self._supabase = create_client(url, key)
            except Exception as e:
                logger.warning(f"Supabase not available for analysis persistence: {e}")
        return self._supabase
    
    async def analyze_content(self, content: CompetitorContent) -> Optional[ContentAnalysis]:
        """
        Analyze a single piece of content using AI.
        
        Extracts:
        - Hook and hook type
        - Content format
        - Themes and audience
        - Why it works
        - Replication tips
        """
        if not self.api_key:
            logger.error("Cannot analyze: OPENAI_API_KEY not configured")
            return None
        
        if not content.caption:
            return ContentAnalysis(content_id=content.media_id)
        
        try:
            prompt = f"""Analyze this Instagram content and extract insights:

CAPTION:
{content.caption[:1000]}

METRICS:
- Play count: {content.play_count or 'N/A'}
- Like count: {content.like_count or 'N/A'}
- Comment count: {content.comment_count or 'N/A'}

Analyze and return JSON with:
1. hook: The opening hook/first line that grabs attention
2. hook_type: Type of hook (question, bold_statement, controversy, curiosity, pain_point, transformation)
3. format_type: Content format (talking_head, broll_overlay, text_cards, tutorial, story, listicle)
4. content_themes: List of 2-3 main themes/topics
5. target_audience: Who this content is for
6. emotional_triggers: List of emotions it evokes (curiosity, fomo, inspiration, etc)
7. cta_type: Call-to-action type (follow, save, comment, share, link, none)
8. why_it_works: 1-2 sentences on why this content performs well
9. replication_tips: 2-3 actionable tips to create similar content

Return ONLY valid JSON, no markdown."""

            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert social media content analyst. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            
            return ContentAnalysis(
                content_id=content.media_id,
                hook=result.get("hook"),
                hook_type=result.get("hook_type"),
                format_type=result.get("format_type"),
                content_themes=result.get("content_themes", []),
                target_audience=result.get("target_audience"),
                emotional_triggers=result.get("emotional_triggers", []),
                cta_type=result.get("cta_type"),
                why_it_works=result.get("why_it_works"),
                replication_tips=result.get("replication_tips", [])
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            return None
    
    async def analyze_account(
        self, 
        username: str, 
        max_content: int = 20
    ) -> Optional[AccountLearnings]:
        """
        Analyze all content from a competitor account and generate learnings.
        """
        logger.info(f"Starting analysis for @{username}")
        
        # Fetch content
        reels = await self.competitor_service.fetch_user_reels(username, count=max_content)
        posts = await self.competitor_service.fetch_user_posts(username, count=max_content)
        
        all_content = reels + posts
        if not all_content:
            logger.warning(f"No content found for @{username}")
            return None
        
        # Analyze individual content pieces (limit to top performers)
        sorted_content = sorted(
            all_content,
            key=lambda x: (x.play_count or 0) + (x.like_count or 0) * 10,
            reverse=True
        )[:10]  # Top 10 by engagement
        
        analyses = []
        for content in sorted_content:
            analysis = await self.analyze_content(content)
            if analysis:
                analyses.append(analysis)
        
        logger.info(f"Analyzed {len(analyses)} content pieces for @{username}")
        
        # Extract keywords from all captions
        caption_data = [
            {
                "caption": c.caption or "",
                "play_count": c.play_count or 0,
                "like_count": c.like_count or 0
            }
            for c in all_content
        ]
        keywords = self.keyword_service.get_trending_keywords(caption_data)
        
        # Aggregate learnings
        learnings = await self._generate_learnings(username, all_content, analyses, keywords)
        
        # Save to file
        await self._save_learnings(username, learnings)
        
        return learnings
    
    async def _generate_learnings(
        self,
        username: str,
        content: List[CompetitorContent],
        analyses: List[ContentAnalysis],
        keywords: Dict[str, Any]
    ) -> AccountLearnings:
        """Generate aggregated learnings from individual analyses"""
        
        # Calculate metrics
        total_plays = sum(c.play_count or 0 for c in content)
        total_likes = sum(c.like_count or 0 for c in content)
        avg_engagement = (total_likes / len(content)) if content else 0
        
        # Aggregate hooks
        hook_counts: Dict[str, int] = {}
        format_counts: Dict[str, int] = {}
        all_themes: List[str] = []
        all_tips: List[str] = []
        
        for a in analyses:
            if a.hook_type:
                hook_counts[a.hook_type] = hook_counts.get(a.hook_type, 0) + 1
            if a.format_type:
                format_counts[a.format_type] = format_counts.get(a.format_type, 0) + 1
            all_themes.extend(a.content_themes)
            all_tips.extend(a.replication_tips)
        
        # Top hooks
        top_hooks = [
            {"type": k, "count": v, "percentage": round(v/len(analyses)*100, 1)}
            for k, v in sorted(hook_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # Top formats
        top_formats = [
            {"type": k, "count": v, "percentage": round(v/len(analyses)*100, 1)}
            for k, v in sorted(format_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # Unique themes
        theme_counts = {}
        for t in all_themes:
            theme_counts[t] = theme_counts.get(t, 0) + 1
        top_themes = [k for k, v in sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:10]]
        
        # Generate content ideas using AI
        content_ideas = await self._generate_content_ideas(username, top_hooks, top_formats, top_themes)
        
        # Key learnings
        key_learnings = list(set(all_tips))[:10]
        
        return AccountLearnings(
            username=username,
            total_content_analyzed=len(content),
            avg_engagement_rate=avg_engagement,
            top_hooks=top_hooks,
            top_formats=top_formats,
            content_themes=top_themes,
            posting_patterns={
                "total_reels": len([c for c in content if c.media_type == "reel"]),
                "total_posts": len([c for c in content if c.media_type != "reel"]),
            },
            key_learnings=key_learnings,
            content_ideas=content_ideas,
            generated_at=datetime.now().isoformat()
        )
    
    async def _generate_content_ideas(
        self,
        username: str,
        top_hooks: List[Dict],
        top_formats: List[Dict],
        themes: List[str]
    ) -> List[str]:
        """Generate content ideas based on competitor patterns"""
        if not self.api_key:
            return []
        
        try:
            prompt = f"""Based on successful content patterns from @{username}, generate 5 content ideas.

TOP PERFORMING HOOKS:
{json.dumps(top_hooks, indent=2)}

TOP FORMATS:
{json.dumps(top_formats, indent=2)}

MAIN THEMES:
{', '.join(themes[:5])}

Generate 5 specific, actionable content ideas that combine these successful patterns.
Each idea should be 1-2 sentences and ready to create.

Return as a JSON array of strings."""

            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a creative social media strategist. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Error generating content ideas: {e}")
            return []
    
    async def _save_learnings(self, username: str, learnings: AccountLearnings):
        """Save learnings to local files and optionally Supabase."""
        # --- File-based storage (always) ---
        account_dir = COMPETITOR_RESEARCH_DIR / "accounts" / username / "analysis"
        account_dir.mkdir(parents=True, exist_ok=True)
        
        json_path = account_dir / "learnings.json"
        with open(json_path, "w") as f:
            json.dump(learnings.model_dump(), f, indent=2, default=str)
        
        md_content = self._generate_markdown(learnings)
        md_path = account_dir / "learnings.md"
        with open(md_path, "w") as f:
            f.write(md_content)
        
        logger.info(f"Saved learnings to {account_dir}")
        
        # --- Supabase persistence (if available) ---
        await self._persist_to_supabase(username, learnings, md_content)
    
    async def _persist_to_supabase(
        self, username: str, learnings: AccountLearnings, markdown: str
    ):
        """Persist analysis results to Supabase tables."""
        supabase = self._get_supabase()
        if not supabase:
            return
        
        try:
            # Upsert into competitor_account
            account_result = supabase.table('competitor_account').upsert({
                'platform': 'instagram',
                'handle': username,
                'fetched_at': datetime.now().isoformat(),
                'last_full_audit_at': datetime.now().isoformat(),
                'is_active': True,
            }, on_conflict='platform,handle').execute()
            
            account_id = None
            if account_result.data:
                account_id = account_result.data[0].get('account_id')
            
            if not account_id:
                # Fetch account_id if upsert didn't return it
                lookup = supabase.table('competitor_account').select('account_id').eq(
                    'platform', 'instagram'
                ).eq('handle', username).execute()
                if lookup.data:
                    account_id = lookup.data[0].get('account_id')
            
            if not account_id:
                logger.warning(f"Could not get account_id for @{username} in Supabase")
                return
            
            # Save audit report
            report_data = {
                'account_id': account_id,
                'posts_analyzed': learnings.total_content_analyzed,
                'time_window': '30d',
                'strategy': json.dumps({
                    'content_pillars': learnings.content_themes,
                    'hook_system': learnings.top_hooks,
                }),
                'playbook': json.dumps({
                    'content_ideas': learnings.content_ideas,
                    'key_learnings': learnings.key_learnings,
                }),
                'full_report_json': json.dumps(learnings.model_dump(), default=str),
                'report_markdown': markdown,
            }
            
            supabase.table('competitor_audit_report').insert(report_data).execute()
            logger.info(f"Persisted analysis for @{username} to Supabase")
            
        except Exception as e:
            logger.warning(f"Failed to persist analysis to Supabase: {e}")
    
    def _generate_markdown(self, learnings: AccountLearnings) -> str:
        """Generate a markdown summary of learnings"""
        md = f"""# Competitor Analysis: @{learnings.username}

**Generated:** {learnings.generated_at}
**Content Analyzed:** {learnings.total_content_analyzed}
**Avg Engagement:** {learnings.avg_engagement_rate:,.0f} likes/post

---

## Top Performing Hooks

| Hook Type | Count | % of Content |
|-----------|-------|--------------|
"""
        for hook in learnings.top_hooks:
            md += f"| {hook['type']} | {hook['count']} | {hook['percentage']}% |\n"
        
        md += """
## Top Content Formats

| Format | Count | % of Content |
|--------|-------|--------------|
"""
        for fmt in learnings.top_formats:
            md += f"| {fmt['type']} | {fmt['count']} | {fmt['percentage']}% |\n"
        
        md += f"""
## Content Themes

{', '.join(learnings.content_themes)}

## Key Learnings

"""
        for i, learning in enumerate(learnings.key_learnings, 1):
            md += f"{i}. {learning}\n"
        
        md += """
## Content Ideas to Try

"""
        for i, idea in enumerate(learnings.content_ideas, 1):
            md += f"{i}. {idea}\n"
        
        md += f"""
---

## Posting Patterns

- **Reels:** {learnings.posting_patterns.get('total_reels', 0)}
- **Posts:** {learnings.posting_patterns.get('total_posts', 0)}
"""
        return md


# Singleton
_analysis_service: Optional[CompetitorAnalysisService] = None


def get_analysis_service() -> CompetitorAnalysisService:
    """Get singleton analysis service"""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = CompetitorAnalysisService()
    return _analysis_service
