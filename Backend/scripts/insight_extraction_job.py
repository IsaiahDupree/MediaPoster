"""
Insight Extraction Job (Nightly)

This job runs nightly to:
1. Analyze recent winners and losers
2. Extract patterns from high-performing content
3. Update playbook rules with new learnings
4. Generate insights for the next content batch

Architecture: Publish → Measure → Review → Extract Patterns → Update Playbook → Generate → Repeat
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import Counter

import asyncpg
from openai import AsyncOpenAI

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mediaposter")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def get_db_pool():
    return await asyncpg.create_pool(DATABASE_URL)


class InsightExtractor:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    
    async def run(self):
        """Run the full insight extraction pipeline."""
        print("=" * 60)
        print("🧠 INSIGHT EXTRACTION JOB")
        print(f"📅 {datetime.now().isoformat()}")
        print("=" * 60)
        
        # Step 1: Analyze recent reviews
        print("\n📊 Step 1: Analyzing recent reviews...")
        reviews = await self.get_recent_reviews(days=14)
        print(f"   Found {len(reviews)} reviews from last 14 days")
        
        # Step 2: Segment by performance
        winners = [r for r in reviews if r['label'] == 'winner']
        losers = [r for r in reviews if r['label'] == 'loser']
        needs_work = [r for r in reviews if r['label'] == 'needs_iteration']
        
        print(f"   Winners: {len(winners)}")
        print(f"   Needs Work: {len(needs_work)}")
        print(f"   Losers: {len(losers)}")
        
        # Step 3: Extract winner patterns
        print("\n🌟 Step 2: Extracting winner patterns...")
        winner_patterns = await self.extract_patterns(winners, "winner")
        
        # Step 4: Extract failure patterns
        print("\n⚠️ Step 3: Extracting failure patterns...")
        failure_patterns = await self.extract_patterns(losers, "loser")
        
        # Step 5: Update playbook rules
        print("\n📚 Step 4: Updating playbook rules...")
        await self.update_playbook_rules(winner_patterns, failure_patterns)
        
        # Step 6: Generate insights
        print("\n💡 Step 5: Generating insights...")
        await self.generate_insights(winners, losers, winner_patterns, failure_patterns)
        
        # Step 7: Summary
        print("\n" + "=" * 60)
        print("✅ INSIGHT EXTRACTION COMPLETE")
        print("=" * 60)
    
    async def get_recent_reviews(self, days: int = 14) -> List[Dict]:
        """Get reviews from the last N days with full context."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    r.id, r.posting_id, r.window_id, r.final_score, r.label,
                    r.failure_reasons, r.next_action, r.reviewed_at,
                    p.platform, p.caption_text, p.hashtags,
                    ci.title, ci.source_type, ci.format_type, ci.hook_text,
                    ci.cta_type, ci.duration_sec,
                    ms.views, ms.likes, ms.comments, ms.shares, ms.saves,
                    rw.name AS window_name
                FROM reviews r
                JOIN postings p ON p.id = r.posting_id
                JOIN content_items ci ON ci.id = p.content_item_id
                JOIN review_windows rw ON rw.id = r.window_id
                LEFT JOIN LATERAL (
                    SELECT * FROM metric_snapshots 
                    WHERE posting_id = p.id 
                    ORDER BY captured_at DESC LIMIT 1
                ) ms ON true
                WHERE r.reviewed_at > NOW() - INTERVAL '%s days'
                ORDER BY r.final_score DESC
            """ % days)
            
        return [dict(r) for r in rows]
    
    async def extract_patterns(self, reviews: List[Dict], category: str) -> Dict:
        """Extract patterns from a set of reviews."""
        if not reviews:
            return {}
        
        patterns = {
            "source_types": Counter(),
            "format_types": Counter(),
            "platforms": Counter(),
            "cta_types": Counter(),
            "hook_patterns": [],
            "duration_ranges": [],
            "engagement_rates": [],
            "failure_reasons": Counter()
        }
        
        for r in reviews:
            if r.get('source_type'):
                patterns["source_types"][r['source_type']] += 1
            if r.get('format_type'):
                patterns["format_types"][r['format_type']] += 1
            if r.get('platform'):
                patterns["platforms"][r['platform']] += 1
            if r.get('cta_type'):
                patterns["cta_types"][r['cta_type']] += 1
            if r.get('hook_text'):
                patterns["hook_patterns"].append(r['hook_text'])
            if r.get('duration_sec'):
                patterns["duration_ranges"].append(r['duration_sec'])
            if r.get('views') and r['views'] > 0:
                eng_rate = (r.get('likes', 0) + r.get('comments', 0) + r.get('shares', 0)) / r['views']
                patterns["engagement_rates"].append(eng_rate)
            if r.get('failure_reasons'):
                for reason in r['failure_reasons']:
                    patterns["failure_reasons"][reason] += 1
        
        # Compute averages
        if patterns["duration_ranges"]:
            patterns["avg_duration"] = sum(patterns["duration_ranges"]) / len(patterns["duration_ranges"])
        if patterns["engagement_rates"]:
            patterns["avg_engagement_rate"] = sum(patterns["engagement_rates"]) / len(patterns["engagement_rates"])
        
        print(f"   {category.upper()} patterns:")
        print(f"     Top source: {patterns['source_types'].most_common(1)}")
        print(f"     Top format: {patterns['format_types'].most_common(1)}")
        print(f"     Top platform: {patterns['platforms'].most_common(1)}")
        
        return patterns
    
    async def update_playbook_rules(self, winner_patterns: Dict, failure_patterns: Dict):
        """Update playbook rules based on extracted patterns."""
        async with self.pool.acquire() as conn:
            rules_created = 0
            
            # Winner source type rule
            if winner_patterns.get("source_types"):
                top_source = winner_patterns["source_types"].most_common(1)
                if top_source:
                    source, count = top_source[0]
                    await conn.execute("""
                        INSERT INTO playbook_rules (rule_type, rule_text, confidence_score, supporting_count)
                        VALUES ('structure', $1, $2, $3)
                        ON CONFLICT DO NOTHING
                    """, f"{source} content consistently outperforms other source types", 
                        min(count * 10, 90), count)
                    rules_created += 1
            
            # Duration rule
            if winner_patterns.get("avg_duration"):
                avg_dur = winner_patterns["avg_duration"]
                await conn.execute("""
                    INSERT INTO playbook_rules (rule_type, rule_text, confidence_score)
                    VALUES ('pacing', $1, $2)
                    ON CONFLICT DO NOTHING
                """, f"Optimal video duration is around {int(avg_dur)} seconds for best performance", 70)
                rules_created += 1
            
            # Failure pattern rules
            if failure_patterns.get("failure_reasons"):
                for reason, count in failure_patterns["failure_reasons"].most_common(3):
                    await conn.execute("""
                        INSERT INTO playbook_rules (rule_type, rule_text, confidence_score, supporting_count)
                        VALUES ('structure', $1, $2, $3)
                        ON CONFLICT DO NOTHING
                    """, f"AVOID: {reason.replace('_', ' ')} - common failure pattern", 
                        min(count * 15, 85), count)
                    rules_created += 1
            
            print(f"   Created/updated {rules_created} playbook rules")
    
    async def generate_insights(
        self, 
        winners: List[Dict], 
        losers: List[Dict],
        winner_patterns: Dict,
        failure_patterns: Dict
    ):
        """Generate and store insights using AI."""
        async with self.pool.acquire() as conn:
            insights_created = 0
            
            # Winner pattern insight
            if winner_patterns.get("source_types"):
                top_source = winner_patterns["source_types"].most_common(1)
                if top_source:
                    source, count = top_source[0]
                    await conn.execute("""
                        INSERT INTO insights (
                            insight_type, title, description, 
                            sample_size, confidence_score, recommended_actions
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                    """, 
                        'winner_pattern',
                        f'{source} Content Dominates',
                        f'{source} content type has {count} winners in the last 14 days, outperforming other formats.',
                        count,
                        min(count * 10, 95),
                        json.dumps([
                            f"Prioritize {source} content in upcoming slots",
                            f"Analyze top {source} performers for hook patterns",
                            "Consider increasing production capacity for this format"
                        ])
                    )
                    insights_created += 1
            
            # Engagement insight
            if winner_patterns.get("avg_engagement_rate") and failure_patterns.get("avg_engagement_rate"):
                winner_eng = winner_patterns["avg_engagement_rate"] * 100
                loser_eng = failure_patterns.get("avg_engagement_rate", 0) * 100
                diff = winner_eng - loser_eng
                
                await conn.execute("""
                    INSERT INTO insights (
                        insight_type, title, description,
                        confidence_score, recommended_actions
                    ) VALUES ($1, $2, $3, $4, $5)
                """,
                    'winner_pattern',
                    'Engagement Gap Identified',
                    f'Winners average {winner_eng:.2f}% engagement vs {loser_eng:.2f}% for losers. {diff:.1f}pp difference.',
                    75,
                    json.dumps([
                        "Add stronger CTAs to increase engagement",
                        "Test different hook styles",
                        "Analyze winner captions for patterns"
                    ])
                )
                insights_created += 1
            
            # Failure pattern insight
            if failure_patterns.get("failure_reasons"):
                top_failures = failure_patterns["failure_reasons"].most_common(3)
                failure_list = [f.replace('_', ' ') for f, _ in top_failures]
                
                await conn.execute("""
                    INSERT INTO insights (
                        insight_type, title, description,
                        confidence_score, recommended_actions
                    ) VALUES ($1, $2, $3, $4, $5)
                """,
                    'failure_pattern',
                    'Common Failure Patterns',
                    f'Top failure reasons: {", ".join(failure_list)}. Address these in upcoming content.',
                    80,
                    json.dumps([
                        f"Review and fix: {failure_list[0]}" if failure_list else "Review failures",
                        "Update content briefs to address issues",
                        "Add pre-publish checklist items"
                    ])
                )
                insights_created += 1
            
            # AI-powered deep insight (if OpenAI available)
            if self.client and winners:
                try:
                    await self.generate_ai_insight(conn, winners[:5], losers[:5])
                    insights_created += 1
                except Exception as e:
                    print(f"   AI insight generation failed: {e}")
            
            print(f"   Generated {insights_created} new insights")
    
    async def generate_ai_insight(self, conn, winners: List[Dict], losers: List[Dict]):
        """Use OpenAI to generate deeper insights."""
        winner_summaries = [
            f"- {w.get('title', 'Untitled')} ({w.get('source_type', 'unknown')}): "
            f"{w.get('views', 0)} views, {w.get('likes', 0)} likes, score {w.get('final_score', 0)}"
            for w in winners
        ]
        
        loser_summaries = [
            f"- {l.get('title', 'Untitled')} ({l.get('source_type', 'unknown')}): "
            f"{l.get('views', 0)} views, {l.get('likes', 0)} likes, "
            f"failures: {l.get('failure_reasons', [])}"
            for l in losers
        ]
        
        prompt = f"""Analyze these content performance results and provide ONE actionable insight.

TOP PERFORMERS:
{chr(10).join(winner_summaries)}

UNDERPERFORMERS:
{chr(10).join(loser_summaries)}

Provide a single, specific insight about what differentiates winners from losers.
Format: Start with a clear title, then 2-3 sentences of analysis, then one recommended action.
Keep it under 100 words total."""

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        
        insight_text = response.choices[0].message.content.strip()
        
        # Parse title from first line
        lines = insight_text.split('\n')
        title = lines[0].replace('#', '').replace('*', '').strip()[:100]
        description = '\n'.join(lines[1:]).strip()[:500]
        
        await conn.execute("""
            INSERT INTO insights (
                insight_type, title, description,
                confidence_score, sample_size
            ) VALUES ($1, $2, $3, $4, $5)
        """,
            'winner_pattern',
            title,
            description,
            85,
            len(winners) + len(losers)
        )
        
        print(f"   AI Insight: {title}")


async def main():
    pool = await get_db_pool()
    try:
        extractor = InsightExtractor(pool)
        await extractor.run()
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
