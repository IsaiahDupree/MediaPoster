"""
RF-007: Touch Cadences
Structured recurring engagement system for relationship maintenance.
"""

import os
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


class CadenceType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class CadenceTask:
    """A single task in a cadence."""
    contact_id: str
    contact_name: str
    platform: str
    task_type: str  # story_reply, check_in, micro_win, curiosity, permissioned_offer
    priority: int  # 1-5
    health_score: int
    context: str
    suggested_message: Optional[str] = None


@dataclass
class DailyCadence:
    """Daily touch cadence - light engagement."""
    date: date
    story_replies: List[CadenceTask] = field(default_factory=list)  # Reply to stories
    hot_check_ins: List[CadenceTask] = field(default_factory=list)  # Check-ins for hot relationships


@dataclass
class WeeklyCadence:
    """Weekly touch cadence - structured outreach."""
    week_start: date
    micro_wins: List[CadenceTask] = field(default_factory=list)      # 10 people: resource/intro
    curiosity_questions: List[CadenceTask] = field(default_factory=list)  # 10 people: ask questions
    permissioned_offers: List[CadenceTask] = field(default_factory=list)  # 5 people: only if fit


@dataclass
class MonthlyCadence:
    """Monthly touch cadence - deep reconnection."""
    month: str  # YYYY-MM
    catch_up_messages: List[CadenceTask] = field(default_factory=list)  # Reflection/catch-up
    focus_questions: List[CadenceTask] = field(default_factory=list)    # "What are you focused on?"


@dataclass
class CadenceStats:
    """Statistics for cadence completion."""
    cadence_type: str
    period: str
    total_tasks: int
    completed_tasks: int
    completion_rate: float
    contacts_touched: int
    micro_wins_sent: int
    curiosity_questions: int
    permissioned_offers: int
    average_response_rate: float


class TouchCadenceManager:
    """
    Manages touch cadences for relationship maintenance.
    
    Philosophy: Consistent, genuine touches > sporadic bursts.
    """
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        logger.info("✅ TouchCadenceManager initialized")
    
    def generate_daily_cadence(self, user_id: str) -> DailyCadence:
        """
        Generate today's daily cadence.
        
        Daily (Light):
        - Reply to stories
        - "how's it going" check-ins for hot relationships (health > 70)
        """
        today = date.today()
        cadence = DailyCadence(date=today)
        
        try:
            with self.engine.connect() as conn:
                # Get contacts for story replies (recently active)
                result = conn.execute(text("""
                    SELECT id, username, display_name, platform, relationship_health,
                           building, struggles
                    FROM dm_contacts
                    WHERE user_id = :user_id
                    AND relationship_health >= 50
                    AND last_touch < NOW() - INTERVAL '1 day'
                    ORDER BY relationship_health DESC
                    LIMIT 10
                """), {"user_id": user_id})
                
                for row in result.mappings():
                    cadence.story_replies.append(CadenceTask(
                        contact_id=str(row["id"]),
                        contact_name=row["display_name"] or row["username"],
                        platform=row["platform"],
                        task_type="story_reply",
                        priority=3,
                        health_score=row["relationship_health"],
                        context=row["building"] or "No context yet"
                    ))
                
                # Get hot relationships for check-ins
                result = conn.execute(text("""
                    SELECT id, username, display_name, platform, relationship_health,
                           building, struggles, win_30d
                    FROM dm_contacts
                    WHERE user_id = :user_id
                    AND relationship_health >= 70
                    AND last_touch < NOW() - INTERVAL '2 days'
                    ORDER BY relationship_health DESC
                    LIMIT 5
                """), {"user_id": user_id})
                
                for row in result.mappings():
                    cadence.hot_check_ins.append(CadenceTask(
                        contact_id=str(row["id"]),
                        contact_name=row["display_name"] or row["username"],
                        platform=row["platform"],
                        task_type="check_in",
                        priority=4,
                        health_score=row["relationship_health"],
                        context=row["building"] or "",
                        suggested_message=f"how's {row['win_30d'] or 'everything'} going?"
                    ))
                    
        except Exception as e:
            logger.error(f"Failed to generate daily cadence: {e}")
        
        return cadence
    
    def generate_weekly_cadence(self, user_id: str) -> WeeklyCadence:
        """
        Generate this week's cadence.
        
        Weekly (Structured):
        - 10 people: Send a micro-win, resource, or intro
        - 10 people: Ask a curiosity question
        - 5 people: Permissioned offer (only if fit)
        """
        week_start = date.today() - timedelta(days=date.today().weekday())
        cadence = WeeklyCadence(week_start=week_start)
        
        try:
            with self.engine.connect() as conn:
                # Micro-wins: People with known struggles (health 50-80)
                result = conn.execute(text("""
                    SELECT id, username, display_name, platform, relationship_health,
                           building, struggles, pipeline_stage
                    FROM dm_contacts
                    WHERE user_id = :user_id
                    AND relationship_health BETWEEN 50 AND 80
                    AND struggles IS NOT NULL AND struggles != ''
                    ORDER BY relationship_health DESC
                    LIMIT 10
                """), {"user_id": user_id})
                
                for row in result.mappings():
                    cadence.micro_wins.append(CadenceTask(
                        contact_id=str(row["id"]),
                        contact_name=row["display_name"] or row["username"],
                        platform=row["platform"],
                        task_type="micro_win",
                        priority=4,
                        health_score=row["relationship_health"],
                        context=row["struggles"],
                        suggested_message=f"if i send you a quick template for {row['struggles'][:50]}..., would it help?"
                    ))
                
                # Curiosity questions: Need more context (low need_clarity)
                result = conn.execute(text("""
                    SELECT id, username, display_name, platform, relationship_health,
                           building, struggles
                    FROM dm_contacts
                    WHERE user_id = :user_id
                    AND relationship_health >= 40
                    AND (building IS NULL OR building = '' OR struggles IS NULL OR struggles = '')
                    ORDER BY relationship_health DESC
                    LIMIT 10
                """), {"user_id": user_id})
                
                for row in result.mappings():
                    cadence.curiosity_questions.append(CadenceTask(
                        contact_id=str(row["id"]),
                        contact_name=row["display_name"] or row["username"],
                        platform=row["platform"],
                        task_type="curiosity",
                        priority=3,
                        health_score=row["relationship_health"],
                        context="Need to learn more about them",
                        suggested_message="what are you optimizing for right now?"
                    ))
                
                # Permissioned offers: High health + fit_identified stage
                result = conn.execute(text("""
                    SELECT id, username, display_name, platform, relationship_health,
                           building, struggles, pipeline_stage
                    FROM dm_contacts
                    WHERE user_id = :user_id
                    AND relationship_health >= 70
                    AND pipeline_stage IN ('fit_identified', 'trust_signals')
                    ORDER BY relationship_health DESC
                    LIMIT 5
                """), {"user_id": user_id})
                
                for row in result.mappings():
                    cadence.permissioned_offers.append(CadenceTask(
                        contact_id=str(row["id"]),
                        contact_name=row["display_name"] or row["username"],
                        platform=row["platform"],
                        task_type="permissioned_offer",
                        priority=5,
                        health_score=row["relationship_health"],
                        context=row["struggles"] or row["building"] or "",
                        suggested_message="want me to show you a simple way i solve that? no pressure."
                    ))
                    
        except Exception as e:
            logger.error(f"Failed to generate weekly cadence: {e}")
        
        return cadence
    
    def generate_monthly_cadence(self, user_id: str) -> MonthlyCadence:
        """
        Generate this month's deep reconnection cadence.
        
        Monthly (Deep):
        - "Catch-up / reflection" messages
        - Ask: "what are you focused on next month?"
        """
        month = date.today().strftime("%Y-%m")
        cadence = MonthlyCadence(month=month)
        
        try:
            with self.engine.connect() as conn:
                # Catch-up: Haven't touched in 2+ weeks
                result = conn.execute(text("""
                    SELECT id, username, display_name, platform, relationship_health,
                           building, struggles, win_30d
                    FROM dm_contacts
                    WHERE user_id = :user_id
                    AND last_touch < NOW() - INTERVAL '14 days'
                    AND relationship_health >= 30
                    ORDER BY relationship_health DESC
                    LIMIT 20
                """), {"user_id": user_id})
                
                for row in result.mappings():
                    cadence.catch_up_messages.append(CadenceTask(
                        contact_id=str(row["id"]),
                        contact_name=row["display_name"] or row["username"],
                        platform=row["platform"],
                        task_type="catch_up",
                        priority=2,
                        health_score=row["relationship_health"],
                        context=row["building"] or "",
                        suggested_message=f"been a minute! hope {row['building'] or 'things'} is going well."
                    ))
                
                # Focus questions for active relationships
                result = conn.execute(text("""
                    SELECT id, username, display_name, platform, relationship_health,
                           building
                    FROM dm_contacts
                    WHERE user_id = :user_id
                    AND relationship_health >= 60
                    ORDER BY last_touch DESC
                    LIMIT 15
                """), {"user_id": user_id})
                
                for row in result.mappings():
                    cadence.focus_questions.append(CadenceTask(
                        contact_id=str(row["id"]),
                        contact_name=row["display_name"] or row["username"],
                        platform=row["platform"],
                        task_type="focus_question",
                        priority=2,
                        health_score=row["relationship_health"],
                        context=row["building"] or "",
                        suggested_message="what are you focused on next month?"
                    ))
                    
        except Exception as e:
            logger.error(f"Failed to generate monthly cadence: {e}")
        
        return cadence
    
    def mark_task_complete(
        self,
        user_id: str,
        contact_id: str,
        task_type: str,
        outcome: str = "completed"
    ) -> bool:
        """Mark a cadence task as complete."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO dm_touch_cadence 
                    (user_id, cadence_type, scheduled_date, completed, contacts_touched)
                    VALUES (:user_id, :task_type, :today, true, 1)
                    ON CONFLICT DO NOTHING
                """), {
                    "user_id": user_id,
                    "task_type": task_type,
                    "today": date.today()
                })
                
                # Update contact's last touch
                conn.execute(text("""
                    UPDATE dm_contacts
                    SET last_touch = NOW()
                    WHERE id = :contact_id
                """), {"contact_id": contact_id})
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to mark task complete: {e}")
            return False
    
    def get_today_summary(self, user_id: str) -> Dict:
        """Get summary of today's cadence tasks."""
        daily = self.generate_daily_cadence(user_id)
        weekly = self.generate_weekly_cadence(user_id)
        
        return {
            "date": str(date.today()),
            "daily": {
                "story_replies": len(daily.story_replies),
                "hot_check_ins": len(daily.hot_check_ins),
                "total": len(daily.story_replies) + len(daily.hot_check_ins)
            },
            "weekly": {
                "micro_wins": len(weekly.micro_wins),
                "curiosity_questions": len(weekly.curiosity_questions),
                "permissioned_offers": len(weekly.permissioned_offers),
                "total": len(weekly.micro_wins) + len(weekly.curiosity_questions) + len(weekly.permissioned_offers)
            },
            "priority_contacts": [
                {
                    "name": t.contact_name,
                    "platform": t.platform,
                    "task": t.task_type,
                    "health": t.health_score,
                    "message": t.suggested_message
                }
                for t in sorted(
                    daily.hot_check_ins + weekly.permissioned_offers,
                    key=lambda x: x.priority,
                    reverse=True
                )[:5]
            ]
        }
