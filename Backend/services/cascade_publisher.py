"""
Multi-Account Cascade Publisher
================================
Automatically distributes content from primary accounts to secondary accounts
with staggered timing and refreshed AI captions.

Flow:
1. Primary post publishes → triggers cascade
2. Cascade scheduler creates entries for each secondary account
3. Staggered delays (2-8 hours) prevent duplicate-content suppression
4. AI Caption Variants refresh each caption per account
5. Posts feed into existing publish pipeline

Usage:
    cascade = CascadePublisher()
    
    # Trigger after primary post publishes
    await cascade.on_post_published(post_id, platform="tiktok", account_id="710")
    
    # Cron: process pending cascades
    await cascade.run_cascade_cycle()
"""

import os
import json
import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from loguru import logger


# ─── Account Hierarchy ───────────────────────────────────────────────────────

ACCOUNT_HIERARCHY = {
    "tiktok": {
        "primary": "710",       # @isaiah_dupree
        "secondary": ["243", "4508", "571"],
    },
    "instagram": {
        "primary": "807",       # @the_isaiah_dupree
        "secondary": ["670", "1369", "4508"],
    },
    "threads": {
        "primary": "201",       # @the_isaiah_dupree
        "secondary": ["173", "1369", "4150"],
    },
    "pinterest": {
        "primary": "173",
        "secondary": ["243"],
    },
}

# Default cascade timing
DEFAULT_DELAY_MIN = 120   # 2 hours
DEFAULT_DELAY_MAX = 360   # 6 hours
MAX_POSTS_PER_DAY_PER_ACCOUNT = 3


class CascadePublisher:
    """Staggered multi-account content distribution."""

    def __init__(self):
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres",
        )

    # ── Trigger Cascade ──────────────────────────────────────────────────

    async def on_post_published(
        self,
        original_post_id: str,
        platform: str,
        account_id: str,
    ) -> Dict[str, Any]:
        """
        Called after a primary post publishes successfully.
        Creates cascade entries for all secondary accounts.
        """
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            # Get cascade rule for this platform+account
            rule = await self._get_rule(platform, account_id)
            if not rule:
                # Check if this is a primary account with default hierarchy
                hierarchy = ACCOUNT_HIERARCHY.get(platform, {})
                if hierarchy.get("primary") != account_id:
                    return {"cascaded": 0, "reason": "Not a primary account"}
                # Create default rule
                rule = {
                    "id": None,
                    "mode": "always",
                    "secondary_account_ids": hierarchy.get("secondary", []),
                    "delay_minutes_min": DEFAULT_DELAY_MIN,
                    "delay_minutes_max": DEFAULT_DELAY_MAX,
                    "refresh_caption": True,
                    "performance_gate_threshold": 1000,
                    "performance_gate_window_hours": 2,
                }

            if not rule["secondary_account_ids"]:
                return {"cascaded": 0, "reason": "No secondary accounts configured"}

            mode = rule.get("mode", "always")
            secondary_ids = rule["secondary_account_ids"]

            # Compute staggered times
            now = datetime.now(timezone.utc)
            stagger_times = self._compute_stagger_times(
                base_time=now,
                num_accounts=len(secondary_ids),
                delay_min=rule.get("delay_minutes_min", DEFAULT_DELAY_MIN),
                delay_max=rule.get("delay_minutes_max", DEFAULT_DELAY_MAX),
            )

            # Create cascade_posts entries
            created = []
            with engine.connect() as conn:
                for i, target_account in enumerate(secondary_ids):
                    delay_mins = stagger_times[i] if i < len(stagger_times) else DEFAULT_DELAY_MIN
                    status = "pending" if mode == "always" else "gated" if mode == "performance_gated" else "manual"

                    cascade_id = str(uuid.uuid4())
                    conn.execute(text("""
                        INSERT INTO cascade_posts (
                            id, original_post_id, cascade_rule_id,
                            target_account_id, delay_minutes, status, created_at
                        ) VALUES (
                            :id, :original_id, :rule_id,
                            :target, :delay, :status, NOW()
                        )
                    """), {
                        "id": cascade_id,
                        "original_id": original_post_id,
                        "rule_id": rule.get("id"),
                        "target": target_account,
                        "delay": delay_mins,
                        "status": status,
                    })

                    created.append({
                        "cascade_id": cascade_id,
                        "target_account": target_account,
                        "delay_minutes": delay_mins,
                        "status": status,
                    })

                conn.commit()

            logger.success(
                f"[Cascade] ✓ Triggered cascade for {platform} post {original_post_id[:8]} → "
                f"{len(created)} secondary accounts ({mode} mode)"
            )

            return {
                "original_post_id": original_post_id,
                "platform": platform,
                "mode": mode,
                "cascaded": len(created),
                "entries": created,
            }

        except Exception as e:
            logger.error(f"[Cascade] Trigger failed: {e}")
            return {"error": str(e)}

    # ── Process Pending Cascades ─────────────────────────────────────────

    async def run_cascade_cycle(self) -> Dict[str, Any]:
        """
        Cron: Process all pending cascade posts whose delay has elapsed.
        Creates scheduled_posts with refreshed captions.
        """
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                # Find pending cascades whose delay has elapsed
                rows = conn.execute(text("""
                    SELECT cp.id, cp.original_post_id, cp.target_account_id,
                           cp.delay_minutes, cp.cascade_rule_id,
                           sp.platform, sp.caption, sp.media_path, sp.hashtags
                    FROM cascade_posts cp
                    JOIN scheduled_posts sp ON sp.id = cp.original_post_id
                    WHERE cp.status = 'pending'
                      AND cp.created_at + (cp.delay_minutes || ' minutes')::INTERVAL < NOW()
                    ORDER BY cp.created_at
                    LIMIT 20
                """)).fetchall()

            if not rows:
                return {"processed": 0, "reason": "No cascade posts ready"}

            processed = 0
            for row in rows:
                cascade_id = str(row[0])
                original_id = str(row[1])
                target_account = row[2]
                platform = row[5]
                original_caption = row[6] or ""
                media_path = row[7]
                hashtags = row[8] or []

                # Refresh caption via AI
                refreshed_caption = original_caption
                try:
                    from services.caption_variants_service import CaptionVariantsService
                    svc = CaptionVariantsService()
                    variants = await svc.generate_variants(
                        base_caption=original_caption,
                        platforms=[platform],
                        context="Cascade repost for secondary account — make it feel fresh and unique",
                    )
                    if variants and platform in variants:
                        refreshed_caption = variants[platform]
                except Exception as e:
                    logger.debug(f"[Cascade] Caption refresh failed, using original: {e}")

                # Create scheduled post
                new_post_id = str(uuid.uuid4())
                sched_time = datetime.now(timezone.utc) + timedelta(minutes=5)

                with engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO scheduled_posts (
                            id, platform, blotato_account_id, caption, media_path,
                            hashtags, scheduled_time, status, source,
                            is_ai_recommended, recommendation_reasoning,
                            created_at, updated_at
                        ) VALUES (
                            :id, :platform, :account, :caption, :media_path,
                            :hashtags, :sched_time, 'scheduled', 'cascade',
                            true, :reasoning, NOW(), NOW()
                        )
                    """), {
                        "id": new_post_id,
                        "platform": platform,
                        "account": target_account,
                        "caption": refreshed_caption,
                        "media_path": media_path,
                        "hashtags": hashtags,
                        "sched_time": sched_time.isoformat(),
                        "reasoning": f"Cascade from post {original_id[:8]} to account {target_account}",
                    })

                    # Update cascade post status
                    conn.execute(text("""
                        UPDATE cascade_posts SET
                            status = 'scheduled',
                            scheduled_post_id = :sp_id,
                            refreshed_caption = :caption
                        WHERE id = :id
                    """), {
                        "id": cascade_id,
                        "sp_id": new_post_id,
                        "caption": refreshed_caption,
                    })

                    conn.commit()
                    processed += 1

            logger.info(f"[Cascade] Processed {processed}/{len(rows)} cascade posts")
            return {"processed": processed, "total_ready": len(rows)}

        except Exception as e:
            logger.error(f"[Cascade] Cycle failed: {e}")
            return {"error": str(e)}

    # ── Performance Gate Check ───────────────────────────────────────────

    async def check_performance_gates(self) -> Dict[str, Any]:
        """Check gated cascade posts and promote to pending if threshold met."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                # Find gated cascades
                rows = conn.execute(text("""
                    SELECT cp.id, cp.original_post_id, cp.cascade_rule_id,
                           cr.performance_gate_metric, cr.performance_gate_threshold,
                           cr.performance_gate_window_hours
                    FROM cascade_posts cp
                    JOIN cascade_rules cr ON cr.id = cp.cascade_rule_id
                    WHERE cp.status = 'gated'
                    ORDER BY cp.created_at
                    LIMIT 50
                """)).fetchall()

            promoted = 0
            skipped = 0

            for row in rows:
                cascade_id, original_id = str(row[0]), str(row[1])
                metric = row[3] or "views"
                threshold = row[4] or 1000
                window_hours = row[5] or 2

                # Check if original post has metrics
                with engine.connect() as conn:
                    metrics = conn.execute(text(f"""
                        SELECT COALESCE({metric}, 0) FROM posted_content
                        WHERE scheduled_post_id = :sp_id
                    """), {"sp_id": original_id}).scalar()

                gate_passed = (metrics or 0) >= threshold
                gate_result = {
                    "metric": metric,
                    "value": metrics or 0,
                    "threshold": threshold,
                    "passed": gate_passed,
                }

                new_status = "pending" if gate_passed else "gated"

                # Check if gate window expired
                with engine.connect() as conn:
                    created = conn.execute(text(
                        "SELECT created_at FROM cascade_posts WHERE id = :id"
                    ), {"id": cascade_id}).scalar()

                if created and (datetime.now(timezone.utc) - created).total_seconds() > window_hours * 3600 * 2:
                    new_status = "skipped"  # Window expired without meeting threshold
                    skipped += 1

                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE cascade_posts SET
                            status = :status,
                            gate_check_at = NOW(),
                            gate_result = :result
                        WHERE id = :id
                    """), {
                        "id": cascade_id,
                        "status": new_status,
                        "result": json.dumps(gate_result),
                    })
                    conn.commit()

                if gate_passed:
                    promoted += 1

            return {"checked": len(rows), "promoted": promoted, "skipped": skipped}

        except Exception as e:
            logger.error(f"[Cascade] Gate check failed: {e}")
            return {"error": str(e)}

    # ── Rules Management ─────────────────────────────────────────────────

    async def get_rules(self) -> List[Dict[str, Any]]:
        """List all cascade rules."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT id, platform, primary_account_id, secondary_account_ids,
                           mode, delay_minutes_min, delay_minutes_max,
                           performance_gate_threshold, refresh_caption, enabled
                    FROM cascade_rules ORDER BY platform
                """)).fetchall()

            return [
                {
                    "id": str(r[0]),
                    "platform": r[1],
                    "primary_account_id": r[2],
                    "secondary_account_ids": r[3],
                    "mode": r[4],
                    "delay_minutes_min": r[5],
                    "delay_minutes_max": r[6],
                    "performance_gate_threshold": r[7],
                    "refresh_caption": r[8],
                    "enabled": r[9],
                }
                for r in rows
            ]

        except Exception as e:
            logger.error(f"[Cascade] Get rules failed: {e}")
            return []

    async def upsert_rule(
        self,
        platform: str,
        primary_account_id: str,
        secondary_account_ids: List[str],
        mode: str = "always",
        delay_min: int = 120,
        delay_max: int = 360,
        performance_gate_threshold: int = 1000,
        refresh_caption: bool = True,
    ) -> Dict[str, Any]:
        """Create or update a cascade rule."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            rule_id = str(uuid.uuid4())
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO cascade_rules (
                        id, platform, primary_account_id, secondary_account_ids,
                        mode, delay_minutes_min, delay_minutes_max,
                        performance_gate_threshold, refresh_caption
                    ) VALUES (
                        :id, :platform, :primary, :secondary,
                        :mode, :delay_min, :delay_max,
                        :threshold, :refresh
                    )
                    ON CONFLICT (platform, primary_account_id) DO UPDATE SET
                        secondary_account_ids = EXCLUDED.secondary_account_ids,
                        mode = EXCLUDED.mode,
                        delay_minutes_min = EXCLUDED.delay_minutes_min,
                        delay_minutes_max = EXCLUDED.delay_minutes_max,
                        performance_gate_threshold = EXCLUDED.performance_gate_threshold,
                        refresh_caption = EXCLUDED.refresh_caption
                """), {
                    "id": rule_id,
                    "platform": platform,
                    "primary": primary_account_id,
                    "secondary": secondary_account_ids,
                    "mode": mode,
                    "delay_min": delay_min,
                    "delay_max": delay_max,
                    "threshold": performance_gate_threshold,
                    "refresh": refresh_caption,
                })
                conn.commit()

            return {"platform": platform, "primary": primary_account_id, "mode": mode, "secondary": secondary_account_ids}

        except Exception as e:
            logger.error(f"[Cascade] Upsert rule failed: {e}")
            return {"error": str(e)}

    async def seed_default_rules(self) -> Dict[str, Any]:
        """Create default cascade rules from ACCOUNT_HIERARCHY."""
        created = 0
        for platform, hierarchy in ACCOUNT_HIERARCHY.items():
            result = await self.upsert_rule(
                platform=platform,
                primary_account_id=hierarchy["primary"],
                secondary_account_ids=hierarchy["secondary"],
            )
            if "error" not in result:
                created += 1
        return {"created": created, "platforms": list(ACCOUNT_HIERARCHY.keys())}

    # ── Stats ────────────────────────────────────────────────────────────

    async def get_stats(self) -> Dict[str, Any]:
        """Cascade performance statistics."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                total = conn.execute(text("SELECT COUNT(*) FROM cascade_posts")).scalar() or 0
                by_status = {}
                rows = conn.execute(text(
                    "SELECT status, COUNT(*) FROM cascade_posts GROUP BY status"
                )).fetchall()
                for r in rows:
                    by_status[r[0]] = r[1]

                rules_count = conn.execute(text("SELECT COUNT(*) FROM cascade_rules WHERE enabled = true")).scalar() or 0

            return {
                "total_cascade_posts": total,
                "by_status": by_status,
                "active_rules": rules_count,
                "account_hierarchy": {
                    k: {"primary": v["primary"], "secondary_count": len(v["secondary"])}
                    for k, v in ACCOUNT_HIERARCHY.items()
                },
            }

        except Exception as e:
            return {"error": str(e)}

    # ── Private Helpers ──────────────────────────────────────────────────

    async def _get_rule(self, platform: str, account_id: str) -> Optional[Dict]:
        """Fetch cascade rule for a platform/account."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT id, mode, secondary_account_ids, delay_minutes_min,
                           delay_minutes_max, refresh_caption,
                           performance_gate_threshold, performance_gate_window_hours
                    FROM cascade_rules
                    WHERE platform = :platform AND primary_account_id = :account AND enabled = true
                """), {"platform": platform, "account": account_id}).fetchone()

            if not row:
                return None

            return {
                "id": str(row[0]),
                "mode": row[1],
                "secondary_account_ids": row[2] or [],
                "delay_minutes_min": row[3],
                "delay_minutes_max": row[4],
                "refresh_caption": row[5],
                "performance_gate_threshold": row[6],
                "performance_gate_window_hours": row[7],
            }

        except Exception as e:
            logger.error(f"[Cascade] Get rule failed: {e}")
            return None

    def _compute_stagger_times(
        self,
        base_time: datetime,
        num_accounts: int,
        delay_min: int,
        delay_max: int,
    ) -> List[int]:
        """
        Compute staggered delay minutes for secondary accounts.
        Each account gets a progressively later window.
        """
        delays = []
        slot_size = (delay_max - delay_min) / max(num_accounts, 1)

        for i in range(num_accounts):
            window_start = delay_min + int(i * slot_size)
            window_end = delay_min + int((i + 1) * slot_size)
            delay = random.randint(window_start, max(window_start + 1, window_end))
            delays.append(delay)

        return delays
