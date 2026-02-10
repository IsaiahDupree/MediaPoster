"""
A/B Testing Framework
======================
Systematically test content variants across duplicate accounts.

With 4 TikTok and 4 Instagram accounts, this service:
1. Creates structured A/B tests (caption, hook, time, hashtag variants)
2. Assigns variants to accounts (balanced random assignment)
3. Schedules posts via existing publish pipeline
4. Collects metrics after 48-72 hours
5. Runs statistical significance tests (two-sample z-test)
6. Declares winners and stores learnings

Usage:
    svc = ABTestingService()
    test = await svc.create_test(
        name="Question vs Bold Hook",
        test_type="caption",
        platform="tiktok",
        media_path="/path/to/video.mp4",
        variants={"A": {"caption": "Is this the future?"}, "B": {"caption": "This changes EVERYTHING."}}
    )
    # ... posts are published ...
    result = await svc.analyze_test(test["id"])
"""

import os
import math
import json
import uuid
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from loguru import logger


# ─── Constants ───────────────────────────────────────────────────────────────

TEST_TYPES = ["caption", "hook", "time", "title", "hashtag", "account"]
MIN_VIEWS_FOR_SIGNIFICANCE = 100  # Lower for small accounts
MIN_HOURS_BEFORE_EVAL = 48
CONFIDENCE_THRESHOLD = 0.95  # 95% confidence
MAX_ACTIVE_TESTS = 10

# Account pools by platform (from Blotato mapping)
ACCOUNT_POOLS = {
    "tiktok": ["710", "243", "4508", "571"],
    "instagram": ["807", "670", "1369", "4508"],
    "threads": ["173", "201", "1369", "4150"],
    "pinterest": ["173", "243"],
}


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class TestResult:
    """Result of statistical analysis."""
    significant: bool
    p_value: float
    winner: Optional[str]  # variant label: 'A', 'B', etc.
    lift: float  # % improvement of winner over loser
    confidence: float
    sample_sizes: Dict[str, int]  # variant -> views


@dataclass
class Learning:
    """An insight derived from a completed A/B test."""
    test_id: str
    platform: str
    test_type: str
    learning: str
    confidence: float
    sample_size: int


# ─── Service ─────────────────────────────────────────────────────────────────

class ABTestingService:
    """A/B testing across multi-account setups."""

    def __init__(self):
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres",
        )

    # ── Create Test ──────────────────────────────────────────────────────

    async def create_test(
        self,
        name: str,
        test_type: str,
        platform: str,
        media_path: Optional[str] = None,
        variants: Optional[Dict[str, Dict[str, Any]]] = None,
        hypothesis: Optional[str] = None,
        auto_schedule: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new A/B test.

        Args:
            name: Human-readable test name
            test_type: One of: caption, hook, time, title, hashtag, account
            platform: Target platform
            media_path: Path to the video/media file
            variants: Dict of variant_label -> {caption, title, hashtags, scheduled_time}
                      e.g. {"A": {"caption": "..."}, "B": {"caption": "..."}}
            hypothesis: What you expect to happen
            auto_schedule: Whether to auto-create scheduled_posts

        Returns:
            Test details with variant assignments
        """
        if test_type not in TEST_TYPES:
            return {"error": f"Invalid test_type. Must be one of: {TEST_TYPES}"}

        # Get available accounts for this platform
        accounts = ACCOUNT_POOLS.get(platform, [])
        if len(accounts) < 2:
            return {"error": f"Need at least 2 accounts for {platform} A/B testing"}

        # Default: 2 variants if not specified
        if not variants:
            variants = {"A": {}, "B": {}}

        variant_labels = list(variants.keys())
        if len(variant_labels) < 2:
            return {"error": "Need at least 2 variants"}

        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            test_id = str(uuid.uuid4())

            with engine.connect() as conn:
                # Create test
                conn.execute(text("""
                    INSERT INTO ab_tests (id, name, test_type, platform, status, hypothesis, created_at)
                    VALUES (:id, :name, :test_type, :platform, 'active', :hypothesis, NOW())
                """), {
                    "id": test_id,
                    "name": name,
                    "test_type": test_type,
                    "platform": platform,
                    "hypothesis": hypothesis,
                })

                # Assign variants to accounts (balanced random)
                random.shuffle(accounts)
                assignments = []
                for i, account_id in enumerate(accounts):
                    label = variant_labels[i % len(variant_labels)]
                    variant_data = variants[label]

                    variant_id = str(uuid.uuid4())
                    scheduled_post_id = None

                    # Auto-create scheduled posts
                    if auto_schedule and media_path:
                        scheduled_post_id = str(uuid.uuid4())
                        sched_time = variant_data.get("scheduled_time")
                        if not sched_time:
                            sched_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

                        conn.execute(text("""
                            INSERT INTO scheduled_posts (
                                id, platform, blotato_account_id, caption, media_path,
                                scheduled_time, status, source, is_ai_recommended,
                                recommendation_reasoning, created_at, updated_at
                            ) VALUES (
                                :id, :platform, :account_id, :caption, :media_path,
                                :scheduled_time, 'scheduled', 'ab_test',
                                true, :reasoning, NOW(), NOW()
                            )
                        """), {
                            "id": scheduled_post_id,
                            "platform": platform,
                            "account_id": account_id,
                            "caption": variant_data.get("caption", ""),
                            "media_path": media_path,
                            "scheduled_time": sched_time,
                            "reasoning": f"A/B Test: {name} | Variant {label}",
                        })

                    # Create variant record
                    conn.execute(text("""
                        INSERT INTO ab_test_variants (
                            id, test_id, variant_label, account_id,
                            scheduled_post_id, caption, title, scheduled_time
                        ) VALUES (
                            :id, :test_id, :label, :account_id,
                            :scheduled_post_id, :caption, :title, :scheduled_time
                        )
                    """), {
                        "id": variant_id,
                        "test_id": test_id,
                        "label": label,
                        "account_id": account_id,
                        "scheduled_post_id": scheduled_post_id,
                        "caption": variant_data.get("caption"),
                        "title": variant_data.get("title"),
                        "scheduled_time": variant_data.get("scheduled_time"),
                    })

                    assignments.append({
                        "variant_id": variant_id,
                        "variant_label": label,
                        "account_id": account_id,
                        "scheduled_post_id": scheduled_post_id,
                        "caption_preview": (variant_data.get("caption") or "")[:80],
                    })

                conn.commit()

            logger.success(
                f"[A/B Test] ✓ Created '{name}' ({test_type}) on {platform} | "
                f"{len(variant_labels)} variants × {len(accounts)} accounts"
            )

            return {
                "id": test_id,
                "name": name,
                "test_type": test_type,
                "platform": platform,
                "status": "active",
                "hypothesis": hypothesis,
                "variants": variant_labels,
                "assignments": assignments,
            }

        except Exception as e:
            logger.error(f"[A/B Test] Create failed: {e}")
            return {"error": str(e)}

    # ── List Tests ───────────────────────────────────────────────────────

    async def list_tests(
        self, status: Optional[str] = None, platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all A/B tests with optional filters."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            query = "SELECT id, name, test_type, platform, status, hypothesis, created_at, completed_at, winner_variant_id FROM ab_tests WHERE 1=1"
            params: Dict[str, Any] = {}

            if status:
                query += " AND status = :status"
                params["status"] = status
            if platform:
                query += " AND platform = :platform"
                params["platform"] = platform

            query += " ORDER BY created_at DESC"

            with engine.connect() as conn:
                rows = conn.execute(text(query), params).fetchall()

            return [
                {
                    "id": str(r[0]),
                    "name": r[1],
                    "test_type": r[2],
                    "platform": r[3],
                    "status": r[4],
                    "hypothesis": r[5],
                    "created_at": r[6].isoformat() if r[6] else None,
                    "completed_at": r[7].isoformat() if r[7] else None,
                    "winner_variant_id": str(r[8]) if r[8] else None,
                }
                for r in rows
            ]

        except Exception as e:
            logger.error(f"[A/B Test] List failed: {e}")
            return []

    # ── Get Test Details ─────────────────────────────────────────────────

    async def get_test(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get full test details including variants and metrics."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                test_row = conn.execute(text("""
                    SELECT id, name, test_type, platform, status, hypothesis,
                           created_at, completed_at, winner_variant_id
                    FROM ab_tests WHERE id = :id
                """), {"id": test_id}).fetchone()

                if not test_row:
                    return None

                variant_rows = conn.execute(text("""
                    SELECT id, variant_label, account_id, scheduled_post_id,
                           caption, title, views, likes, comments, shares, saves,
                           engagement_rate, is_winner, metrics_collected_at
                    FROM ab_test_variants WHERE test_id = :test_id
                    ORDER BY variant_label
                """), {"test_id": test_id}).fetchall()

            return {
                "id": str(test_row[0]),
                "name": test_row[1],
                "test_type": test_row[2],
                "platform": test_row[3],
                "status": test_row[4],
                "hypothesis": test_row[5],
                "created_at": test_row[6].isoformat() if test_row[6] else None,
                "completed_at": test_row[7].isoformat() if test_row[7] else None,
                "winner_variant_id": str(test_row[8]) if test_row[8] else None,
                "variants": [
                    {
                        "id": str(v[0]),
                        "label": v[1],
                        "account_id": v[2],
                        "scheduled_post_id": str(v[3]) if v[3] else None,
                        "caption_preview": (v[4] or "")[:100],
                        "title": v[5],
                        "views": v[6] or 0,
                        "likes": v[7] or 0,
                        "comments": v[8] or 0,
                        "shares": v[9] or 0,
                        "saves": v[10] or 0,
                        "engagement_rate": float(v[11]) if v[11] else 0,
                        "is_winner": v[12] or False,
                        "metrics_collected_at": v[13].isoformat() if v[13] else None,
                    }
                    for v in variant_rows
                ],
            }

        except Exception as e:
            logger.error(f"[A/B Test] Get test failed: {e}")
            return None

    # ── Collect Metrics ──────────────────────────────────────────────────

    async def collect_metrics(self, test_id: str) -> Dict[str, Any]:
        """
        Pull latest engagement metrics for all variants in a test.
        Reads from posted_content / content_metrics_snapshots.
        """
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                # Get all variants
                variants = conn.execute(text("""
                    SELECT v.id, v.variant_label, v.scheduled_post_id
                    FROM ab_test_variants v
                    WHERE v.test_id = :test_id
                """), {"test_id": test_id}).fetchall()

                updated = 0
                for v in variants:
                    variant_id, label, sp_id = v[0], v[1], v[2]
                    if not sp_id:
                        continue

                    # Try posted_content first
                    metrics = conn.execute(text("""
                        SELECT views, likes, comments, shares, saves, engagement_rate
                        FROM posted_content
                        WHERE scheduled_post_id = :sp_id
                        LIMIT 1
                    """), {"sp_id": str(sp_id)}).fetchone()

                    if not metrics:
                        # Try content_metrics_snapshots
                        metrics = conn.execute(text("""
                            SELECT views, likes, comments, shares, saves, engagement_rate
                            FROM content_metrics_snapshots
                            WHERE scheduled_post_id = :sp_id
                            ORDER BY snapshot_at DESC
                            LIMIT 1
                        """), {"sp_id": str(sp_id)}).fetchone()

                    if metrics:
                        conn.execute(text("""
                            UPDATE ab_test_variants SET
                                views = :views, likes = :likes,
                                comments = :comments, shares = :shares,
                                saves = :saves, engagement_rate = :er,
                                metrics_collected_at = NOW()
                            WHERE id = :id
                        """), {
                            "id": str(variant_id),
                            "views": metrics[0] or 0,
                            "likes": metrics[1] or 0,
                            "comments": metrics[2] or 0,
                            "shares": metrics[3] or 0,
                            "saves": metrics[4] or 0,
                            "er": metrics[5] or 0,
                        })
                        updated += 1

                conn.commit()

            logger.info(f"[A/B Test] Collected metrics for {updated}/{len(variants)} variants in test {test_id[:8]}")
            return {"updated": updated, "total_variants": len(variants)}

        except Exception as e:
            logger.error(f"[A/B Test] Metrics collection failed: {e}")
            return {"error": str(e)}

    # ── Analyze Test ─────────────────────────────────────────────────────

    async def analyze_test(self, test_id: str) -> Dict[str, Any]:
        """
        Run statistical analysis on a test.
        Uses two-sample z-test for engagement rate proportions.
        """
        test = await self.get_test(test_id)
        if not test:
            return {"error": "Test not found"}

        # Collect latest metrics first
        await self.collect_metrics(test_id)
        test = await self.get_test(test_id)

        variants = test["variants"]
        if len(variants) < 2:
            return {"error": "Need at least 2 variants to analyze"}

        # Group by variant label
        groups: Dict[str, List[Dict]] = defaultdict(list)
        for v in variants:
            groups[v["label"]].append(v)

        # Aggregate per group
        group_stats = {}
        for label, group_variants in groups.items():
            total_views = sum(v["views"] for v in group_variants)
            total_engagements = sum(
                v["likes"] + v["comments"] + v["shares"]
                for v in group_variants
            )
            er = total_engagements / total_views if total_views > 0 else 0
            group_stats[label] = {
                "views": total_views,
                "engagements": total_engagements,
                "engagement_rate": er,
                "accounts": len(group_variants),
            }

        # Run z-test between first two groups
        labels = sorted(group_stats.keys())
        if len(labels) < 2:
            return {"error": "Not enough variant groups with data"}

        a_stats = group_stats[labels[0]]
        b_stats = group_stats[labels[1]]

        result = self._two_sample_z_test(
            n1=a_stats["views"],
            x1=a_stats["engagements"],
            n2=b_stats["views"],
            x2=b_stats["engagements"],
        )

        # Determine winner
        winner_label = None
        if result.significant:
            winner_label = labels[0] if a_stats["engagement_rate"] > b_stats["engagement_rate"] else labels[1]

        analysis = {
            "test_id": test_id,
            "test_name": test["name"],
            "status": test["status"],
            "result": {
                "significant": result.significant,
                "p_value": round(result.p_value, 6),
                "confidence": round(result.confidence, 4),
                "winner": winner_label,
                "lift": round(result.lift, 2),
            },
            "groups": {
                label: {
                    "views": stats["views"],
                    "engagements": stats["engagements"],
                    "engagement_rate": round(stats["engagement_rate"], 6),
                    "accounts": stats["accounts"],
                }
                for label, stats in group_stats.items()
            },
        }

        logger.info(
            f"[A/B Test] Analysis: '{test['name']}' | "
            f"Winner: {winner_label or 'inconclusive'} | "
            f"p={result.p_value:.4f} | lift={result.lift:.1f}%"
        )

        return analysis

    # ── Declare Winner ───────────────────────────────────────────────────

    async def declare_winner(self, test_id: str) -> Dict[str, Any]:
        """Force-declare a winner and store the learning."""
        analysis = await self.analyze_test(test_id)
        if "error" in analysis:
            return analysis

        winner = analysis["result"]["winner"]
        if not winner:
            return {"error": "No statistically significant winner yet", "analysis": analysis}

        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            with engine.connect() as conn:
                # Find winner variant ID
                winner_variant = conn.execute(text("""
                    SELECT id FROM ab_test_variants
                    WHERE test_id = :test_id AND variant_label = :label
                    LIMIT 1
                """), {"test_id": test_id, "label": winner}).fetchone()

                winner_variant_id = str(winner_variant[0]) if winner_variant else None

                # Update test status
                conn.execute(text("""
                    UPDATE ab_tests SET
                        status = 'completed',
                        completed_at = NOW(),
                        winner_variant_id = :winner_id
                    WHERE id = :test_id
                """), {"test_id": test_id, "winner_id": winner_variant_id})

                # Mark winner variants
                conn.execute(text("""
                    UPDATE ab_test_variants SET is_winner = (variant_label = :winner)
                    WHERE test_id = :test_id
                """), {"test_id": test_id, "winner": winner})

                # Store learning
                test = await self.get_test(test_id)
                lift = analysis["result"]["lift"]
                groups = analysis["groups"]
                learning_text = self._generate_learning(test, winner, lift, groups)

                conn.execute(text("""
                    INSERT INTO ab_test_learnings (id, test_id, platform, test_type, learning, confidence, sample_size, created_at)
                    VALUES (:id, :test_id, :platform, :test_type, :learning, :confidence, :sample_size, NOW())
                """), {
                    "id": str(uuid.uuid4()),
                    "test_id": test_id,
                    "platform": test["platform"],
                    "test_type": test["test_type"],
                    "learning": learning_text,
                    "confidence": analysis["result"]["confidence"],
                    "sample_size": sum(g["views"] for g in groups.values()),
                })

                conn.commit()

            logger.success(f"[A/B Test] ✓ Winner declared: Variant {winner} for '{test['name']}'")
            return {
                "winner": winner,
                "lift": analysis["result"]["lift"],
                "confidence": analysis["result"]["confidence"],
                "learning": learning_text,
            }

        except Exception as e:
            logger.error(f"[A/B Test] Declare winner failed: {e}")
            return {"error": str(e)}

    # ── Get Learnings ────────────────────────────────────────────────────

    async def get_learnings(
        self, platform: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Browse accumulated A/B test learnings."""
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.db_url)

            query = """
                SELECT l.id, l.test_id, l.platform, l.test_type, l.learning,
                       l.confidence, l.sample_size, l.created_at, t.name as test_name
                FROM ab_test_learnings l
                JOIN ab_tests t ON t.id = l.test_id
                WHERE 1=1
            """
            params: Dict[str, Any] = {"limit": limit}
            if platform:
                query += " AND l.platform = :platform"
                params["platform"] = platform

            query += " ORDER BY l.created_at DESC LIMIT :limit"

            with engine.connect() as conn:
                rows = conn.execute(text(query), params).fetchall()

            return [
                {
                    "id": str(r[0]),
                    "test_id": str(r[1]),
                    "platform": r[2],
                    "test_type": r[3],
                    "learning": r[4],
                    "confidence": round(float(r[5]), 4) if r[5] else 0,
                    "sample_size": r[6] or 0,
                    "created_at": r[7].isoformat() if r[7] else None,
                    "test_name": r[8],
                }
                for r in rows
            ]

        except Exception as e:
            logger.error(f"[A/B Test] Get learnings failed: {e}")
            return []

    # ── Statistical Engine ───────────────────────────────────────────────

    def _two_sample_z_test(
        self, n1: int, x1: int, n2: int, x2: int
    ) -> TestResult:
        """
        Two-sample z-test for proportions.
        n1, n2 = sample sizes (views)
        x1, x2 = successes (engagements)
        """
        if n1 == 0 or n2 == 0:
            return TestResult(
                significant=False, p_value=1.0, winner=None,
                lift=0.0, confidence=0.0,
                sample_sizes={"A": n1, "B": n2},
            )

        p1 = x1 / n1
        p2 = x2 / n2
        p_pool = (x1 + x2) / (n1 + n2)

        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2)) if p_pool > 0 and p_pool < 1 else 0.001

        if se == 0:
            return TestResult(
                significant=False, p_value=1.0, winner=None,
                lift=0.0, confidence=0.0,
                sample_sizes={"A": n1, "B": n2},
            )

        z = (p1 - p2) / se
        # Two-tailed p-value using normal CDF approximation
        p_value = 2 * (1 - self._normal_cdf(abs(z)))

        significant = p_value < (1 - CONFIDENCE_THRESHOLD)
        lift = ((max(p1, p2) - min(p1, p2)) / min(p1, p2) * 100) if min(p1, p2) > 0 else 0

        winner = None
        if significant:
            winner = "A" if p1 > p2 else "B"

        return TestResult(
            significant=significant,
            p_value=p_value,
            winner=winner,
            lift=round(lift, 2),
            confidence=round(1 - p_value, 4),
            sample_sizes={"A": n1, "B": n2},
        )

    @staticmethod
    def _normal_cdf(x: float) -> float:
        """Approximate standard normal CDF (Abramowitz & Stegun)."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    @staticmethod
    def _generate_learning(
        test: Dict, winner: str, lift: float, groups: Dict
    ) -> str:
        """Generate a human-readable learning from test results."""
        test_type = test.get("test_type", "unknown")
        platform = test.get("platform", "unknown")
        name = test.get("name", "")

        winner_data = groups.get(winner, {})
        loser = [l for l in groups if l != winner]
        loser_label = loser[0] if loser else "?"

        if test_type == "caption":
            return (
                f"Variant {winner} caption outperformed Variant {loser_label} by {lift:.1f}% "
                f"on {platform.title()} (ER: {winner_data.get('engagement_rate', 0):.4f}). "
                f"Test: {name}"
            )
        elif test_type == "hook":
            return (
                f"Hook variant {winner} got {lift:.1f}% more engagement than {loser_label} "
                f"on {platform.title()}. Test: {name}"
            )
        elif test_type == "time":
            return (
                f"Posting time variant {winner} outperformed {loser_label} by {lift:.1f}% "
                f"on {platform.title()}. Test: {name}"
            )
        else:
            return (
                f"Variant {winner} won with {lift:.1f}% lift on {platform.title()}. "
                f"Test: {name}"
            )
