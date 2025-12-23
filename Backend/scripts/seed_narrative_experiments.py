#!/usr/bin/env python3
"""
Seed Script: Narrative Builder & Experiments Demo Data
=======================================================
Seeds the database with comprehensive demo data for testing:
- Social accounts with MAINLINE and EXPERIMENT_ARM roles
- KB rules from experiment learnings
- Narrative goals for content strategy
- Trend opportunities
- Scheduled posts with origin tracking

Usage:
    python scripts/seed_narrative_experiments.py
"""

import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


def get_engine():
    return create_engine(DATABASE_URL)


def seed_account_roles(conn):
    """Assign account roles to social accounts."""
    print("🔧 Setting up account roles...")
    
    try:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'social_accounts' AND column_name = 'account_role'
        """))
        if not result.fetchone():
            print("⚠️ account_role column doesn't exist yet. Run migration first:")
            print("   supabase db push")
            print("   Skipping account role setup...")
            return
        
        # Set most accounts to MAINLINE, a few to EXPERIMENT_ARM
        conn.execute(text("""
            UPDATE social_accounts 
            SET account_role = 'MAINLINE' 
            WHERE account_role IS NULL OR account_role = ''
        """))
        
        # Mark specific accounts as EXPERIMENT_ARM (use lower-follower accounts for testing)
        conn.execute(text("""
            UPDATE social_accounts 
            SET account_role = 'EXPERIMENT_ARM' 
            WHERE id IN (
                SELECT id FROM social_accounts 
                ORDER BY RANDOM() 
                LIMIT 2
            )
        """))
        
        conn.commit()
        print("✅ Account roles configured")
    except Exception as e:
        print(f"⚠️ Could not set account roles: {e}")


def seed_kb_rules(conn):
    """Seed Knowledge Base rules from experiment learnings."""
    print("📚 Seeding KB rules...")
    
    try:
        # Check if table exists
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'kb_rules'
        """))
        if not result.fetchone():
            print("⚠️ kb_rules table doesn't exist yet. Run migration first.")
            return
    except:
        pass
    
    rules = [
        {
            "rule_type": "hook",
            "name": "Pain Point Cold Open",
            "description": "Start with a specific pain point question",
            "conditions": {"platform": ["tiktok", "instagram"], "format": ["vertical"]},
            "recommendation": "Use 'Are you still struggling with...' or 'Stop doing X...' opening hooks",
            "expected_lift": 34.0,
            "confidence": 0.95,
            "sample_size": 25000,
        },
        {
            "rule_type": "hook",
            "name": "Question Hook Pattern",
            "description": "Start with a direct question to audience",
            "conditions": {"platform": ["tiktok", "instagram", "youtube"], "content_pillar": ["education"]},
            "recommendation": "Ask a specific question that your audience is asking themselves",
            "expected_lift": 28.0,
            "confidence": 0.92,
            "sample_size": 18000,
        },
        {
            "rule_type": "caption",
            "name": "Short Caption Performance",
            "description": "Shorter captions perform better for engagement",
            "conditions": {"platform": ["tiktok", "instagram"]},
            "recommendation": "Keep captions under 100 characters, focus on one key message",
            "expected_lift": 52.0,
            "confidence": 0.98,
            "sample_size": 30000,
        },
        {
            "rule_type": "cta",
            "name": "Comment Keyword CTA",
            "description": "Comment keyword CTAs drive more engagement than link CTAs",
            "conditions": {"platform": ["tiktok", "instagram"]},
            "recommendation": "Use 'Comment [KEYWORD] for...' instead of 'Link in bio'",
            "expected_lift": 133.0,
            "confidence": 0.96,
            "sample_size": 22000,
        },
        {
            "rule_type": "timing",
            "name": "Evening Prime Time",
            "description": "Evening posts (6-9PM) get higher engagement",
            "conditions": {"platform": ["tiktok", "instagram", "youtube"]},
            "recommendation": "Schedule primary content between 6PM-9PM local time",
            "expected_lift": 18.0,
            "confidence": 0.89,
            "sample_size": 50000,
        },
        {
            "rule_type": "format",
            "name": "15-30s Optimal Length",
            "description": "Videos 15-30 seconds have highest completion rate",
            "conditions": {"platform": ["tiktok", "instagram"], "content_type": ["tips", "hacks"]},
            "recommendation": "Keep tip/hack content between 15-30 seconds for optimal completion",
            "expected_lift": 22.0,
            "confidence": 0.94,
            "sample_size": 35000,
        },
        {
            "rule_type": "thumbnail",
            "name": "Face Forward Thumbnail",
            "description": "Thumbnails with faces get higher CTR",
            "conditions": {"platform": ["youtube"]},
            "recommendation": "Include an expressive face in thumbnail, looking at camera",
            "expected_lift": 15.0,
            "confidence": 0.88,
            "sample_size": 15000,
        },
    ]
    
    for rule in rules:
        conn.execute(text("""
            INSERT INTO kb_rules (
                id, rule_type, name, description, conditions, recommendation,
                expected_lift, confidence, sample_size, status, created_at
            ) VALUES (
                :id, :rule_type, :name, :description, :conditions::jsonb, :recommendation,
                :expected_lift, :confidence, :sample_size, 'active', NOW()
            ) ON CONFLICT DO NOTHING
        """), {
            "id": str(uuid4()),
            "rule_type": rule["rule_type"],
            "name": rule["name"],
            "description": rule["description"],
            "conditions": str(rule["conditions"]).replace("'", '"'),
            "recommendation": rule["recommendation"],
            "expected_lift": rule["expected_lift"],
            "confidence": rule["confidence"],
            "sample_size": rule["sample_size"],
        })
    
    conn.commit()
    print(f"✅ Seeded {len(rules)} KB rules")


def seed_narrative_goals(conn):
    """Seed narrative goals for content strategy."""
    print("🎯 Seeding narrative goals...")
    
    try:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'narrative_goals'
        """))
        if not result.fetchone():
            print("⚠️ narrative_goals table doesn't exist yet. Run migration first.")
            return
    except:
        pass
    
    goals = [
        {
            "name": "Q1 Follower Growth",
            "description": "Grow follower count by 50% through educational content",
            "goal_type": "growth",
            "target_metric": "followers",
            "target_value": 15000,
            "current_value": 10000,
            "content_pillars": ["education", "proof", "pain"],
            "platform_mix": {"tiktok": 0.5, "instagram": 0.3, "youtube": 0.2},
            "posting_cadence": {"min_per_day": 1, "max_per_day": 3, "target_per_day": 2},
            "priority": 90,
            "progress_percent": 33.3,
        },
        {
            "name": "Course Waitlist Campaign",
            "description": "Drive 500 signups to course waitlist over 30 days",
            "goal_type": "campaign",
            "target_metric": "waitlist_signups",
            "target_value": 500,
            "current_value": 125,
            "content_pillars": ["proof", "process", "product"],
            "platform_mix": {"tiktok": 0.4, "instagram": 0.4, "youtube": 0.2},
            "posting_cadence": {"min_per_day": 2, "max_per_day": 4, "target_per_day": 3},
            "priority": 85,
            "progress_percent": 25.0,
        },
        {
            "name": "Authority Building Series",
            "description": "Establish expertise through educational deep-dives",
            "goal_type": "series",
            "target_metric": "engagement_rate",
            "target_value": 8.0,
            "current_value": 5.2,
            "content_pillars": ["education", "personality", "process"],
            "platform_mix": {"youtube": 0.5, "tiktok": 0.3, "instagram": 0.2},
            "posting_cadence": {"min_per_day": 1, "max_per_day": 2, "target_per_day": 1},
            "priority": 70,
            "progress_percent": 65.0,
        },
    ]
    
    for goal in goals:
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=30)
        
        conn.execute(text("""
            INSERT INTO narrative_goals (
                id, name, description, goal_type, target_metric, target_value, current_value,
                content_pillars, platform_mix, posting_cadence, priority, progress_percent,
                start_date, end_date, status, created_at
            ) VALUES (
                :id, :name, :description, :goal_type, :target_metric, :target_value, :current_value,
                :content_pillars::jsonb, :platform_mix::jsonb, :posting_cadence::jsonb, :priority, :progress_percent,
                :start_date, :end_date, 'active', NOW()
            ) ON CONFLICT DO NOTHING
        """), {
            "id": str(uuid4()),
            "name": goal["name"],
            "description": goal["description"],
            "goal_type": goal["goal_type"],
            "target_metric": goal["target_metric"],
            "target_value": goal["target_value"],
            "current_value": goal["current_value"],
            "content_pillars": str(goal["content_pillars"]).replace("'", '"'),
            "platform_mix": str(goal["platform_mix"]).replace("'", '"'),
            "posting_cadence": str(goal["posting_cadence"]).replace("'", '"'),
            "priority": goal["priority"],
            "progress_percent": goal["progress_percent"],
            "start_date": start_date,
            "end_date": end_date,
        })
    
    conn.commit()
    print(f"✅ Seeded {len(goals)} narrative goals")


def seed_trend_opportunities(conn):
    """Seed trend opportunities for reactive content."""
    print("📈 Seeding trend opportunities...")
    
    try:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'trend_opportunities'
        """))
        if not result.fetchone():
            print("⚠️ trend_opportunities table doesn't exist yet. Run migration first.")
            return
    except:
        pass
    
    trends = [
        {
            "title": "Viral Sound: 'POV you finally...'",
            "description": "Sound trending in education/tutorial niche with 50M+ views",
            "opportunity_score": 92,
            "relevance_to_brand": 85,
            "content_fit": 90,
            "priority": "high",
            "window_hours": 48,
            "recommended_actions": ["Create tutorial video using sound", "Film POV transformation"],
        },
        {
            "title": "Format: Split Screen Comparisons",
            "description": "Before/after split screen format trending across platforms",
            "opportunity_score": 78,
            "relevance_to_brand": 80,
            "content_fit": 85,
            "priority": "medium",
            "window_hours": 168,
            "recommended_actions": ["Show skill progression", "Compare beginner vs expert"],
        },
        {
            "title": "Topic: AI Tools for Creators",
            "description": "Surge in interest for AI productivity tools",
            "opportunity_score": 85,
            "relevance_to_brand": 70,
            "content_fit": 75,
            "priority": "high",
            "window_hours": 72,
            "recommended_actions": ["Review new AI tool", "Share workflow integration"],
        },
        {
            "title": "Challenge: 30-Second Tutorial",
            "description": "Creators condensing tutorials into 30 seconds",
            "opportunity_score": 72,
            "relevance_to_brand": 90,
            "content_fit": 95,
            "priority": "medium",
            "window_hours": 120,
            "recommended_actions": ["Create speed tutorial", "Show quick hack"],
        },
    ]
    
    for trend in trends:
        window_start = datetime.now()
        window_end = window_start + timedelta(hours=trend["window_hours"])
        
        conn.execute(text("""
            INSERT INTO trend_opportunities (
                id, title, description, opportunity_score, relevance_to_brand, content_fit,
                priority, window_start, window_end, recommended_actions, status, created_at
            ) VALUES (
                :id, :title, :description, :opportunity_score, :relevance_to_brand, :content_fit,
                :priority, :window_start, :window_end, :recommended_actions::jsonb, 'active', NOW()
            ) ON CONFLICT DO NOTHING
        """), {
            "id": str(uuid4()),
            "title": trend["title"],
            "description": trend["description"],
            "opportunity_score": trend["opportunity_score"],
            "relevance_to_brand": trend["relevance_to_brand"],
            "content_fit": trend["content_fit"],
            "priority": trend["priority"],
            "window_start": window_start,
            "window_end": window_end,
            "recommended_actions": str(trend["recommended_actions"]).replace("'", '"'),
        })
    
    conn.commit()
    print(f"✅ Seeded {len(trends)} trend opportunities")


def seed_scheduled_posts_with_origin(conn):
    """Seed scheduled posts with origin tracking."""
    print("📅 Seeding scheduled posts with origin tracking...")
    
    # Get existing accounts
    result = conn.execute(text("""
        SELECT id, platform, handle, account_role FROM social_accounts LIMIT 10
    """))
    accounts = result.fetchall()
    
    if not accounts:
        print("⚠️ No social accounts found, skipping scheduled posts")
        return
    
    mainline_accounts = [a for a in accounts if a[3] == 'MAINLINE']
    experiment_accounts = [a for a in accounts if a[3] == 'EXPERIMENT_ARM']
    
    # Seed NARRATIVE posts (from Narrative Builder)
    for i in range(5):
        if mainline_accounts:
            account = random.choice(mainline_accounts)
            scheduled_at = datetime.now() + timedelta(days=i+1, hours=random.randint(9, 20))
            
            conn.execute(text("""
                INSERT INTO scheduled_posts (
                    id, account_id, platform, caption, scheduled_at, status, origin, created_at
                ) VALUES (
                    :id, :account_id, :platform, :caption, :scheduled_at, 'scheduled', 'NARRATIVE', NOW()
                ) ON CONFLICT DO NOTHING
            """), {
                "id": str(uuid4()),
                "account_id": str(account[0]),
                "platform": account[1],
                "caption": f"[Narrative Builder] Educational content #{i+1} - Pain point hook approach 🎯",
                "scheduled_at": scheduled_at,
            })
    
    # Seed EXPERIMENT posts (from A/B Tests)
    for i in range(3):
        if experiment_accounts:
            account = random.choice(experiment_accounts)
            scheduled_at = datetime.now() + timedelta(days=i+1, hours=random.randint(9, 20))
            
            conn.execute(text("""
                INSERT INTO scheduled_posts (
                    id, account_id, platform, caption, scheduled_at, status, origin, experiment_arm, created_at
                ) VALUES (
                    :id, :account_id, :platform, :caption, :scheduled_at, 'scheduled', 'EXPERIMENT', :arm, NOW()
                ) ON CONFLICT DO NOTHING
            """), {
                "id": str(uuid4()),
                "account_id": str(account[0]),
                "platform": account[1],
                "caption": f"[Experiment] Testing hook variant {chr(65+i)} 🧪",
                "scheduled_at": scheduled_at,
                "arm": f"variant_{chr(97+i)}",
            })
    
    # Seed MANUAL posts
    for i in range(2):
        if mainline_accounts:
            account = random.choice(mainline_accounts)
            scheduled_at = datetime.now() + timedelta(days=i+2, hours=random.randint(9, 20))
            
            conn.execute(text("""
                INSERT INTO scheduled_posts (
                    id, account_id, platform, caption, scheduled_at, status, origin, created_at
                ) VALUES (
                    :id, :account_id, :platform, :caption, :scheduled_at, 'scheduled', 'MANUAL', NOW()
                ) ON CONFLICT DO NOTHING
            """), {
                "id": str(uuid4()),
                "account_id": str(account[0]),
                "platform": account[1],
                "caption": f"[Manual] One-off promotional post #{i+1} ✋",
                "scheduled_at": scheduled_at,
            })
    
    conn.commit()
    print("✅ Seeded scheduled posts with origin tracking")


def main():
    """Run all seed functions."""
    print("\n" + "="*60)
    print("🌱 SEEDING NARRATIVE BUILDER & EXPERIMENTS DEMO DATA")
    print("="*60 + "\n")
    
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            seed_account_roles(conn)
            seed_kb_rules(conn)
            seed_narrative_goals(conn)
            seed_trend_opportunities(conn)
            seed_scheduled_posts_with_origin(conn)
            
            print("\n" + "="*60)
            print("✅ ALL DEMO DATA SEEDED SUCCESSFULLY!")
            print("="*60)
            print("\nYou can now:")
            print("  1. View goals: GET /api/narrative-builder/goals")
            print("  2. Generate 7-day plan: GET /api/narrative-builder/plan/7-day")
            print("  3. View KB rules: GET /api/kb/rules")
            print("  4. View trends: GET /api/trends/opportunities")
            print("  5. View calendar by origin: GET /api/calendar/posts/by-origin")
            print("  6. View calendar stats: GET /api/calendar/stats/by-origin")
            print()
            
        except Exception as e:
            print(f"\n❌ Error seeding data: {e}")
            raise


if __name__ == "__main__":
    main()
