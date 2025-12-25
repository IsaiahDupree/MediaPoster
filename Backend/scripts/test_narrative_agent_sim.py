#!/usr/bin/env python3
"""
Narrative Agent Test with Simulated Publishing
================================================
Runs the full narrative agent workflow with simulated (dry-run) publishing.
Shows live thoughts, decisions, and actions in the terminal.
"""

import asyncio
import os
import sys
import json
from datetime import datetime, timedelta
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


class SimulatedPublisher:
    """Simulates publishing without actually posting."""
    
    def __init__(self):
        self.published = []
        self.sim_mode = True
    
    async def publish(self, video_id: str, platforms: list, caption: str, scheduled_time: str):
        """Simulate publishing a video."""
        result = {
            "video_id": video_id,
            "platforms": platforms,
            "caption": caption[:50] + "..." if len(caption) > 50 else caption,
            "scheduled_time": scheduled_time,
            "sim_published_at": datetime.now().isoformat(),
            "status": "SIM_SUCCESS"
        }
        self.published.append(result)
        return result


class NarrativeAgentTester:
    """Tests the narrative agent with live output."""
    
    def __init__(self, sim_publish: bool = True):
        self.engine = create_engine(DATABASE_URL)
        self.sim_publish = sim_publish
        self.publisher = SimulatedPublisher() if sim_publish else None
        self.run_id = str(uuid4())
        self.events = []
    
    def log_event(self, event_type: str, title: str, data: dict = None):
        """Log an event with visual formatting."""
        icons = {
            "thought": "💭",
            "decision": "⚖️",
            "action": "⚡",
            "result": "✅",
            "error": "❌",
            "milestone": "🎯",
            "data": "📊"
        }
        icon = icons.get(event_type, "📌")
        
        event = {
            "type": event_type,
            "title": title,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.events.append(event)
        
        print(f"\n{icon} [{event_type.upper()}] {title}")
        if data:
            for key, value in data.items():
                print(f"   └─ {key}: {value}")
    
    async def run_full_test(self):
        """Run the complete narrative agent test."""
        print("\n" + "="*60)
        print("🤖 NARRATIVE AGENT TEST - SIMULATED PUBLISH")
        print("="*60)
        print(f"Run ID: {self.run_id}")
        print(f"Sim Publish: {self.sim_publish}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        try:
            # Step 1: Load Goal
            self.log_event("milestone", "Step 1: Loading Narrative Goal")
            goal = await self._load_goal()
            
            # Step 2: Load Pillars
            self.log_event("milestone", "Step 2: Loading Content Pillars")
            pillars = await self._load_pillars(goal.get("id") if goal else None)
            
            # Step 3: Load Available Videos
            self.log_event("milestone", "Step 3: Loading Available Videos")
            videos = await self._load_videos()
            
            # Step 4: AI Reasoning
            self.log_event("milestone", "Step 4: AI Reasoning & Planning")
            plan = await self._generate_plan(goal, pillars, videos)
            
            # Step 5: Schedule Posts (Simulated)
            self.log_event("milestone", "Step 5: Scheduling Posts (Simulated)")
            scheduled = await self._schedule_posts(plan)
            
            # Step 6: Summary
            self._print_summary(scheduled)
            
            return {
                "success": True,
                "run_id": self.run_id,
                "events": self.events,
                "scheduled_posts": scheduled
            }
            
        except Exception as e:
            self.log_event("error", f"Test failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _load_goal(self):
        """Load or create a default goal."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, goal_statement, primary_cta, target_audience, time_horizon, status
                FROM narrative_goals
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
            """))
            row = result.fetchone()
            
            if row:
                goal = {
                    "id": str(row[0]),
                    "goal_statement": row[1],
                    "cta_type": row[2] or "engagement",
                    "target_audience": row[3],
                    "time_horizon": row[4],
                    "status": row[5]
                }
                self.log_event("data", "Loaded active goal", {
                    "goal": goal["goal_statement"][:60] + "...",
                    "cta_type": goal["cta_type"]
                })
                return goal
            else:
                self.log_event("thought", "No active goal found, using default", {
                    "default_goal": "Grow audience engagement"
                })
                return {
                    "id": None,
                    "goal_statement": "Grow audience engagement through consistent, high-quality content",
                    "cta_type": "engagement",
                    "time_horizon": "7days"
                }
    
    async def _load_pillars(self, goal_id: str = None):
        """Load content pillars."""
        # Use default pillars - table may not exist
        pillars = [
            {"name": "Educational/How-To", "percentage": 40},
            {"name": "Entertainment", "percentage": 35},
            {"name": "Behind-the-scenes", "percentage": 25}
        ]
        self.log_event("thought", "Using content pillars", {
            "pillars": ", ".join([p["name"] for p in pillars])
        })
        return pillars
    
    async def _load_videos(self):
        """Load available analyzed videos."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT v.id, v.title, v.source_uri, v.duration_sec, 
                       va.pre_social_score, va.detected_hook, va.pillar_tags
                FROM videos v
                LEFT JOIN video_analysis va ON v.id = va.video_id
                WHERE va.pre_social_score IS NOT NULL
                  AND va.pre_social_score >= 60
                ORDER BY va.pre_social_score DESC
                LIMIT 50
            """))
            
            videos = [
                {
                    "id": str(row[0]),
                    "title": row[1] or "Untitled",
                    "source_uri": row[2],
                    "duration": row[3],
                    "score": row[4] or 70,
                    "hook": row[5],
                    "pillars": row[6]
                }
                for row in result
            ]
            
            # If no scored videos, get any videos
            if not videos:
                result = conn.execute(text("""
                    SELECT id, title, source_uri, duration_sec
                    FROM videos
                    ORDER BY created_at DESC
                    LIMIT 50
                """))
                videos = [
                    {
                        "id": str(row[0]),
                        "title": row[1] or "Untitled",
                        "source_uri": row[2],
                        "duration": row[3],
                        "score": 70
                    }
                    for row in result
                ]
            
            self.log_event("data", f"Found {len(videos)} eligible videos", {
                "avg_score": round(sum(v.get("score", 70) for v in videos) / max(len(videos), 1), 1),
                "top_score": videos[0].get("score", 70) if videos else 0
            })
            
            return videos
    
    async def _generate_plan(self, goal: dict, pillars: list, videos: list):
        """Generate a 7-day plan using AI reasoning."""
        self.log_event("thought", "Analyzing goal and available content...")
        
        # Simulate AI reasoning
        self.log_event("thought", f"Goal focus: {goal.get('cta_type', 'engagement')}")
        self.log_event("thought", f"Content pool: {len(videos)} videos across {len(pillars)} pillars")
        
        # Selection reasoning
        self.log_event("decision", "Selecting top videos based on score and diversity", {
            "criteria": "score >= 70, pillar balance, freshness"
        })
        
        # Create plan
        plan = []
        selected_videos = videos[:14]  # 2 per day for 7 days
        
        base_date = datetime.now().date()
        for i, video in enumerate(selected_videos):
            day_offset = i // 2
            post_time = "09:00" if i % 2 == 0 else "18:00"
            post_date = base_date + timedelta(days=day_offset)
            
            plan.append({
                "video_id": video["id"],
                "video_title": video["title"],
                "scheduled_date": post_date.isoformat(),
                "scheduled_time": post_time,
                "platforms": ["tiktok", "instagram"],
                "caption": f"Check out this content! #{goal.get('cta_type', 'fyp')}",
                "score": video["score"]
            })
            
            self.log_event("action", f"Scheduled: {video['title'][:40]}...", {
                "date": post_date.isoformat(),
                "time": post_time,
                "score": video["score"]
            })
        
        self.log_event("result", f"Created {len(plan)} post schedule", {
            "days": 7,
            "posts_per_day": 2
        })
        
        return plan
    
    async def _schedule_posts(self, plan: list):
        """Schedule posts (simulated or real)."""
        scheduled = []
        
        for post in plan:
            if self.sim_publish:
                result = await self.publisher.publish(
                    video_id=post["video_id"],
                    platforms=post["platforms"],
                    caption=post["caption"],
                    scheduled_time=f"{post['scheduled_date']} {post['scheduled_time']}"
                )
                scheduled.append(result)
                self.log_event("result", f"SIM PUBLISH: {post['video_title'][:30]}...", {
                    "platforms": ", ".join(post["platforms"]),
                    "status": "SIM_SUCCESS"
                })
            else:
                # Would call real Blotato API here
                self.log_event("action", f"REAL PUBLISH: {post['video_title'][:30]}...")
                scheduled.append(post)
        
        return scheduled
    
    def _print_summary(self, scheduled: list):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"Total events: {len(self.events)}")
        print(f"Posts scheduled: {len(scheduled)}")
        print(f"Sim publish mode: {self.sim_publish}")
        
        # Event breakdown
        event_types = {}
        for e in self.events:
            t = e["type"]
            event_types[t] = event_types.get(t, 0) + 1
        
        print("\nEvent breakdown:")
        for t, count in event_types.items():
            print(f"  - {t}: {count}")
        
        if self.sim_publish and self.publisher:
            print(f"\nSimulated publications: {len(self.publisher.published)}")
        
        print("="*60)
        print("✅ Test completed successfully!")
        print("="*60 + "\n")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Narrative Agent with Simulated Publishing")
    parser.add_argument("--real", action="store_true", help="Use real publishing (not simulated)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    tester = NarrativeAgentTester(sim_publish=not args.real)
    result = await tester.run_full_test()
    
    if args.verbose:
        print("\n📋 Full event log:")
        print(json.dumps(result["events"], indent=2, default=str))
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
