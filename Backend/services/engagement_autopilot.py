"""
Engagement Autopilot
=====================
AI-powered engagement automation across all accounts.

Components:
1. CommentMonitor      — Fetches & classifies new comments on your posts
2. AIResponseEngine    — GPT-powered contextual reply generation
3. ProactiveEngine     — Like/comment on niche-relevant content
4. RateLimiter         — Human-like delays & daily caps
5. SafetyGuardrails    — Never engage inappropriately

Modes:
- full_auto:  Everything runs automatically
- reply_only: Only auto-reply to own post comments
- assist:     AI drafts, human approves
- monitor:    Collect data, no actions
- off:        Disabled

Usage:
    autopilot = EngagementAutopilot()
    
    # Generate AI replies for new comments
    replies = await autopilot.generate_comment_replies(account_id="710", platform="tiktok")
    
    # Run a proactive engagement session
    session = await autopilot.run_engagement_session(platform="tiktok", duration_minutes=20)
    
    # Get engagement stats
    stats = await autopilot.get_stats(period_days=7)
"""

import os
import json
import uuid
import random
import asyncio
from datetime import datetime, timedelta, timezone, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from loguru import logger


# ─── Rate Limits ─────────────────────────────────────────────────────────────

DAILY_LIMITS = {
    "tiktok":    {"likes": 100, "comments": 30, "follows": 20, "dms": 10, "replies": 50},
    "instagram": {"likes": 80,  "comments": 25, "follows": 15, "dms": 10, "replies": 40},
    "twitter":   {"likes": 100, "comments": 50, "follows": 25, "dms": 20, "replies": 50},
    "threads":   {"likes": 60,  "comments": 20, "follows": 10, "dms": 5,  "replies": 30},
    "youtube":   {"likes": 50,  "comments": 20, "follows": 0,  "dms": 0,  "replies": 30},
}

HUMANIZER_CONFIG = {
    "min_delay_seconds": 30,
    "max_delay_seconds": 300,
    "session_duration_minutes": 20,
    "sessions_per_day": 4,
    "typing_speed_cps": 5,
}

SAFETY_NEVER_REPLY = ["hate_speech", "spam", "scam", "explicit"]
SAFETY_GUIDELINES = {
    "never_mention": ["politics", "religion", "controversy"],
    "always_positive": True,
    "max_reply_length": 200,
    "never_argue": True,
}

# Default engagement mode per account
DEFAULT_MODE = "assist"  # Safe default: AI drafts, human approves


class EngagementAutopilot:
    """AI-powered engagement automation."""

    def __init__(self):
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres",
        )
        self._mode = DEFAULT_MODE

    # ═══════════════════════════════════════════════════════════════════════
    # 1. COMMENT MONITOR — Classify & queue replies
    # ═══════════════════════════════════════════════════════════════════════

    async def classify_comment(
        self, comment_text: str, post_caption: str, platform: str
    ) -> Dict[str, Any]:
        """
        AI classification of a comment:
        - sentiment: positive, neutral, negative, hate
        - type: question, compliment, feedback, spam, troll
        - priority: high, medium, low
        - requires_reply: bool
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Classify this social media comment. Return JSON:
{
    "sentiment": "positive|neutral|negative|hate",
    "type": "question|compliment|feedback|spam|troll|genuine",
    "priority": "high|medium|low",
    "requires_reply": true/false,
    "reason": "brief reason"
}
Questions and genuine engagement = high priority.
Spam, trolls = low priority, no reply.
Hate speech = skip entirely.""",
                    },
                    {
                        "role": "user",
                        "content": f"Post caption: {post_caption[:200]}\nComment: {comment_text}",
                    },
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.warning(f"[Engagement] Comment classification failed: {e}")
            return {
                "sentiment": "neutral",
                "type": "genuine",
                "priority": "medium",
                "requires_reply": True,
                "reason": "Classification unavailable",
            }

    async def generate_reply(
        self,
        comment_text: str,
        post_caption: str,
        platform: str,
        creator_voice: str = "warm, authentic, encouraging, occasionally uses emojis",
    ) -> Dict[str, Any]:
        """
        Generate a contextual, authentic reply to a comment.
        Matches creator's voice and references the specific comment.
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are replying to a comment on your social media post.
Your voice: {creator_voice}
Platform: {platform}

Rules:
- Reference the specific comment content (don't be generic)
- Vary length (sometimes short, sometimes longer)
- Be genuine and conversational
- Occasionally use 1-2 emojis
- If it's a question, answer it thoughtfully
- If it's a compliment, thank them naturally
- Max {SAFETY_GUIDELINES['max_reply_length']} characters
- Never mention: {', '.join(SAFETY_GUIDELINES['never_mention'])}
- Always stay positive, never argue

Return JSON: {{"reply": "your reply text", "confidence": 0.0-1.0}}""",
                    },
                    {
                        "role": "user",
                        "content": f"Your post: {post_caption[:200]}\nTheir comment: {comment_text}\n\nWrite a reply:",
                    },
                ],
                temperature=0.85,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return {
                "reply": result.get("reply", ""),
                "confidence": result.get("confidence", 0.7),
            }

        except Exception as e:
            logger.warning(f"[Engagement] Reply generation failed: {e}")
            return {"reply": "", "confidence": 0, "error": str(e)}

    async def generate_comment_replies(
        self,
        account_id: str,
        platform: str,
        comments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Process a batch of comments: classify each, generate replies,
        and store as pending engagement actions.
        
        If no comments provided, uses placeholder to demonstrate the pipeline.
        """
        if not comments:
            return {"generated": 0, "reason": "No comments provided. Pass comments list to generate replies."}

        generated = 0
        skipped = 0

        from sqlalchemy import create_engine, text
        engine = create_engine(self.db_url)

        for comment in comments:
            comment_text = comment.get("text", "")
            post_caption = comment.get("post_caption", "")
            commenter = comment.get("username", "unknown")
            post_id = comment.get("post_id", "")

            # Classify
            classification = await self.classify_comment(comment_text, post_caption, platform)

            if not classification.get("requires_reply", True):
                skipped += 1
                continue

            if classification.get("sentiment") == "hate":
                skipped += 1
                continue

            # Generate reply
            reply_data = await self.generate_reply(comment_text, post_caption, platform)
            reply_text = reply_data.get("reply", "")
            if not reply_text:
                skipped += 1
                continue

            # Determine status based on mode
            status = "approved" if self._mode == "full_auto" else "pending"

            # Store as engagement action
            action_id = str(uuid.uuid4())
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO engagement_actions (
                        id, account_id, platform, action_type,
                        target_user, target_post_id, content,
                        status, ai_generated, created_at
                    ) VALUES (
                        :id, :account_id, :platform, 'reply',
                        :target_user, :post_id, :content,
                        :status, true, NOW()
                    )
                """), {
                    "id": action_id,
                    "account_id": account_id,
                    "platform": platform,
                    "target_user": commenter,
                    "post_id": post_id,
                    "content": reply_text,
                    "status": status,
                })
                conn.commit()

            generated += 1

            # Humanized delay between processing
            await asyncio.sleep(random.uniform(0.5, 1.5))

        logger.info(f"[Engagement] Generated {generated} replies, skipped {skipped} for {account_id} on {platform}")
        return {"generated": generated, "skipped": skipped, "mode": self._mode}

    # ═══════════════════════════════════════════════════════════════════════
    # 2. PROACTIVE ENGAGEMENT — Generate comments for niche content
    # ═══════════════════════════════════════════════════════════════════════

    async def generate_engagement_comment(
        self,
        target_caption: str,
        platform: str,
    ) -> Dict[str, Any]:
        """
        Generate a genuine, value-adding comment for niche content.
        Rules: No generic comments, must reference specific content, add value.
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are engaging with content from a fellow creator in your niche (relationships, self-improvement, motivation).
Write a genuine, value-adding comment. Platform: {platform}

Rules:
- NEVER write generic comments like "Great post!" or "Love this!"
- Reference SPECIFIC content from their post
- Add value: share an insight, ask a thoughtful question, or relate a brief experience
- 1-3 sentences max
- Be conversational, not formal
- Occasional emoji OK

Return JSON: {{"comment": "your comment", "engagement_type": "insight|question|relate"}}""",
                    },
                    {"role": "user", "content": f"Their post: {target_caption[:300]}"},
                ],
                temperature=0.9,
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.warning(f"[Engagement] Comment generation failed: {e}")
            return {"comment": "", "error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════
    # 3. RATE LIMITER — Daily caps & human-like delays
    # ═══════════════════════════════════════════════════════════════════════

    async def can_perform_action(
        self, account_id: str, platform: str, action_type: str
    ) -> Tuple[bool, str]:
        """Check if action is within daily limits."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            today = date.today()
            limits = DAILY_LIMITS.get(platform, {})
            max_actions = limits.get(action_type, 0)

            if max_actions == 0:
                return False, f"{action_type} not supported on {platform}"

            with engine.connect() as conn:
                count = conn.execute(text("""
                    SELECT COUNT(*) FROM engagement_actions
                    WHERE account_id = :account_id AND platform = :platform
                      AND action_type = :action_type
                      AND created_at::date = :today
                      AND status IN ('approved', 'executed')
                """), {
                    "account_id": account_id,
                    "platform": platform,
                    "action_type": action_type,
                    "today": today,
                }).scalar() or 0

            if count >= max_actions:
                return False, f"Daily limit reached: {count}/{max_actions} {action_type} on {platform}"

            return True, f"{count}/{max_actions} {action_type} today"

        except Exception as e:
            return False, str(e)

    async def get_humanized_delay(self, action_type: str = "comment") -> float:
        """Return a randomized human-like delay in seconds."""
        base_min = HUMANIZER_CONFIG["min_delay_seconds"]
        base_max = HUMANIZER_CONFIG["max_delay_seconds"]

        # Shorter delays for likes, longer for comments
        multiplier = {"like": 0.3, "comment": 1.0, "follow": 0.5, "reply": 0.8, "dm": 1.2}
        mult = multiplier.get(action_type, 1.0)

        delay = random.uniform(base_min * mult, base_max * mult)
        return round(delay, 1)

    # ═══════════════════════════════════════════════════════════════════════
    # 4. ACTION MANAGEMENT — Approve, reject, execute
    # ═══════════════════════════════════════════════════════════════════════

    async def get_pending_actions(
        self,
        platform: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get pending actions for human approval."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            query = """SELECT id, account_id, platform, action_type, target_user,
                              target_post_id, content, status, created_at
                       FROM engagement_actions WHERE status = 'pending'"""
            params: Dict[str, Any] = {"limit": limit}
            if platform:
                query += " AND platform = :platform"
                params["platform"] = platform
            query += " ORDER BY created_at DESC LIMIT :limit"

            with engine.connect() as conn:
                rows = conn.execute(text(query), params).fetchall()

            return [
                {
                    "id": str(r[0]),
                    "account_id": r[1],
                    "platform": r[2],
                    "action_type": r[3],
                    "target_user": r[4],
                    "target_post_id": r[5],
                    "content": r[6],
                    "status": r[7],
                    "created_at": r[8].isoformat() if r[8] else None,
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"[Engagement] Get pending failed: {e}")
            return []

    async def approve_action(self, action_id: str) -> Dict[str, Any]:
        """Approve a pending engagement action."""
        return await self._update_action_status(action_id, "approved", human_approved=True)

    async def reject_action(self, action_id: str) -> Dict[str, Any]:
        """Reject a pending engagement action."""
        return await self._update_action_status(action_id, "skipped")

    async def _update_action_status(
        self, action_id: str, status: str, human_approved: bool = False
    ) -> Dict[str, Any]:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE engagement_actions SET status = :status, human_approved = :approved
                    WHERE id = :id
                """), {"id": action_id, "status": status, "approved": human_approved})
                conn.commit()
            return {"action_id": action_id, "status": status}
        except Exception as e:
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════
    # 5. SESSION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    async def start_session(
        self, account_id: str, platform: str
    ) -> Dict[str, Any]:
        """Start an engagement session."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)
            session_id = str(uuid.uuid4())
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO engagement_sessions (id, account_id, platform, session_start, status)
                    VALUES (:id, :account_id, :platform, NOW(), 'active')
                """), {"id": session_id, "account_id": account_id, "platform": platform})
                conn.commit()
            logger.info(f"[Engagement] Session started: {account_id} on {platform}")
            return {"session_id": session_id, "account_id": account_id, "platform": platform, "status": "active"}
        except Exception as e:
            return {"error": str(e)}

    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End an active engagement session."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE engagement_sessions SET session_end = NOW(), status = 'completed'
                    WHERE id = :id
                """), {"id": session_id})
                conn.commit()
            return {"session_id": session_id, "status": "completed"}
        except Exception as e:
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════
    # 6. SETTINGS & STATS
    # ═══════════════════════════════════════════════════════════════════════

    async def get_settings(self) -> Dict[str, Any]:
        """Get current engagement configuration."""
        return {
            "mode": self._mode,
            "daily_limits": DAILY_LIMITS,
            "humanizer": HUMANIZER_CONFIG,
            "safety": SAFETY_GUIDELINES,
        }

    async def update_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Update engagement configuration."""
        if "mode" in settings:
            valid_modes = ["full_auto", "reply_only", "assist", "monitor", "off"]
            if settings["mode"] in valid_modes:
                self._mode = settings["mode"]
            else:
                return {"error": f"Invalid mode. Must be one of: {valid_modes}"}
        return await self.get_settings()

    async def get_stats(self, period_days: int = 7) -> Dict[str, Any]:
        """Engagement statistics for the dashboard."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)
            cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

            with engine.connect() as conn:
                # Action counts by type
                action_rows = conn.execute(text("""
                    SELECT action_type, status, COUNT(*)
                    FROM engagement_actions
                    WHERE created_at > :cutoff
                    GROUP BY action_type, status
                """), {"cutoff": cutoff}).fetchall()

                # Session counts
                session_count = conn.execute(text("""
                    SELECT COUNT(*) FROM engagement_sessions
                    WHERE session_start > :cutoff
                """), {"cutoff": cutoff}).scalar() or 0

                # Daily stats
                daily_rows = conn.execute(text("""
                    SELECT stat_date, SUM(total_replies), SUM(total_likes),
                           SUM(total_comments), SUM(total_follows)
                    FROM engagement_daily_stats
                    WHERE stat_date > :cutoff
                    GROUP BY stat_date ORDER BY stat_date
                """), {"cutoff": cutoff.date()}).fetchall()

            # Aggregate
            action_summary = {}
            for r in action_rows:
                key = f"{r[0]}_{r[1]}"
                action_summary[key] = r[2]

            return {
                "period_days": period_days,
                "mode": self._mode,
                "actions": action_summary,
                "total_sessions": session_count,
                "daily_stats": [
                    {
                        "date": r[0].isoformat() if r[0] else None,
                        "replies": r[1] or 0,
                        "likes": r[2] or 0,
                        "comments": r[3] or 0,
                        "follows": r[4] or 0,
                    }
                    for r in daily_rows
                ],
                "daily_limits": DAILY_LIMITS,
            }

        except Exception as e:
            logger.error(f"[Engagement] Stats query failed: {e}")
            return {"error": str(e)}

    async def get_dashboard(self) -> Dict[str, Any]:
        """Engagement dashboard overview."""
        stats = await self.get_stats(period_days=7)
        pending = await self.get_pending_actions(limit=5)

        return {
            "mode": self._mode,
            "stats_7d": stats,
            "pending_actions": pending,
            "pending_count": len(pending),
        }
