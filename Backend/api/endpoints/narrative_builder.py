"""
Narrative Builder API Endpoints
Provides signals, recommendations, and scheduling support for AI-powered content strategy
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import json

router = APIRouter(prefix="/api/narrative-builder", tags=["Narrative Builder"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

def get_engine():
    return create_engine(DATABASE_URL)


# =============================================================================
# MODELS
# =============================================================================

class NarrativeGoal(BaseModel):
    goal: str
    cta_type: str
    pillars: List[str]
    audience: str
    time_horizon: str
    platforms: List[str]
    max_posts_per_day: int
    content_mix: Dict[str, int]


class SignalMetrics(BaseModel):
    creative_fatigue: float
    topic_momentum: List[Dict[str, Any]]
    retention_health: Dict[str, float]
    sentiment_health: Dict[str, Any]
    conversion_signals: Dict[str, float]
    tone_distribution: List[Dict[str, Any]]
    pacing_distribution: List[Dict[str, Any]]
    posting_frequency: List[Dict[str, Any]]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/signals")
async def get_narrative_signals():
    """Get all signal metrics for the narrative builder dashboard."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # 1. Creative Fatigue - % of content used in last 30 days
        total_content = conn.execute(text("""
            SELECT COUNT(*) FROM video_analysis
        """)).scalar() or 1
        
        used_content = conn.execute(text("""
            SELECT COUNT(DISTINCT content_id) 
            FROM scheduled_posts 
            WHERE scheduled_at > NOW() - INTERVAL '30 days'
            AND content_id IS NOT NULL
        """)).scalar() or 0
        
        creative_fatigue = round((used_content / total_content) * 100, 1) if total_content > 0 else 0
        
        # 2. Topic Momentum - trending topics based on analysis
        topic_results = conn.execute(text("""
            SELECT 
                unnest(topics) as topic,
                COUNT(*) as count,
                AVG(pre_social_score) as avg_score
            FROM video_analysis
            WHERE topics IS NOT NULL AND array_length(topics, 1) > 0
            GROUP BY topic
            ORDER BY count DESC
            LIMIT 10
        """)).fetchall()
        
        topic_momentum = []
        for row in topic_results:
            # Determine trend based on score
            score = float(row[2]) if row[2] else 50
            trend = 'up' if score > 60 else 'down' if score < 40 else 'stable'
            topic_momentum.append({
                'topic': row[0],
                'count': row[1],
                'score': round(score, 1),
                'trend': trend
            })
        
        # 3. Retention Health - based on video scores
        retention_stats = conn.execute(text("""
            SELECT 
                AVG(pre_social_score) as avg_score,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY pre_social_score) as p25,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY pre_social_score) as p75
            FROM video_analysis
            WHERE pre_social_score IS NOT NULL
        """)).fetchone()
        
        avg_score = float(retention_stats[0]) if retention_stats[0] else 50
        retention_health = {
            'hook_rate': round(min(avg_score * 1.2, 100), 1),  # Estimate hook rate
            'avg_viewed': round(avg_score, 1),
            'completion_rate': round(avg_score * 0.7, 1)  # Estimate completion
        }
        
        # 4. Sentiment Health - from posted content engagement
        engagement_stats = conn.execute(text("""
            SELECT 
                AVG(CASE WHEN likes > 0 THEN 1 ELSE 0 END) * 100 as like_rate,
                AVG(CASE WHEN comments > 0 THEN 1 ELSE 0 END) * 100 as comment_rate,
                AVG(engagement_rate) as avg_engagement
            FROM posted_content
            WHERE views > 0
        """)).fetchone()
        
        # Estimate sentiment from engagement
        like_rate = float(engagement_stats[0]) if engagement_stats[0] else 50
        sentiment_health = {
            'positive': round(min(like_rate + 20, 80), 1),
            'neutral': round(max(100 - like_rate - 20, 15), 1),
            'negative': round(max(10 - like_rate/10, 5), 1),
            'top_themes': ['helpful', 'informative', 'want more', 'tutorial request']
        }
        
        # 5. Conversion Signals
        conversion_stats = conn.execute(text("""
            SELECT 
                AVG(engagement_rate) * 100 as avg_engagement,
                AVG(CASE WHEN comments > 0 THEN comments::float / NULLIF(views, 0) * 100 ELSE 0 END) as comment_rate
            FROM posted_content
            WHERE views > 0
        """)).fetchone()
        
        conversion_signals = {
            'ctr': round(float(conversion_stats[0]) if conversion_stats[0] else 2.5, 2),
            'high_intent_rate': round(float(conversion_stats[1]) if conversion_stats[1] else 8.0, 2)
        }
        
        # 6. Tone Distribution
        tone_results = conn.execute(text("""
            SELECT tone, COUNT(*) as count
            FROM video_analysis
            WHERE tone IS NOT NULL AND tone != ''
            GROUP BY tone
            ORDER BY count DESC
            LIMIT 8
        """)).fetchall()
        
        tone_distribution = [{'tone': row[0], 'count': row[1]} for row in tone_results]
        
        # 7. Pacing Distribution
        pacing_results = conn.execute(text("""
            SELECT pacing, COUNT(*) as count
            FROM video_analysis
            WHERE pacing IS NOT NULL AND pacing != ''
            AND pacing NOT LIKE 'Unknown%'
            GROUP BY pacing
            ORDER BY count DESC
        """)).fetchall()
        
        pacing_distribution = [{'pacing': row[0], 'count': row[1]} for row in pacing_results]
        
        # 8. Posting Frequency
        frequency_results = conn.execute(text("""
            SELECT 
                DATE(scheduled_at) as post_date,
                COUNT(*) as post_count,
                platform
            FROM scheduled_posts
            WHERE scheduled_at > NOW() - INTERVAL '14 days'
            AND scheduled_at < NOW() + INTERVAL '14 days'
            GROUP BY DATE(scheduled_at), platform
            ORDER BY post_date
        """)).fetchall()
        
        posting_frequency = [
            {'date': str(row[0]), 'count': row[1], 'platform': row[2]} 
            for row in frequency_results
        ]
    
    return {
        'creative_fatigue': creative_fatigue,
        'topic_momentum': topic_momentum,
        'retention_health': retention_health,
        'sentiment_health': sentiment_health,
        'conversion_signals': conversion_signals,
        'tone_distribution': tone_distribution,
        'pacing_distribution': pacing_distribution,
        'posting_frequency': posting_frequency
    }


@router.get("/candidates")
async def get_candidate_pool(
    limit: int = 50,
    status: Optional[str] = None,
    pillar: Optional[str] = None
):
    """Get candidate media items for scheduling with enriched data from 3-level mapping."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get videos with analysis, metrics rollup, and posting history
        result = conn.execute(text("""
            SELECT 
                v.id,
                v.file_name,
                v.duration_sec,
                v.thumbnail_path,
                v.aspect_ratio,
                va.pre_social_score,
                va.curation_status,
                va.hooks,
                va.topics,
                va.tone,
                va.pacing,
                va.transcript,
                va.detected_hook,
                va.pillar_tags,
                va.format_tags,
                va.analyzed_at,
                -- From creative_asset_metrics (rollup)
                COALESCE(cam.total_posts, 0) as total_posts,
                COALESCE(cam.total_views, 0) as total_views,
                cam.last_posted_at,
                cam.avg_sentiment_score,
                cam.performance_decay_rate,
                cam.avg_hook_rate_3s,
                cam.avg_percent_viewed,
                -- Calculate days since last post
                EXTRACT(EPOCH FROM (NOW() - cam.last_posted_at)) / 86400 as days_since_posted
            FROM videos v
            INNER JOIN video_analysis va ON v.id = va.video_id
            LEFT JOIN creative_asset_metrics cam ON v.id = cam.video_id
            WHERE va.pre_social_score IS NOT NULL
            ORDER BY va.pre_social_score DESC NULLS LAST
            LIMIT :limit
        """), {'limit': limit}).fetchall()
        
        candidates = []
        for i, row in enumerate(result):
            # Row mapping from new query:
            # 0: id, 1: file_name, 2: duration_sec, 3: thumbnail_path, 4: aspect_ratio
            # 5: pre_social_score, 6: curation_status, 7: hooks, 8: topics, 9: tone
            # 10: pacing, 11: transcript, 12: detected_hook, 13: pillar_tags, 14: format_tags
            # 15: analyzed_at, 16: total_posts, 17: total_views, 18: last_posted_at
            # 19: avg_sentiment_score, 20: performance_decay_rate, 21: avg_hook_rate_3s
            # 22: avg_percent_viewed, 23: days_since_posted
            
            total_posts = row[16] or 0
            
            # Determine status based on post count
            if total_posts == 0:
                item_status = 'fresh'
            elif total_posts <= 3:
                item_status = 'tested'
            else:
                item_status = 'saturated'
            
            # Convert thumbnail path
            thumb_path = row[3]
            if thumb_path and thumb_path.startswith("/tmp/mediaposter/thumbnails/"):
                thumb_filename = thumb_path.split("/")[-1]
                thumb_path = f"/thumbnails/{thumb_filename}"
            
            # Get pillar from pillar_tags or topics
            pillar_tags = row[13] or []
            topics = row[8] or []
            pillar = pillar_tags[0] if pillar_tags else (topics[0] if topics else 'general')
            
            # Calculate novelty score (100 = never posted, decays)
            novelty_score = max(100 - (total_posts * 25), 10)
            
            # Calculate cooldown score based on days since posted
            days_since = row[23] or 999
            cooldown_ok = days_since > 7 if days_since else True
            
            candidates.append({
                'id': str(row[0]),
                'index': i + 1,
                'title': row[1] or 'Untitled',
                'duration_sec': row[2],
                'thumbnail_path': thumb_path,
                'aspect_ratio': row[4],
                'score': int(row[5]) if row[5] else 0,
                'curation_status': row[6] or 'pending',
                'hooks': row[7] or [],
                'topics': topics,
                'tone': row[9],
                'pacing': row[10],
                'transcript': row[11][:200] if row[11] else None,
                'detected_hook': row[12],
                'pillar_tags': pillar_tags,
                'format_tags': row[14] or [],
                'analyzed_at': str(row[15]) if row[15] else None,
                'status': item_status,
                'post_count': total_posts,
                'total_views': row[17] or 0,
                'last_posted': str(row[18]) if row[18] else None,
                'days_since_posted': round(days_since, 1) if days_since and days_since < 999 else None,
                'avg_sentiment_score': float(row[19]) if row[19] else None,
                'avg_hook_rate': float(row[21]) if row[21] else None,
                'avg_percent_viewed': float(row[22]) if row[22] else None,
                'novelty_score': novelty_score,
                'cooldown_ok': cooldown_ok,
                'pillar': pillar,
                'format': 'video',
            })
    
    # Calculate status counts
    status_counts = {
        'fresh': len([c for c in candidates if c['status'] == 'fresh']),
        'tested': len([c for c in candidates if c['status'] == 'tested']),
        'saturated': len([c for c in candidates if c['status'] == 'saturated']),
    }
    
    return {
        'candidates': candidates,
        'total': len(candidates),
        'status_counts': status_counts
    }


@router.post("/generate-recommendations")
async def generate_recommendations(goal: NarrativeGoal):
    """Generate AI-powered content recommendations based on narrative goal."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get candidate pool
        result = conn.execute(text("""
            SELECT 
                v.id,
                v.file_name,
                v.duration_sec,
                v.thumbnail_path,
                va.pre_social_score,
                va.hooks,
                va.topics,
                va.tone,
                va.pacing,
                COALESCE(sp.schedule_count, 0) as schedule_count
            FROM videos v
            INNER JOIN video_analysis va ON v.id = va.video_id
            LEFT JOIN (
                SELECT content_id::uuid, COUNT(*) as schedule_count
                FROM scheduled_posts
                WHERE content_id IS NOT NULL
                GROUP BY content_id::uuid
            ) sp ON v.id = sp.content_id
            WHERE va.pre_social_score IS NOT NULL
            AND (sp.schedule_count IS NULL OR sp.schedule_count < 5)
            ORDER BY va.pre_social_score DESC
            LIMIT 30
        """)).fetchall()
        
        recommendations = []
        suggested_times = ['9:00 AM', '12:00 PM', '3:00 PM', '6:00 PM', '8:00 PM']
        
        for i, row in enumerate(result[:10]):
            score = float(row[4]) if row[4] else 50
            topics = row[6] or []
            hooks = row[5] or []
            schedule_count = row[9] or 0
            
            # Calculate scores
            # Narrative alignment - how well topics match pillars
            pillar_match = sum(1 for t in topics if any(p in t.lower() for p in goal.pillars))
            narrative_score = min(60 + (pillar_match * 15), 100)
            
            # Predicted performance based on historical score
            predicted_performance = min(score + 10, 100)
            
            # Sentiment fit - higher for fresher content
            sentiment_fit = 90 - (schedule_count * 10) if schedule_count < 5 else 50
            
            # Novelty score
            novelty_score = 100 - (schedule_count * 20) if schedule_count < 5 else 20
            
            # Overall score (weighted average)
            overall_score = int(
                (narrative_score * 0.3) +
                (predicted_performance * 0.35) +
                (sentiment_fit * 0.15) +
                (novelty_score * 0.2)
            )
            
            # Generate reasoning
            reasoning = []
            if pillar_match > 0:
                reasoning.append(f"Aligns with {pillar_match} of your narrative pillars")
            reasoning.append(f"Historical performance score: {int(score)}/100")
            if schedule_count == 0:
                reasoning.append("Fresh content - never posted before")
            elif schedule_count <= 2:
                reasoning.append(f"Light usage ({schedule_count}x) - room to grow")
            
            # Convert thumbnail path
            thumb_path = row[3]
            if thumb_path and thumb_path.startswith("/tmp/mediaposter/thumbnails/"):
                thumb_filename = thumb_path.split("/")[-1]
                thumb_path = f"/thumbnails/{thumb_filename}"
            
            recommendations.append({
                'id': f'rec-{i}',
                'media': {
                    'id': str(row[0]),
                    'title': row[1] or 'Untitled',
                    'duration_sec': row[2],
                    'thumbnail_path': thumb_path,
                    'score': int(score),
                    'hooks': hooks,
                    'topics': topics,
                    'tone': row[7],
                    'status': 'fresh' if schedule_count == 0 else 'tested' if schedule_count <= 3 else 'saturated',
                    'post_count': schedule_count,
                },
                'narrative_score': int(narrative_score),
                'predicted_performance': int(predicted_performance),
                'sentiment_fit': int(sentiment_fit),
                'novelty_score': int(novelty_score),
                'overall_score': overall_score,
                'reasoning': reasoning,
                'suggested_caption': hooks[0] if hooks else f"Check out this {topics[0] if topics else 'content'}!",
                'suggested_time': suggested_times[i % len(suggested_times)],
                'platforms': goal.platforms,
            })
        
        # Sort by overall score
        recommendations.sort(key=lambda x: x['overall_score'], reverse=True)
        
        # Add rank
        for i, rec in enumerate(recommendations):
            rec['rank'] = i + 1
        
        # Save recommendations to database
        try:
            # Clear old recommendations
            conn.execute(text("DELETE FROM narrative_recommendations WHERE created_at < NOW() - INTERVAL '7 days'"))
            
            # Insert new recommendations
            for rec in recommendations:
                conn.execute(text("""
                    INSERT INTO narrative_recommendations (
                        video_id, rank, narrative_score, predicted_performance,
                        sentiment_fit, novelty_score, overall_score, reasoning,
                        suggested_caption, suggested_time, platforms, goal_text
                    ) VALUES (
                        :video_id, :rank, :narrative, :performance,
                        :sentiment, :novelty, :overall, :reasoning,
                        :caption, :time, :platforms, :goal
                    )
                    ON CONFLICT (video_id) DO UPDATE SET
                        rank = EXCLUDED.rank,
                        narrative_score = EXCLUDED.narrative_score,
                        predicted_performance = EXCLUDED.predicted_performance,
                        overall_score = EXCLUDED.overall_score,
                        updated_at = NOW()
                """), {
                    'video_id': rec['media']['id'],
                    'rank': rec['rank'],
                    'narrative': rec['narrative_score'],
                    'performance': rec['predicted_performance'],
                    'sentiment': rec['sentiment_fit'],
                    'novelty': rec['novelty_score'],
                    'overall': rec['overall_score'],
                    'reasoning': ', '.join(rec['reasoning']),
                    'caption': rec['suggested_caption'],
                    'time': rec['suggested_time'],
                    'platforms': rec['platforms'],
                    'goal': goal.goal[:200],
                })
            conn.commit()
        except Exception as e:
            print(f"Warning: Could not save recommendations: {e}")
    
    return {
        'recommendations': recommendations,
        'goal_summary': {
            'goal': goal.goal[:100] + '...' if len(goal.goal) > 100 else goal.goal,
            'cta': goal.cta_type,
            'pillars': goal.pillars,
            'platforms': goal.platforms,
            'time_horizon': goal.time_horizon,
        }
    }


@router.get("/saved-recommendations")
async def get_saved_recommendations():
    """Get previously saved recommendations."""
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                cr.video_id, cr.rank, cr.narrative_score, cr.predicted_performance,
                cr.sentiment_fit, cr.novelty_score, cr.overall_score, cr.reasoning,
                cr.suggested_caption, cr.suggested_time, cr.platforms, cr.goal_text,
                cr.created_at,
                v.file_name, v.duration_sec, v.thumbnail_path,
                va.pre_social_score, va.hooks, va.topics, va.tone
            FROM narrative_recommendations cr
            JOIN videos v ON cr.video_id = v.id
            JOIN video_analysis va ON v.id = va.video_id
            ORDER BY cr.rank
            LIMIT 20
        """)).fetchall()
        
        recommendations = []
        for row in result:
            thumb_path = row[15]
            if thumb_path and thumb_path.startswith("/tmp/mediaposter/thumbnails/"):
                thumb_filename = thumb_path.split("/")[-1]
                thumb_path = f"/thumbnails/{thumb_filename}"
            
            hooks = row[17] or []
            topics = row[18] or []
            
            recommendations.append({
                'id': f'rec-{row[1]}',
                'media': {
                    'id': str(row[0]),
                    'title': row[13] or 'Untitled',
                    'duration_sec': row[14],
                    'thumbnail_path': thumb_path,
                    'score': int(row[16]) if row[16] else 0,
                    'hooks': hooks,
                    'topics': topics,
                    'tone': row[19],
                    'status': 'recommended',
                    'post_count': 0,
                },
                'narrative_score': row[2],
                'predicted_performance': row[3],
                'sentiment_fit': row[4],
                'novelty_score': row[5],
                'overall_score': row[6],
                'reasoning': row[7].split(', ') if row[7] else [],
                'suggested_caption': row[8],
                'suggested_time': row[9],
                'platforms': row[10] or [],
                'rank': row[1],
                'saved_at': str(row[12]) if row[12] else None,
            })
        
        return {
            'recommendations': recommendations,
            'count': len(recommendations),
        }


# =============================================================================
# PHASE 3: NARRATIVE GOALS MANAGEMENT
# =============================================================================

class NarrativeGoalCreate(BaseModel):
    name: str
    description: Optional[str] = None
    goal_type: str = 'growth'  # 'campaign', 'series', 'funnel_stage', 'growth'
    target_metric: Optional[str] = None
    target_value: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    content_pillars: List[str] = []
    platform_mix: Dict[str, float] = {}  # e.g., {"tiktok": 0.5, "instagram": 0.3}
    posting_cadence: Dict[str, int] = {}  # e.g., {"min_per_day": 1, "max_per_day": 3}
    playbook_id: Optional[str] = None


@router.get("/goals")
async def list_narrative_goals(status: str = 'active'):
    """List narrative goals for mainline content."""
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                SELECT id, name, description, goal_type, target_metric, target_value,
                       current_value, start_date, end_date, content_pillars, platform_mix,
                       posting_cadence, playbook_id, priority, status, progress_percent,
                       created_at, updated_at
                FROM narrative_goals
                WHERE status = :status
                ORDER BY priority DESC, created_at DESC
            """), {'status': status}).fetchall()
            
            goals = []
            for row in result:
                goals.append({
                    'id': str(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'goal_type': row[3],
                    'target_metric': row[4],
                    'target_value': float(row[5]) if row[5] else None,
                    'current_value': float(row[6]) if row[6] else None,
                    'start_date': str(row[7]) if row[7] else None,
                    'end_date': str(row[8]) if row[8] else None,
                    'content_pillars': row[9] or [],
                    'platform_mix': row[10] or {},
                    'posting_cadence': row[11] or {},
                    'playbook_id': str(row[12]) if row[12] else None,
                    'priority': row[13],
                    'status': row[14],
                    'progress_percent': float(row[15]) if row[15] else 0,
                    'created_at': str(row[16]) if row[16] else None
                })
            
            return {'goals': goals, 'count': len(goals)}
        except Exception as e:
            return {'goals': [], 'count': 0, 'error': str(e)}


@router.post("/goals")
async def create_narrative_goal(goal: NarrativeGoalCreate):
    """Create a new narrative goal."""
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                INSERT INTO narrative_goals (
                    name, description, goal_type, target_metric, target_value,
                    start_date, end_date, content_pillars, platform_mix,
                    posting_cadence, playbook_id
                ) VALUES (
                    :name, :description, :goal_type, :target_metric, :target_value,
                    :start_date, :end_date, :content_pillars::jsonb, :platform_mix::jsonb,
                    :posting_cadence::jsonb, :playbook_id
                )
                RETURNING id
            """), {
                'name': goal.name,
                'description': goal.description,
                'goal_type': goal.goal_type,
                'target_metric': goal.target_metric,
                'target_value': goal.target_value,
                'start_date': goal.start_date,
                'end_date': goal.end_date,
                'content_pillars': json.dumps(goal.content_pillars),
                'platform_mix': json.dumps(goal.platform_mix),
                'posting_cadence': json.dumps(goal.posting_cadence),
                'playbook_id': goal.playbook_id
            })
            
            goal_id = str(result.fetchone()[0])
            conn.commit()
            
            return {'id': goal_id, 'name': goal.name, 'message': 'Goal created'}
        except Exception as e:
            return {'error': str(e), 'message': 'Could not create goal. Run migrations first.'}


@router.patch("/goals/{goal_id}")
async def update_narrative_goal(goal_id: str, updates: Dict[str, Any]):
    """Update a narrative goal."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Build dynamic update query
        set_clauses = []
        params = {'id': goal_id}
        
        for key, value in updates.items():
            if key in ['name', 'description', 'goal_type', 'target_metric', 'status']:
                set_clauses.append(f"{key} = :{key}")
                params[key] = value
            elif key in ['target_value', 'current_value', 'progress_percent', 'priority']:
                set_clauses.append(f"{key} = :{key}")
                params[key] = float(value) if value else None
            elif key in ['content_pillars', 'platform_mix', 'posting_cadence']:
                set_clauses.append(f"{key} = :{key}::jsonb")
                params[key] = json.dumps(value)
        
        if not set_clauses:
            return {'error': 'No valid fields to update'}
        
        set_clauses.append("updated_at = NOW()")
        
        conn.execute(text(f"""
            UPDATE narrative_goals 
            SET {', '.join(set_clauses)}
            WHERE id = :id
        """), params)
        conn.commit()
        
        return {'id': goal_id, 'updated': list(updates.keys())}


# =============================================================================
# PHASE 3: 7-DAY LOOKAHEAD PLANNING
# =============================================================================

@router.get("/plan/7-day")
async def get_seven_day_plan():
    """Generate a 7-day content plan based on goals, rules, and opportunities."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # 1. Get active goals (with fallback if table/columns don't exist)
        goals = []
        try:
            goals = conn.execute(text("""
                SELECT id, name, content_pillars, platform_mix, posting_cadence
                FROM narrative_goals WHERE status = 'active'
                ORDER BY priority DESC LIMIT 3
            """)).fetchall()
        except Exception as e:
            # Table or column might not exist yet
            pass
        
        # 2. Get applicable KB rules
        rules = []
        try:
            rules_result = conn.execute(text("""
                SELECT id, rule_type, recommendation, expected_lift, confidence
                FROM kb_rules WHERE status = 'active'
                ORDER BY confidence DESC LIMIT 10
            """)).fetchall()
            rules = [{'id': str(r[0]), 'type': r[1], 'recommendation': r[2], 
                     'lift': float(r[3]) if r[3] else 0, 'confidence': float(r[4]) if r[4] else 0}
                    for r in rules_result]
        except:
            pass
        
        # 3. Get trend opportunities
        opportunities = []
        try:
            opp_result = conn.execute(text("""
                SELECT id, title, opportunity_score, priority, recommended_actions
                FROM trend_opportunities 
                WHERE status = 'new' AND window_end > NOW()
                ORDER BY opportunity_score DESC LIMIT 5
            """)).fetchall()
            opportunities = [{'id': str(o[0]), 'title': o[1], 'score': float(o[2]) if o[2] else 0,
                            'priority': o[3], 'actions': o[4] or []}
                           for o in opp_result]
        except:
            pass
        
        # 4. Get candidate content
        candidates = conn.execute(text("""
            SELECT v.id, v.file_name, va.pre_social_score, va.topics, va.pillar_tags,
                   COALESCE(cam.total_posts, 0) as post_count,
                   cam.last_posted_at
            FROM videos v
            INNER JOIN video_analysis va ON v.id = va.video_id
            LEFT JOIN creative_asset_metrics cam ON v.id = cam.video_id
            WHERE va.pre_social_score >= 50
            AND (cam.total_posts IS NULL OR cam.total_posts < 5)
            AND (cam.last_posted_at IS NULL OR cam.last_posted_at < NOW() - INTERVAL '7 days')
            ORDER BY va.pre_social_score DESC
            LIMIT 30
        """)).fetchall()
        
        # 5. Get MAINLINE accounts
        mainline_accounts = []
        try:
            accounts = conn.execute(text("""
                SELECT id, platform, handle FROM social_accounts
                WHERE account_role = 'MAINLINE' AND is_active = true
            """)).fetchall()
            mainline_accounts = [{'id': str(a[0]), 'platform': a[1], 'handle': a[2]} for a in accounts]
        except:
            # Fallback if account_role doesn't exist
            accounts = conn.execute(text("""
                SELECT id, platform, handle FROM social_accounts WHERE is_active = true
            """)).fetchall()
            mainline_accounts = [{'id': str(a[0]), 'platform': a[1], 'handle': a[2]} for a in accounts]
        
        # 6. Generate 7-day plan
        plan_days = []
        candidate_idx = 0
        
        for day_offset in range(7):
            day_date = datetime.now() + timedelta(days=day_offset)
            day_name = day_date.strftime('%A')
            
            # Determine posts for this day based on cadence
            posts_today = 2  # Default
            if goals:
                cadence = goals[0][4] or {}
                posts_today = cadence.get('target_per_day', 2)
            
            day_posts = []
            for post_num in range(min(posts_today, 3)):
                if candidate_idx < len(candidates):
                    cand = candidates[candidate_idx]
                    candidate_idx += 1
                    
                    # Determine best platform
                    platform = 'tiktok'
                    if goals and goals[0][3]:
                        platform_mix = goals[0][3]
                        platform = max(platform_mix.items(), key=lambda x: x[1])[0] if platform_mix else 'tiktok'
                    
                    # Determine time slot
                    time_slots = ['9:00 AM', '12:00 PM', '6:00 PM']
                    time_slot = time_slots[post_num % len(time_slots)]
                    
                    # Check if trend-reactive slot
                    trend_slot = day_offset == 0 and post_num == 0 and opportunities
                    
                    post = {
                        'slot': post_num + 1,
                        'content_id': str(cand[0]),
                        'content_title': cand[1],
                        'content_score': int(cand[2]) if cand[2] else 0,
                        'topics': cand[3] or [],
                        'platform': platform,
                        'suggested_time': time_slot,
                        'type': 'trend_reactive' if trend_slot else 'planned',
                        'trend_opportunity': opportunities[0] if trend_slot else None,
                        'applicable_rules': [r for r in rules if r['type'] in ['hook', 'timing']][:2]
                    }
                    day_posts.append(post)
            
            plan_days.append({
                'date': day_date.strftime('%Y-%m-%d'),
                'day_name': day_name,
                'posts': day_posts,
                'total_posts': len(day_posts)
            })
        
        return {
            'plan': plan_days,
            'total_posts': sum(d['total_posts'] for d in plan_days),
            'goals_applied': [{'id': str(g[0]), 'name': g[1]} for g in goals],
            'rules_applied': len(rules),
            'trend_opportunities': len(opportunities),
            'mainline_accounts': mainline_accounts,
            'generated_at': datetime.now().isoformat()
        }


# =============================================================================
# PHASE 3: KNOWLEDGE BASE RULES INTEGRATION
# =============================================================================

@router.get("/applicable-rules")
async def get_applicable_rules(platform: Optional[str] = None, content_type: Optional[str] = None):
    """Get KB rules applicable to current content planning."""
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            query = """
                SELECT id, rule_type, name, conditions, recommendation,
                       expected_lift, confidence, source_experiment_id
                FROM kb_rules
                WHERE status = 'active'
            """
            params = {}
            
            if platform:
                query += " AND (conditions->>'platform' IS NULL OR conditions->'platform' ? :platform)"
                params['platform'] = platform
            
            query += " ORDER BY confidence DESC, expected_lift DESC LIMIT 20"
            
            result = conn.execute(text(query), params).fetchall()
            
            rules = []
            for row in result:
                rules.append({
                    'id': str(row[0]),
                    'rule_type': row[1],
                    'name': row[2],
                    'conditions': row[3] or {},
                    'recommendation': row[4],
                    'expected_lift': float(row[5]) if row[5] else None,
                    'confidence': float(row[6]) if row[6] else None,
                    'source_experiment_id': str(row[7]) if row[7] else None
                })
            
            return {'rules': rules, 'count': len(rules)}
        except Exception as e:
            return {'rules': [], 'count': 0, 'error': str(e)}


# =============================================================================
# PHASE 3: TREND OPPORTUNITY INTEGRATION
# =============================================================================

@router.get("/trend-opportunities")
async def get_trend_opportunities_for_narrative():
    """Get trend opportunities relevant to mainline narrative."""
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                SELECT id, title, description, opportunity_score, relevance_to_brand,
                       content_fit, priority, window_start, window_end, recommended_actions,
                       matching_asset_ids
                FROM trend_opportunities
                WHERE status = 'new' AND window_end > NOW()
                AND relevance_to_brand >= 30
                ORDER BY opportunity_score DESC
                LIMIT 10
            """)).fetchall()
            
            opportunities = []
            for row in result:
                opportunities.append({
                    'id': str(row[0]),
                    'title': row[1],
                    'description': row[2],
                    'opportunity_score': float(row[3]) if row[3] else 0,
                    'relevance_to_brand': float(row[4]) if row[4] else 0,
                    'content_fit': float(row[5]) if row[5] else 0,
                    'priority': row[6],
                    'window': {
                        'start': row[7].isoformat() if row[7] else None,
                        'end': row[8].isoformat() if row[8] else None
                    },
                    'recommended_actions': row[9] or [],
                    'matching_assets': [str(a) for a in (row[10] or [])]
                })
            
            return {'opportunities': opportunities, 'count': len(opportunities)}
        except Exception as e:
            return {'opportunities': [], 'count': 0, 'error': str(e)}


@router.post("/schedule-from-plan")
async def schedule_from_plan(plan_items: List[Dict[str, Any]]):
    """Schedule posts from the 7-day plan to MAINLINE accounts."""
    engine = get_engine()
    scheduled = []
    
    with engine.connect() as conn:
        for item in plan_items:
            try:
                # Get a MAINLINE account for the platform
                account = conn.execute(text("""
                    SELECT id FROM social_accounts
                    WHERE platform = :platform AND account_role = 'MAINLINE' AND is_active = true
                    LIMIT 1
                """), {'platform': item.get('platform', 'tiktok')}).fetchone()
                
                if not account:
                    # Fallback to any active account
                    account = conn.execute(text("""
                        SELECT id FROM social_accounts
                        WHERE platform = :platform AND is_active = true
                        LIMIT 1
                    """), {'platform': item.get('platform', 'tiktok')}).fetchone()
                
                if account:
                    result = conn.execute(text("""
                        INSERT INTO scheduled_posts (
                            account_id, platform, content_id, caption, scheduled_at,
                            status, origin, goal_id
                        ) VALUES (
                            :account_id, :platform, :content_id, :caption, :scheduled_at,
                            'scheduled', 'NARRATIVE', :goal_id
                        )
                        RETURNING id
                    """), {
                        'account_id': account[0],
                        'platform': item.get('platform', 'tiktok'),
                        'content_id': item.get('content_id'),
                        'caption': item.get('caption', ''),
                        'scheduled_at': item.get('scheduled_at'),
                        'goal_id': item.get('goal_id')
                    })
                    
                    scheduled.append({
                        'post_id': str(result.fetchone()[0]),
                        'content_id': item.get('content_id'),
                        'platform': item.get('platform')
                    })
            except Exception as e:
                continue
        
        conn.commit()
    
    return {'scheduled': scheduled, 'count': len(scheduled)}


@router.get("/content-stats")
async def get_content_stats():
    """Get overall content statistics for the narrative builder."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Overall stats
        stats = conn.execute(text("""
            SELECT 
                COUNT(*) as total_analyzed,
                AVG(pre_social_score) as avg_score,
                COUNT(*) FILTER (WHERE curation_status = 'approved') as approved,
                COUNT(*) FILTER (WHERE pre_social_score >= 70) as high_performers
            FROM video_analysis
        """)).fetchone()
        
        # Scheduled stats
        scheduled_stats = conn.execute(text("""
            SELECT 
                COUNT(*) as total_scheduled,
                COUNT(*) FILTER (WHERE status = 'scheduled') as pending,
                COUNT(*) FILTER (WHERE status = 'posted') as posted,
                COUNT(DISTINCT content_id) as unique_content
            FROM scheduled_posts
        """)).fetchone()
        
        # Posted content performance
        performance = conn.execute(text("""
            SELECT 
                SUM(views) as total_views,
                SUM(likes) as total_likes,
                AVG(engagement_rate) as avg_engagement
            FROM posted_content
            WHERE views > 0
        """)).fetchone()
    
    return {
        'content': {
            'total_analyzed': stats[0] or 0,
            'avg_score': round(float(stats[1]), 1) if stats[1] else 0,
            'approved': stats[2] or 0,
            'high_performers': stats[3] or 0,
        },
        'scheduling': {
            'total_scheduled': scheduled_stats[0] or 0,
            'pending': scheduled_stats[1] or 0,
            'posted': scheduled_stats[2] or 0,
            'unique_content': scheduled_stats[3] or 0,
        },
        'performance': {
            'total_views': int(performance[0]) if performance[0] else 0,
            'total_likes': int(performance[1]) if performance[1] else 0,
            'avg_engagement': round(float(performance[2]) * 100, 2) if performance[2] else 0,
        }
    }
