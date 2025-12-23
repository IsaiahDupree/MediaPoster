"""
Seed Automation Data
=====================
Creates sample schedules, runs, steps, and events for testing the Automation Center UI.
"""

import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4
import json

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


def seed_data():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("🌱 Seeding automation test data...")
        
        # Clear existing test data
        conn.execute(text("DELETE FROM agent_events WHERE source_service LIKE '%Test%'"))
        conn.execute(text("DELETE FROM agent_artifacts WHERE kind LIKE 'test_%'"))
        conn.execute(text("DELETE FROM agent_steps WHERE run_id IN (SELECT id FROM agent_runs WHERE root_context_json->>'test' = 'true')"))
        conn.execute(text("DELETE FROM agent_runs WHERE root_context_json->>'test' = 'true'"))
        conn.execute(text("DELETE FROM agent_queue WHERE payload_json->>'test' = 'true'"))
        conn.commit()
        
        # =====================================================================
        # Create test runs with steps and events
        # =====================================================================
        
        # Run 1: Completed narrative run
        run1_id = str(uuid4())
        conn.execute(text("""
            INSERT INTO agent_runs (id, agent_type, status, progress_current, progress_total, 
                started_at, finished_at, root_context_json)
            VALUES (:id, 'narrative', 'succeeded', 5, 5, 
                :started, :finished, :context)
        """), {
            "id": run1_id,
            "started": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "finished": (datetime.utcnow() - timedelta(hours=1, minutes=45)).isoformat(),
            "context": json.dumps({"test": "true", "goal": "Weekly content plan"})
        })
        
        # Steps for run 1
        steps1 = [
            ("context_gathering", "Context Gathering", 1, "completed", "Loaded 3 pillars, 5 constraints"),
            ("content_analysis", "Content Analysis", 2, "completed", "Analyzed 400 videos, 122 match criteria"),
            ("selection_reasoning", "Selection Reasoning", 3, "completed", "Adjusted pillar mix based on learnings"),
            ("video_selection", "Video Selection", 4, "completed", "Selected 14 videos with justifications"),
            ("schedule_generation", "Schedule Generation", 5, "completed", "Created weekly schedule"),
        ]
        
        step_ids = {}
        for key, name, order, status, summary in steps1:
            step_id = str(uuid4())
            step_ids[key] = step_id
            conn.execute(text("""
                INSERT INTO agent_steps (id, run_id, step_key, step_name, step_order, status, 
                    started_at, finished_at, summary)
                VALUES (:id, :run_id, :key, :name, :order, :status, :started, :finished, :summary)
            """), {
                "id": step_id,
                "run_id": run1_id,
                "key": key,
                "name": name,
                "order": order,
                "status": status,
                "started": (datetime.utcnow() - timedelta(hours=2, minutes=order*3)).isoformat(),
                "finished": (datetime.utcnow() - timedelta(hours=2, minutes=order*3-2)).isoformat(),
                "summary": summary
            })
        
        # Events for run 1
        events1 = [
            (step_ids["context_gathering"], "thought.summary", "Goal is to optimize for CTA while keeping pillar mix within constraints."),
            (step_ids["context_gathering"], "data.fetched", "Loaded 3 pillars, 5 constraints, last 4 weeks performance"),
            (step_ids["content_analysis"], "action.performed", "Analyzing 400 available videos against pillars"),
            (step_ids["content_analysis"], "thought.summary", "Found 122 videos meeting quality threshold"),
            (step_ids["selection_reasoning"], "decision", "Increasing Process/How-To allocation from 35% to 45%"),
            (step_ids["video_selection"], "action.performed", "Selected 14 videos (2/day) with per-item justifications"),
            (step_ids["schedule_generation"], "artifact.created", "Created weekly_schedule.json"),
        ]
        
        for i, (step_id, event_type, message) in enumerate(events1):
            conn.execute(text("""
                INSERT INTO agent_events (id, run_id, step_id, topic, event_type, severity, 
                    source_service, message, ts)
                VALUES (:id, :run_id, :step_id, :topic, :event_type, 'info', 
                    'TestNarrativeService', :message, :ts)
            """), {
                "id": str(uuid4()),
                "run_id": run1_id,
                "step_id": step_id,
                "topic": f"narrative.{event_type}",
                "event_type": event_type,
                "message": message,
                "ts": (datetime.utcnow() - timedelta(hours=2, minutes=15-i)).isoformat()
            })
        
        # Run 2: Running experiments run
        run2_id = str(uuid4())
        conn.execute(text("""
            INSERT INTO agent_runs (id, agent_type, status, progress_current, progress_total, 
                started_at, root_context_json)
            VALUES (:id, 'experiments', 'running', 3, 5, :started, :context)
        """), {
            "id": run2_id,
            "started": (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
            "context": json.dumps({"test": "true", "experiment": "Question hooks"})
        })
        
        # Steps for run 2
        steps2 = [
            ("plan_experiments", "Plan Experiments", 1, "completed", "3 experiment opportunities identified"),
            ("create_hypotheses", "Create Hypotheses", 2, "completed", "Created 3 hypotheses"),
            ("generate_variants", "Build Variants", 3, "running", None),
            ("schedule_variants", "Schedule Variants", 4, "pending", None),
            ("analyze_results", "Analyze Results", 5, "pending", None),
        ]
        
        step_ids2 = {}
        for key, name, order, status, summary in steps2:
            step_id = str(uuid4())
            step_ids2[key] = step_id
            conn.execute(text("""
                INSERT INTO agent_steps (id, run_id, step_key, step_name, step_order, status, 
                    started_at, summary)
                VALUES (:id, :run_id, :key, :name, :order, :status, :started, :summary)
            """), {
                "id": step_id,
                "run_id": run2_id,
                "key": key,
                "name": name,
                "order": order,
                "status": status,
                "started": (datetime.utcnow() - timedelta(minutes=10-order)).isoformat() if status != "pending" else None,
                "summary": summary
            })
        
        # Events for run 2
        events2 = [
            (step_ids2["plan_experiments"], "thought.summary", "Selecting hypotheses that test high-leverage variables"),
            (step_ids2["create_hypotheses"], "action.performed", "Created 3 hypotheses: question-hook, 6pm timing, CTA placement"),
            (step_ids2["generate_variants"], "tool.call.requested", "Calling add_hook tool to generate variants"),
        ]
        
        for i, (step_id, event_type, message) in enumerate(events2):
            conn.execute(text("""
                INSERT INTO agent_events (id, run_id, step_id, topic, event_type, severity, 
                    source_service, message, ts)
                VALUES (:id, :run_id, :step_id, :topic, :event_type, 'info', 
                    'TestExperimentsService', :message, :ts)
            """), {
                "id": str(uuid4()),
                "run_id": run2_id,
                "step_id": step_id,
                "topic": f"experiments.{event_type}",
                "event_type": event_type,
                "message": message,
                "ts": (datetime.utcnow() - timedelta(minutes=8-i*2)).isoformat()
            })
        
        # Run 3: Failed run
        run3_id = str(uuid4())
        conn.execute(text("""
            INSERT INTO agent_runs (id, agent_type, status, progress_current, progress_total, 
                started_at, finished_at, error_message, root_context_json)
            VALUES (:id, 'narrative', 'failed', 2, 5, :started, :finished, :error, :context)
        """), {
            "id": run3_id,
            "started": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
            "finished": (datetime.utcnow() - timedelta(hours=4, minutes=55)).isoformat(),
            "error": "Failed to fetch content from API",
            "context": json.dumps({"test": "true"})
        })
        
        # Add error event
        conn.execute(text("""
            INSERT INTO agent_events (id, run_id, topic, event_type, severity, 
                source_service, message, ts)
            VALUES (:id, :run_id, 'shared.run.failed', 'error', 'error', 
                'TestNarrativeService', 'Failed to fetch content from API', :ts)
        """), {
            "id": str(uuid4()),
            "run_id": run3_id,
            "ts": (datetime.utcnow() - timedelta(hours=4, minutes=55)).isoformat()
        })
        
        # Run 4: Queued run
        run4_id = str(uuid4())
        conn.execute(text("""
            INSERT INTO agent_runs (id, agent_type, status, progress_current, progress_total, 
                root_context_json)
            VALUES (:id, 'experiments', 'queued', 0, 5, :context)
        """), {
            "id": run4_id,
            "context": json.dumps({"test": "true"})
        })
        
        conn.commit()
        
        print(f"✅ Created 4 test runs:")
        print(f"   - Run 1 (narrative/succeeded): {run1_id}")
        print(f"   - Run 2 (experiments/running): {run2_id}")
        print(f"   - Run 3 (narrative/failed): {run3_id}")
        print(f"   - Run 4 (experiments/queued): {run4_id}")
        print("✅ Seed data complete!")


if __name__ == "__main__":
    seed_data()
