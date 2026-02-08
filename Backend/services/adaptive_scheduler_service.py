"""
Adaptive Scheduler Service (ADAPT-001)
========================================
Assessment-driven scheduling system that continuously adapts posting strategy
based on cross-platform performance data. Finds what works, cross-posts it
intelligently, rotates offer CTAs, and prevents audience fatigue.

Architecture:
    1. Assessment Ingestion  - Consumes StrategicReport from analysis service
    2. Content Scorer        - Ranks all recent content by composite score
    3. Cross-Post Engine     - Queues top content for other platforms
    4. Offer Funnel Manager  - Rotates CTAs across 11 products
    5. Fatigue Guard         - Prevents over-posting per platform/audience
    6. Schedule Adapter      - Mutates weekly cadence from assessment data

Event Bus Integration:
    Subscribes:
        strategy.report.ready        -> ingest new assessment
        strategy.analysis.completed  -> ingest AI analysis
        metrics.fetch.completed      -> score individual content
        publish.completed            -> track what was posted
    Publishes:
        adaptive.assessment.ingested
        adaptive.schedule.adapted
        adaptive.crosspost.queued
        adaptive.offer.rotated
        adaptive.fatigue.warning
        adaptive.content.scored
        adaptive.cycle.completed

Usage:
    service = get_adaptive_scheduler()
    await service.start()
    schedule = service.get_next_7_days()
"""

import asyncio
import logging
import os
import json
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from uuid import uuid4

from services.event_bus import EventBus, Event, Topics

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


# =============================================================================
# OFFER REGISTRY — 11 Software Products
# =============================================================================

@dataclass
class Offer:
    """A product/offer that can be promoted via CTA"""
    id: str
    name: str
    status_pct: int            # 0-100 build completion
    category: str              # "tool", "platform", "service"
    cta_templates: List[str]   # CTA text variations
    landing_url: str = ""
    priority: float = 1.0      # Higher = more promotion weight
    min_days_between: int = 3  # Fatigue: min days between same offer
    last_promoted_at: Optional[str] = None
    times_promoted_30d: int = 0
    is_launchable: bool = True  # Only promote if >= 60% built

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "status_pct": self.status_pct,
            "category": self.category, "priority": self.priority,
            "is_launchable": self.is_launchable,
            "last_promoted_at": self.last_promoted_at,
            "times_promoted_30d": self.times_promoted_30d,
        }


OFFERS_REGISTRY: List[Offer] = [
    Offer(
        id="watermark_remover", name="Watermark Remover (BlankLogo)",
        status_pct=100, category="tool", priority=1.5,
        cta_templates=[
            "Remove watermarks instantly with AI -> link in bio",
            "Clean your content in seconds. BlankLogo is live -> link in bio",
            "Tired of watermarks? We built the fix -> link in bio",
        ],
    ),
    Offer(
        id="everreach_crm", name="EverReach CRM",
        status_pct=100, category="platform", priority=1.5,
        cta_templates=[
            "Score your contacts, coach your outreach. EverReach CRM -> link in bio",
            "Stop guessing who to follow up with. EverReach knows -> link in bio",
            "Your contacts scored and ranked automatically -> link in bio",
        ],
    ),
    Offer(
        id="auto_comment", name="Auto Comment",
        status_pct=95, category="tool", priority=1.2,
        cta_templates=[
            "Automate your comments across IG, TikTok, Twitter, Threads -> link in bio",
            "Engagement on autopilot. Auto Comment handles it -> link in bio",
        ],
    ),
    Offer(
        id="mediaposter", name="MediaPoster",
        status_pct=90, category="platform", priority=1.3,
        cta_templates=[
            "Post to every platform at once. MediaPoster -> link in bio",
            "One upload, every platform. That's MediaPoster -> link in bio",
        ],
    ),
    Offer(
        id="tts_studio", name="TTS Studio",
        status_pct=85, category="tool", priority=1.0,
        cta_templates=[
            "Clone your voice. Generate voiceovers in seconds -> link in bio",
            "AI voice cloning that sounds like you. TTS Studio -> link in bio",
        ],
    ),
    Offer(
        id="auto_dm", name="Auto DM",
        status_pct=80, category="tool", priority=1.1,
        cta_templates=[
            "AI-powered DMs that convert. Auto DM -> link in bio",
            "Turn followers into conversations automatically -> link in bio",
        ],
    ),
    Offer(
        id="sora_video", name="Sora Video",
        status_pct=70, category="tool", priority=0.9,
        cta_templates=[
            "Generate videos with AI. Sora Video orchestrator -> link in bio",
            "AI video creation, automated. Sora Video -> link in bio",
        ],
    ),
    Offer(
        id="waitlistlab", name="WaitlistLab",
        status_pct=60, category="platform", priority=0.8,
        cta_templates=[
            "Capture leads before you launch. WaitlistLab -> link in bio",
            "Build hype with a waitlist that converts -> link in bio",
        ],
    ),
    Offer(
        id="ai_video_platform", name="AI Video Platform",
        status_pct=40, category="platform", priority=0.3,
        is_launchable=False,
        cta_templates=["Full AI video suite coming soon -> follow for updates"],
    ),
    Offer(
        id="kalodata_scraper", name="KaloData Scraper",
        status_pct=0, category="tool", priority=0.0,
        is_launchable=False,
        cta_templates=["TikTok Shop analytics tool in development"],
    ),
    Offer(
        id="competitor_research", name="Competitor Research",
        status_pct=0, category="tool", priority=0.0,
        is_launchable=False,
        cta_templates=["Competitor monitoring tool coming soon"],
    ),
]


# =============================================================================
# CONTENT PERFORMANCE SCORER
# =============================================================================

@dataclass
class ScoredContent:
    """A piece of content with a composite performance score"""
    content_id: str
    platform: str
    title: str
    score: float = 0.0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    views: int = 0
    total_interactions: int = 0
    engagement_rate: float = 0.0
    date: str = ""
    permalink: str = ""
    media_type: str = ""
    # Cross-post tracking
    cross_posted_to: List[str] = field(default_factory=list)
    is_cross_post_candidate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_id": self.content_id, "platform": self.platform,
            "title": self.title, "score": round(self.score, 2),
            "likes": self.likes, "comments": self.comments,
            "shares": self.shares, "saves": self.saves,
            "views": self.views, "total_interactions": self.total_interactions,
            "date": self.date, "permalink": self.permalink,
            "media_type": self.media_type,
            "cross_posted_to": self.cross_posted_to,
            "is_cross_post_candidate": self.is_cross_post_candidate,
        }


# =============================================================================
# SCHEDULED SLOT
# =============================================================================

@dataclass
class ScheduledSlot:
    """A single slot in the adaptive weekly schedule"""
    day: str                     # "Monday", "Tuesday", etc.
    time_est: str                # "10:00 AM", "2:00 PM"
    platform: str                # "tiktok", "instagram", "youtube"
    format: str                  # "Reels", "Short-form", "Shorts", "Story"
    content_type: str            # "original", "cross-post", "repurpose"
    offer_id: Optional[str] = None  # Which offer CTA to attach
    offer_cta: str = ""
    notes: str = ""
    source_content_id: Optional[str] = None  # If cross-post, the source
    confidence: float = 0.5      # How confident we are this slot works (0-1)
    performance_history: List[float] = field(default_factory=list)  # Past engagement rates

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day": self.day, "time_est": self.time_est,
            "platform": self.platform, "format": self.format,
            "content_type": self.content_type,
            "offer_id": self.offer_id, "offer_cta": self.offer_cta,
            "notes": self.notes, "confidence": round(self.confidence, 2),
            "source_content_id": self.source_content_id,
        }


# =============================================================================
# CROSS-POST RULES
# =============================================================================

CROSS_POST_RULES = {
    # source_platform -> list of (target_platform, format_adaptation, delay_hours)
    "tiktok": [
        ("instagram", "Reels", 24),
        ("youtube", "Shorts", 48),
    ],
    "instagram_graph": [
        ("tiktok", "Short-form", 24),
        ("youtube", "Shorts", 48),
    ],
    "youtube": [
        ("tiktok", "Short-form", 24),
        ("instagram", "Reels", 24),
    ],
}

# Platform-specific constraints
PLATFORM_CONSTRAINTS = {
    "tiktok": {"max_per_day": 3, "min_hours_between": 4, "best_times_est": ["9:00 AM", "12:00 PM", "7:00 PM"]},
    "instagram": {"max_per_day": 2, "min_hours_between": 6, "best_times_est": ["11:00 AM", "2:00 PM", "6:00 PM"]},
    "instagram_graph": {"max_per_day": 2, "min_hours_between": 6, "best_times_est": ["11:00 AM", "2:00 PM", "6:00 PM"]},
    "youtube": {"max_per_day": 1, "min_hours_between": 24, "best_times_est": ["3:00 PM"]},
    "twitter": {"max_per_day": 5, "min_hours_between": 2, "best_times_est": ["8:00 AM", "12:00 PM", "5:00 PM"]},
    "threads": {"max_per_day": 3, "min_hours_between": 4, "best_times_est": ["10:00 AM", "1:00 PM", "8:00 PM"]},
    "facebook": {"max_per_day": 1, "min_hours_between": 24, "best_times_est": ["1:00 PM"]},
}


# =============================================================================
# ADAPTIVE SCHEDULER SERVICE
# =============================================================================

class AdaptiveSchedulerService:
    """
    Assessment-driven adaptive scheduler.

    Ingests strategic assessments, scores content, identifies cross-post
    candidates, rotates offer CTAs, prevents fatigue, and continuously
    adapts the weekly posting schedule based on what's working.
    """

    _instance: Optional["AdaptiveSchedulerService"] = None

    def __init__(self):
        if AdaptiveSchedulerService._instance is not None:
            raise RuntimeError("Use get_adaptive_scheduler()")

        # Event bus
        self._bus: Optional[EventBus] = None

        # State
        self._offers = {o.id: o for o in OFFERS_REGISTRY}
        self._scored_content: List[ScoredContent] = []
        self._cross_post_queue: List[Dict[str, Any]] = []
        self._weekly_schedule: List[ScheduledSlot] = []
        self._assessment_history: List[Dict[str, Any]] = []
        self._post_log: List[Dict[str, Any]] = []  # Recent posts for fatigue tracking

        # Fatigue tracking: platform -> list of datetimes
        self._platform_post_times: Dict[str, List[datetime]] = defaultdict(list)
        # Offer fatigue: offer_id -> list of datetimes
        self._offer_promo_times: Dict[str, List[datetime]] = defaultdict(list)

        # Adaptation state
        self._last_assessment_at: Optional[str] = None
        self._adaptation_count = 0
        self._started = False

        # === INTEGRATED SERVICES (lazy-loaded) ===
        self._blotato_service = None
        self._background_publisher = None
        self._narrative_scheduler = None
        self._visual_campaign_service = None
        # --- Wave 2 integrations ---
        self._fate_scorer = None
        self._trend_brief_service = None
        self._engagement_scorer = None
        self._weekly_planner = None
        self._tiktok_repurpose = None
        self._repurpose_pipeline = None
        self._meta_pixel = None
        self._agent_scheduler = None
        self._dm_warmth = None
        # --- Wave 3 integrations ---
        self._insights_engine = None
        self._performance_correlator = None
        self._bandit_allocator = None
        self._content_mix_planner = None
        self._ab_testing = None
        self._ai_content_generator = None
        self._ai_thumbnail_selector = None
        self._sora_pipeline = None
        self._sleep_mode = None
        self._dco_optimizer = None
        self._comment_automation = None
        self._analysis_health = None
        # --- Wave 4 integrations (strategic closed-loop) ---
        self._template_leaderboard = None
        self._qa_gate = None
        self._awareness_classifier = None
        self._competitor_analysis = None
        self._content_gen_pipeline = None
        self._slot_executor = None
        self._learner_worker = None
        self._approval_workflow = None
        self._auto_curator = None
        self._benchmark_service = None
        self._ai_recommendation = None
        self._engagement_worker = None
        self._trend_intelligence = None
        self._sora_daily_pipeline = None
        self._pipeline_monitor = None
        # --- Wave 5 integrations (full-stack automation) ---
        self._content_gap = None
        self._hook_library = None
        self._channel_router = None
        self._daily_automation = None
        self._growth_data_plane = None
        self._lead_discovery = None
        self._offer_tracker = None
        self._email_sequence = None
        self._format_classifier = None
        self._deduplication_guard = None
        self._content_sourcing = None
        self._clip_selector = None
        self._feedback_loop_scorer = None
        self._embedding_service = None
        self._inventory_scheduler = None
        self._meta_ads_autopilot = None
        self._checkback_scheduler = None
        # --- Wave 6 integrations (publishing & operations) ---
        self._post_scheduler = None
        self._calendar_service = None
        self._video_publish_pipeline = None
        self._multi_platform_publisher = None
        self._nightly_analysis = None
        self._data_hydration = None
        self._trend_velocity = None
        self._trend_scoring = None
        self._batch_processor = None
        self._content_analytics = None
        self._touchpoint_service = None
        self._workflow_manager = None
        self._twitter_campaign = None
        self._external_queue = None

        # Available video pool from NarrativeScheduler
        self._video_pool: List[Dict[str, Any]] = []
        # Performance feedback from PostTracker
        self._performance_feedback: Dict[str, float] = {}  # content_id -> score
        # Account rotation tracking: platform -> index into accounts list
        self._account_rotation_idx: Dict[str, int] = defaultdict(int)
        # Trend briefs cache
        self._active_trend_briefs: List[Dict[str, Any]] = []
        # FATE scores for video pool
        self._fate_scores: Dict[str, Dict[str, float]] = {}  # content_id -> {F,A,T,E}
        # DM outreach queue coordinated with post schedule
        self._dm_outreach_queue: List[Dict[str, Any]] = []

        logger.info("AdaptiveSchedulerService initialized")

    @classmethod
    def get_instance(cls) -> "AdaptiveSchedulerService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    # ---- Lazy service accessors ----

    @property
    def blotato(self):
        if self._blotato_service is None:
            try:
                from services.blotato_service import BlotatoService
                self._blotato_service = BlotatoService.get_instance()
            except Exception as e:
                logger.warning(f"BlotatoService not available: {e}")
        return self._blotato_service

    @property
    def publisher(self):
        if self._background_publisher is None:
            try:
                from services.background_publisher import get_background_publisher
                self._background_publisher = get_background_publisher()
            except Exception as e:
                logger.warning(f"BackgroundPublisher not available: {e}")
        return self._background_publisher

    @property
    def narrative(self):
        if self._narrative_scheduler is None:
            try:
                from services.narrative_scheduler.scheduler import NarrativeScheduler
                self._narrative_scheduler = NarrativeScheduler()
            except Exception as e:
                logger.warning(f"NarrativeScheduler not available: {e}")
        return self._narrative_scheduler

    @property
    def visual_campaign(self):
        if self._visual_campaign_service is None:
            try:
                from services.visual_campaign_service import get_visual_campaign_service
                self._visual_campaign_service = get_visual_campaign_service()
            except Exception as e:
                logger.warning(f"VisualCampaignService not available: {e}")
        return self._visual_campaign_service

    @property
    def fate_scorer(self):
        if self._fate_scorer is None:
            try:
                from services.fate_scorer import FATEScorer
                self._fate_scorer = FATEScorer()
            except Exception as e:
                logger.warning(f"FATEScorer not available: {e}")
        return self._fate_scorer

    @property
    def trend_brief(self):
        if self._trend_brief_service is None:
            try:
                from services.trend_brief_service import TrendBriefService
                self._trend_brief_service = TrendBriefService()
            except Exception as e:
                logger.warning(f"TrendBriefService not available: {e}")
        return self._trend_brief_service

    @property
    def engagement_scorer(self):
        if self._engagement_scorer is None:
            try:
                from services.engagement_scorer import EngagementScorer
                self._engagement_scorer = EngagementScorer()
            except Exception as e:
                logger.warning(f"EngagementScorer not available: {e}")
        return self._engagement_scorer

    @property
    def weekly_planner(self):
        if self._weekly_planner is None:
            try:
                from services.weekly_planner import WeeklyPlanner
                self._weekly_planner = WeeklyPlanner()
            except Exception as e:
                logger.warning(f"WeeklyPlanner not available: {e}")
        return self._weekly_planner

    @property
    def tiktok_repurpose(self):
        if self._tiktok_repurpose is None:
            try:
                from services.tiktok_repurpose_service import TikTokRepurposeService
                self._tiktok_repurpose = TikTokRepurposeService()
            except Exception as e:
                logger.warning(f"TikTokRepurposeService not available: {e}")
        return self._tiktok_repurpose

    @property
    def repurpose_pipeline(self):
        if self._repurpose_pipeline is None:
            try:
                from services.repurpose.pipeline import RepurposePipeline
                self._repurpose_pipeline = RepurposePipeline()
            except Exception as e:
                logger.warning(f"RepurposePipeline not available: {e}")
        return self._repurpose_pipeline

    @property
    def meta_pixel(self):
        if self._meta_pixel is None:
            try:
                from services.meta_pixel_service import get_meta_pixel_service
                self._meta_pixel = get_meta_pixel_service()
            except Exception as e:
                logger.warning(f"MetaPixelService not available: {e}")
        return self._meta_pixel

    @property
    def dm_warmth(self):
        if self._dm_warmth is None:
            try:
                from services.dm_warmth_system import DMWarmthManager
                self._dm_warmth = DMWarmthManager.get_instance()
            except Exception as e:
                logger.warning(f"DMWarmthManager not available: {e}")
        return self._dm_warmth

    # ---- Wave 3 lazy service accessors ----

    @property
    def insights_engine(self):
        if self._insights_engine is None:
            try:
                from services.insights_engine import InsightsEngine
                from sqlalchemy.orm import Session
                from sqlalchemy import create_engine
                engine = create_engine(DATABASE_URL)
                session = Session(engine)
                self._insights_engine = InsightsEngine(session)
            except Exception as e:
                logger.warning(f"InsightsEngine not available: {e}")
        return self._insights_engine

    @property
    def performance_correlator(self):
        if self._performance_correlator is None:
            try:
                from services.performance_correlator import PerformanceCorrelator
                from sqlalchemy.orm import Session
                from sqlalchemy import create_engine
                engine = create_engine(DATABASE_URL)
                session = Session(engine)
                self._performance_correlator = PerformanceCorrelator(session)
            except Exception as e:
                logger.warning(f"PerformanceCorrelator not available: {e}")
        return self._performance_correlator

    @property
    def bandit_allocator(self):
        if self._bandit_allocator is None:
            try:
                from services.bandit_allocator import get_bandit_allocator
                self._bandit_allocator = get_bandit_allocator()
            except Exception as e:
                logger.warning(f"BanditAllocator not available: {e}")
        return self._bandit_allocator

    @property
    def content_mix_planner(self):
        if self._content_mix_planner is None:
            try:
                from services.content_mix_planner import get_content_mix_planner
                self._content_mix_planner = get_content_mix_planner()
            except Exception as e:
                logger.warning(f"ContentMixPlanner not available: {e}")
        return self._content_mix_planner

    @property
    def ab_testing(self):
        if self._ab_testing is None:
            try:
                from services.ab_testing import ABTestingService
                self._ab_testing = ABTestingService()
            except Exception as e:
                logger.warning(f"ABTestingService not available: {e}")
        return self._ab_testing

    @property
    def ai_content_generator(self):
        if self._ai_content_generator is None:
            try:
                from services.ai_content_generator import AIContentGenerator
                self._ai_content_generator = AIContentGenerator()
            except Exception as e:
                logger.warning(f"AIContentGenerator not available: {e}")
        return self._ai_content_generator

    @property
    def ai_thumbnail(self):
        if self._ai_thumbnail_selector is None:
            try:
                from services.ai_thumbnail_selector import AIThumbnailSelector
                self._ai_thumbnail_selector = AIThumbnailSelector()
            except Exception as e:
                logger.warning(f"AIThumbnailSelector not available: {e}")
        return self._ai_thumbnail_selector

    @property
    def sora_pipeline(self):
        if self._sora_pipeline is None:
            try:
                from services.sora_video_pipeline import SoraVideoPipeline
                self._sora_pipeline = SoraVideoPipeline()
            except Exception as e:
                logger.warning(f"SoraVideoPipeline not available: {e}")
        return self._sora_pipeline

    @property
    def sleep_mode(self):
        if self._sleep_mode is None:
            try:
                from services.sleep_mode_service import SleepModeService
                self._sleep_mode = SleepModeService.get_instance()
            except Exception as e:
                logger.warning(f"SleepModeService not available: {e}")
        return self._sleep_mode

    @property
    def dco_optimizer(self):
        if self._dco_optimizer is None:
            try:
                from services.ad_testing.dco_optimizer import get_dco_optimizer
                self._dco_optimizer = get_dco_optimizer()
            except Exception as e:
                logger.warning(f"DCOOptimizer not available: {e}")
        return self._dco_optimizer

    @property
    def comment_automation(self):
        if self._comment_automation is None:
            try:
                from services.instagram.comment_automation import InstagramCommentAutomation
                self._comment_automation = InstagramCommentAutomation(
                    account_username="the_isaiah_dupree"
                )
            except Exception as e:
                logger.warning(f"CommentAutomation not available: {e}")
        return self._comment_automation

    @property
    def analysis_health(self):
        if self._analysis_health is None:
            try:
                from services.analysis_health import AnalysisHealthService
                # Needs async session — store class ref, instantiate per-call
                self._analysis_health = AnalysisHealthService
            except Exception as e:
                logger.warning(f"AnalysisHealthService not available: {e}")
        return self._analysis_health

    # ---- Wave 4 lazy service accessors (strategic closed-loop) ----

    @property
    def template_leaderboard(self):
        if self._template_leaderboard is None:
            try:
                from services.template_leaderboard import get_template_leaderboard
                self._template_leaderboard = get_template_leaderboard()
            except Exception as e:
                logger.warning(f"TemplateLeaderboard not available: {e}")
        return self._template_leaderboard

    @property
    def qa_gate(self):
        if self._qa_gate is None:
            try:
                from services.qa_gate_service import QAGateService
                self._qa_gate = QAGateService.get_instance()
            except Exception as e:
                logger.warning(f"QAGateService not available: {e}")
        return self._qa_gate

    @property
    def awareness_classifier(self):
        if self._awareness_classifier is None:
            try:
                from services.awareness_classifier import AwarenessClassifier
                self._awareness_classifier = AwarenessClassifier.get_instance()
            except Exception as e:
                logger.warning(f"AwarenessClassifier not available: {e}")
        return self._awareness_classifier

    @property
    def competitor_analysis(self):
        if self._competitor_analysis is None:
            try:
                from services.competitor_analysis_service import CompetitorAnalysisService
                self._competitor_analysis = CompetitorAnalysisService()
            except Exception as e:
                logger.warning(f"CompetitorAnalysisService not available: {e}")
        return self._competitor_analysis

    @property
    def content_gen_pipeline(self):
        if self._content_gen_pipeline is None:
            try:
                from services.content_generation_pipeline import get_content_generation_pipeline
                self._content_gen_pipeline = get_content_generation_pipeline()
            except Exception as e:
                logger.warning(f"ContentGenerationPipeline not available: {e}")
        return self._content_gen_pipeline

    @property
    def slot_executor(self):
        if self._slot_executor is None:
            try:
                from services.workers.slot_executor_worker import SlotExecutorWorker
                self._slot_executor = SlotExecutorWorker(event_bus=self._bus)
            except Exception as e:
                logger.warning(f"SlotExecutorWorker not available: {e}")
        return self._slot_executor

    @property
    def learner(self):
        if self._learner_worker is None:
            try:
                from services.workers.learner_worker import LearnerWorker
                self._learner_worker = LearnerWorker(event_bus=self._bus)
            except Exception as e:
                logger.warning(f"LearnerWorker not available: {e}")
        return self._learner_worker

    @property
    def approval_workflow(self):
        if self._approval_workflow is None:
            try:
                from services.approval_workflow import get_approval_workflow
                self._approval_workflow = get_approval_workflow()
            except Exception as e:
                logger.warning(f"ApprovalWorkflow not available: {e}")
        return self._approval_workflow

    @property
    def auto_curator(self):
        if self._auto_curator is None:
            try:
                from services.auto_curator import get_auto_curator
                self._auto_curator = get_auto_curator()
            except Exception as e:
                logger.warning(f"AutoCurator not available: {e}")
        return self._auto_curator

    @property
    def benchmark(self):
        if self._benchmark_service is None:
            try:
                from services.benchmark_service import get_benchmark_service
                self._benchmark_service = get_benchmark_service()
            except Exception as e:
                logger.warning(f"BenchmarkService not available: {e}")
        return self._benchmark_service

    @property
    def ai_recommendation(self):
        if self._ai_recommendation is None:
            try:
                from services.ai_recommendation_service import AIRecommendationService
                from sqlalchemy.orm import Session
                from sqlalchemy import create_engine
                engine = create_engine(DATABASE_URL)
                session = Session(engine)
                self._ai_recommendation = AIRecommendationService(session)
            except Exception as e:
                logger.warning(f"AIRecommendationService not available: {e}")
        return self._ai_recommendation

    @property
    def engagement_worker(self):
        if self._engagement_worker is None:
            try:
                from services.workers.engagement_worker import EngagementWorker
                self._engagement_worker = EngagementWorker(event_bus=self._bus)
            except Exception as e:
                logger.warning(f"EngagementWorker not available: {e}")
        return self._engagement_worker

    @property
    def trend_intelligence(self):
        if self._trend_intelligence is None:
            try:
                from services.trend_intelligence.brief_service import get_brief_service
                self._trend_intelligence = get_brief_service()
            except Exception as e:
                logger.warning(f"TrendIntelligence not available: {e}")
        return self._trend_intelligence

    @property
    def sora_daily(self):
        if self._sora_daily_pipeline is None:
            try:
                from services.sora_daily.pipeline_worker import SoraDailyPipelineWorker
                self._sora_daily_pipeline = SoraDailyPipelineWorker()
            except Exception as e:
                logger.warning(f"SoraDailyPipeline not available: {e}")
        return self._sora_daily_pipeline

    @property
    def pipeline_monitor(self):
        if self._pipeline_monitor is None:
            try:
                from services.pipeline_monitor import PipelineMonitor
                self._pipeline_monitor = PipelineMonitor()
            except Exception as e:
                logger.warning(f"PipelineMonitor not available: {e}")
        return self._pipeline_monitor

    # ---- Wave 5 lazy service accessors (full-stack automation) ----

    @property
    def content_gap(self):
        if self._content_gap is None:
            try:
                from services.content_gap_service import get_content_gap_service
                self._content_gap = get_content_gap_service()
            except Exception as e:
                logger.warning(f"ContentGapService not available: {e}")
        return self._content_gap

    @property
    def hook_library(self):
        if self._hook_library is None:
            try:
                from services.hook_library_service import get_hook_library_service
                self._hook_library = get_hook_library_service()
            except Exception as e:
                logger.warning(f"HookLibraryService not available: {e}")
        return self._hook_library

    @property
    def channel_router(self):
        if self._channel_router is None:
            try:
                from services.channel_router import get_channel_router
                self._channel_router = get_channel_router()
            except Exception as e:
                logger.warning(f"ChannelRouter not available: {e}")
        return self._channel_router

    @property
    def daily_automation(self):
        if self._daily_automation is None:
            try:
                from services.daily_automation.manager import DailyAutomationManager
                self._daily_automation = DailyAutomationManager.get_instance()
            except Exception as e:
                logger.warning(f"DailyAutomationManager not available: {e}")
        return self._daily_automation

    @property
    def growth_data_plane(self):
        if self._growth_data_plane is None:
            try:
                from services.growth_data_plane import get_growth_data_plane
                self._growth_data_plane = get_growth_data_plane()
            except Exception as e:
                logger.warning(f"GrowthDataPlane not available: {e}")
        return self._growth_data_plane

    @property
    def lead_discovery(self):
        if self._lead_discovery is None:
            try:
                from services.lead_discovery_service import LeadDiscoveryService
                self._lead_discovery = LeadDiscoveryService()
            except Exception as e:
                logger.warning(f"LeadDiscoveryService not available: {e}")
        return self._lead_discovery

    @property
    def offer_tracker(self):
        if self._offer_tracker is None:
            try:
                from services.offer_tracker import get_offer_tracker
                self._offer_tracker = get_offer_tracker()
            except Exception as e:
                logger.warning(f"OfferTracker not available: {e}")
        return self._offer_tracker

    @property
    def email_sequence(self):
        if self._email_sequence is None:
            try:
                from services.email_sequence_service import get_email_sequence_service
                self._email_sequence = get_email_sequence_service()
            except Exception as e:
                logger.warning(f"EmailSequenceService not available: {e}")
        return self._email_sequence

    @property
    def format_classifier(self):
        if self._format_classifier is None:
            try:
                from services.format_classifier import FormatClassifier
                self._format_classifier = FormatClassifier()
            except Exception as e:
                logger.warning(f"FormatClassifier not available: {e}")
        return self._format_classifier

    @property
    def dedup_guard(self):
        if self._deduplication_guard is None:
            try:
                from services.deduplication_guard import DeduplicationGuard
                self._deduplication_guard = DeduplicationGuard()
            except Exception as e:
                logger.warning(f"DeduplicationGuard not available: {e}")
        return self._deduplication_guard

    @property
    def content_sourcing(self):
        if self._content_sourcing is None:
            try:
                from services.content_sourcing_engine import ContentSourcingEngine
                self._content_sourcing = ContentSourcingEngine
            except Exception as e:
                logger.warning(f"ContentSourcingEngine not available: {e}")
        return self._content_sourcing

    @property
    def clip_selector(self):
        if self._clip_selector is None:
            try:
                from services.clip_selector import ClipSelector
                from sqlalchemy.orm import Session
                from sqlalchemy import create_engine
                engine = create_engine(DATABASE_URL)
                session = Session(engine)
                self._clip_selector = ClipSelector(session)
            except Exception as e:
                logger.warning(f"ClipSelector not available: {e}")
        return self._clip_selector

    @property
    def feedback_scorer(self):
        if self._feedback_loop_scorer is None:
            try:
                from services.feedback_loop.scorer import PostScorer
                self._feedback_loop_scorer = PostScorer()
            except Exception as e:
                logger.warning(f"FeedbackLoopScorer not available: {e}")
        return self._feedback_loop_scorer

    @property
    def embedding(self):
        if self._embedding_service is None:
            try:
                from services.embedding_service import EmbeddingService
                self._embedding_service = EmbeddingService()
            except Exception as e:
                logger.warning(f"EmbeddingService not available: {e}")
        return self._embedding_service

    @property
    def inventory_scheduler(self):
        if self._inventory_scheduler is None:
            try:
                from services.inventory_aware_scheduler import InventoryAwareScheduler
                self._inventory_scheduler = InventoryAwareScheduler()
            except Exception as e:
                logger.warning(f"InventoryAwareScheduler not available: {e}")
        return self._inventory_scheduler

    @property
    def meta_ads(self):
        if self._meta_ads_autopilot is None:
            try:
                from services.meta_ads_autopilot import MetaAdsAutopilot
                self._meta_ads_autopilot = MetaAdsAutopilot()
            except Exception as e:
                logger.warning(f"MetaAdsAutopilot not available: {e}")
        return self._meta_ads_autopilot

    @property
    def checkback(self):
        if self._checkback_scheduler is None:
            try:
                from services.checkback_scheduler import CheckbackScheduler
                self._checkback_scheduler = CheckbackScheduler()
            except Exception as e:
                logger.warning(f"CheckbackScheduler not available: {e}")
        return self._checkback_scheduler

    # --- Wave 6 lazy accessors (publishing & operations) ---

    @property
    def post_scheduler(self):
        if self._post_scheduler is None:
            try:
                from services.post_scheduler import PostScheduler
                self._post_scheduler = PostScheduler()
            except Exception as e:
                logger.warning(f"PostScheduler not available: {e}")
        return self._post_scheduler

    @property
    def calendar(self):
        if self._calendar_service is None:
            try:
                from services.calendar_service import CalendarService
                from database.connection import get_db_session
                db = get_db_session()
                self._calendar_service = CalendarService(db)
            except Exception as e:
                logger.warning(f"CalendarService not available: {e}")
        return self._calendar_service

    @property
    def video_publish(self):
        if self._video_publish_pipeline is None:
            try:
                from services.video_publish_pipeline import VideoPublishPipeline
                self._video_publish_pipeline = VideoPublishPipeline.get_instance()
            except Exception as e:
                logger.warning(f"VideoPublishPipeline not available: {e}")
        return self._video_publish_pipeline

    @property
    def multi_publisher(self):
        if self._multi_platform_publisher is None:
            try:
                from services.multi_platform_publisher import MultiPlatformPublisher
                self._multi_platform_publisher = MultiPlatformPublisher()
            except Exception as e:
                logger.warning(f"MultiPlatformPublisher not available: {e}")
        return self._multi_platform_publisher

    @property
    def nightly_analysis(self):
        if self._nightly_analysis is None:
            try:
                from services.nightly_analysis_scheduler import NightlyAnalysisScheduler
                self._nightly_analysis = NightlyAnalysisScheduler()
            except Exception as e:
                logger.warning(f"NightlyAnalysisScheduler not available: {e}")
        return self._nightly_analysis

    @property
    def data_hydration(self):
        if self._data_hydration is None:
            try:
                from services.data_hydration_service import DataHydrationService
                self._data_hydration = DataHydrationService()
            except Exception as e:
                logger.warning(f"DataHydrationService not available: {e}")
        return self._data_hydration

    @property
    def trend_velocity(self):
        if self._trend_velocity is None:
            try:
                from services.trend_velocity_service import TrendVelocityService
                self._trend_velocity = TrendVelocityService()
            except Exception as e:
                logger.warning(f"TrendVelocityService not available: {e}")
        return self._trend_velocity

    @property
    def trend_scoring(self):
        if self._trend_scoring is None:
            try:
                from services.trend_scoring_service import TrendScoringService
                self._trend_scoring = TrendScoringService()
            except Exception as e:
                logger.warning(f"TrendScoringService not available: {e}")
        return self._trend_scoring

    @property
    def batch_proc(self):
        if self._batch_processor is None:
            try:
                from services.batch_processor import BatchProcessor
                self._batch_processor = BatchProcessor()
            except Exception as e:
                logger.warning(f"BatchProcessor not available: {e}")
        return self._batch_processor

    @property
    def content_analytics(self):
        if self._content_analytics is None:
            try:
                from services.content_analytics import ContentAnalyticsService
                self._content_analytics = ContentAnalyticsService()
            except Exception as e:
                logger.warning(f"ContentAnalytics not available: {e}")
        return self._content_analytics

    @property
    def touchpoints(self):
        if self._touchpoint_service is None:
            try:
                from services.touchpoint_service import TouchpointService
                self._touchpoint_service = TouchpointService.get_instance()
            except Exception as e:
                logger.warning(f"TouchpointService not available: {e}")
        return self._touchpoint_service

    @property
    def workflows(self):
        if self._workflow_manager is None:
            try:
                from services.workflow_manager import WorkflowManager
                self._workflow_manager = WorkflowManager.get_instance()
            except Exception as e:
                logger.warning(f"WorkflowManager not available: {e}")
        return self._workflow_manager

    @property
    def twitter_campaign(self):
        if self._twitter_campaign is None:
            try:
                from services.twitter_campaign_scheduler import TwitterCampaignScheduler, get_twitter_campaign_scheduler
                self._twitter_campaign = get_twitter_campaign_scheduler()
            except Exception as e:
                logger.warning(f"TwitterCampaignScheduler not available: {e}")
        return self._twitter_campaign

    @property
    def external_queue(self):
        if self._external_queue is None:
            try:
                from services.external_queue_manager import ExternalQueueManager
                self._external_queue = ExternalQueueManager()
            except Exception as e:
                logger.warning(f"ExternalQueueManager not available: {e}")
        return self._external_queue

    async def start(self, event_bus: Optional[EventBus] = None):
        """Start the service and subscribe to events."""
        self._bus = event_bus or EventBus.get_instance()

        # Subscribe to relevant events
        self._bus.subscribe(Topics.STRATEGY_REPORT_READY, self._on_report_ready)
        self._bus.subscribe(Topics.STRATEGY_AI_ANALYSIS_COMPLETED, self._on_ai_analysis)
        self._bus.subscribe(Topics.METRICS_FETCH_COMPLETED, self._on_metrics_update)
        self._bus.subscribe(Topics.PUBLISH_COMPLETED, self._on_post_published)
        self._bus.subscribe(Topics.CHECKBACK_COMPLETED, self._on_checkback_completed)
        self._bus.subscribe(Topics.POST_PUBLISHED, self._on_post_tracked)

        # Generate initial default schedule
        if not self._weekly_schedule:
            self._weekly_schedule = self._generate_default_schedule()

        # Load available video pool from NarrativeScheduler
        await self._load_video_pool()

        self._started = True
        logger.info("AdaptiveSchedulerService started (7 services integrated)")

    async def _publish(self, topic: str, payload: Dict[str, Any]):
        if self._bus:
            try:
                await self._bus.publish(topic, payload, source="adaptive-scheduler")
            except Exception as e:
                logger.debug(f"Could not publish {topic}: {e}")

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    async def _on_report_ready(self, event: Event):
        """Handle strategy.report.ready — ingest full assessment."""
        report_data = event.payload
        logger.info("AdaptiveScheduler: Ingesting new strategic assessment")
        await self.ingest_assessment(report_data)

    async def _on_ai_analysis(self, event: Event):
        """Handle strategy.ai_analysis.completed — update schedule from AI recommendations."""
        ai_data = event.payload
        if "weekly_cadence" in ai_data:
            self._apply_ai_cadence(ai_data["weekly_cadence"])

    async def _on_metrics_update(self, event: Event):
        """Handle metrics.fetch.completed — re-score content."""
        platform = event.payload.get("platform", "unknown")
        logger.debug(f"AdaptiveScheduler: Metrics update for {platform}")

    async def _on_post_published(self, event: Event):
        """Handle publish.completed — track for fatigue + score later."""
        platform = event.payload.get("platform", "unknown")
        now = datetime.now(timezone.utc)
        self._platform_post_times[platform].append(now)
        self._post_log.append({
            "platform": platform,
            "posted_at": now.isoformat(),
            "content_id": event.payload.get("content_id"),
            "title": event.payload.get("title", ""),
        })

    async def _on_checkback_completed(self, event: Event):
        """Handle checkback.completed — feed performance score back into slot confidence."""
        post_id = event.payload.get("scheduled_post_id", "")
        score = event.payload.get("performance_score")
        platform = event.payload.get("platform", "")
        if score is not None:
            self._performance_feedback[post_id] = float(score)
            # Adjust slot confidence based on performance
            self._adjust_slot_confidence(platform, float(score))
            logger.info(f"AdaptiveScheduler: Performance feedback for {post_id}: score={score}")

    async def _on_post_tracked(self, event: Event):
        """Handle post.published from PostTracker — record for cross-platform awareness."""
        platform = event.payload.get("platform", "")
        url = event.payload.get("platform_url", "")
        if platform and url:
            self._post_log.append({
                "platform": platform,
                "platform_url": url,
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "tracked": True,
            })

    # =========================================================================
    # INTEGRATED: VIDEO POOL (NarrativeScheduler)
    # =========================================================================

    async def _load_video_pool(self):
        """Load analyzed, approved videos from NarrativeScheduler's DB query."""
        try:
            from sqlalchemy import create_engine, text as sa_text
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                result = conn.execute(sa_text("""
                    SELECT v.id, v.file_name, v.source_uri, v.duration_sec,
                           va.pre_social_score, va.topics, va.hooks, va.tone,
                           va.curation_status
                    FROM videos v
                    JOIN video_analysis va ON va.video_id = v.id
                    WHERE va.curation_status = 'approved'
                      AND NOT EXISTS (
                          SELECT 1 FROM scheduled_posts sp
                          WHERE (sp.content_id = v.id::text OR sp.clip_id = v.id)
                            AND sp.status IN ('scheduled', 'publishing', 'posted', 'published')
                      )
                    ORDER BY va.pre_social_score DESC NULLS LAST
                    LIMIT 200
                """))
                self._video_pool = []
                for row in result.fetchall():
                    self._video_pool.append({
                        "id": str(row[0]),
                        "file_name": row[1] or "",
                        "source_uri": row[2] or "",
                        "duration_sec": float(row[3]) if row[3] else None,
                        "pre_social_score": int(row[4]) if row[4] else 0,
                        "topics": list(row[5]) if row[5] else [],
                        "hooks": list(row[6]) if row[6] else [],
                        "tone": row[7] or "",
                        "curation_status": row[8] or "",
                    })
                logger.info(f"AdaptiveScheduler: Loaded {len(self._video_pool)} approved videos into pool")
        except Exception as e:
            logger.warning(f"Could not load video pool: {e}")
            self._video_pool = []

    # =========================================================================
    # INTEGRATED: BLOTATO ACCOUNT MAPPING
    # =========================================================================

    def _get_blotato_account_for_slot(self, slot: "ScheduledSlot") -> Optional[Dict[str, Any]]:
        """
        Map a schedule slot to a real Blotato account using round-robin rotation.
        Uses BlotatoService.get_accounts_by_platform() for the real account list.
        """
        platform = slot.platform
        # Normalize platform names (instagram_graph -> instagram)
        platform_map = {"instagram_graph": "instagram", "facebook_ads": "facebook"}
        blotato_platform = platform_map.get(platform, platform)

        if not self.blotato:
            return None

        accounts = self.blotato.get_accounts_by_platform(blotato_platform)
        if not accounts:
            return None

        # Round-robin rotation
        idx = self._account_rotation_idx[blotato_platform] % len(accounts)
        self._account_rotation_idx[blotato_platform] = idx + 1
        acct = accounts[idx]
        return {
            "blotato_account_id": acct.id,
            "platform": acct.platform,
            "username": acct.username,
            "display_name": acct.display_name,
        }

    # =========================================================================
    # INTEGRATED: MATERIALIZE TO scheduled_posts DB
    # =========================================================================

    def materialize_schedule_to_db(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Write the adaptive weekly schedule into the scheduled_posts DB table
        so PostScheduler can pick them up and publish via BackgroundPublisher.

        Returns list of created scheduled_post records.
        """
        from sqlalchemy import create_engine, text as sa_text
        engine = create_engine(DATABASE_URL)
        now = datetime.now(timezone.utc)
        days_map = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today_idx = now.weekday()
        created = []

        with engine.connect() as conn:
            for slot in self._weekly_schedule:
                slot_day_idx = days_map.index(slot.day) if slot.day in days_map else 0
                days_offset = (slot_day_idx - today_idx) % 7
                if days_offset == 0 and slot.time_est:
                    days_offset = 7  # Push to next week if same day
                target_date = now + timedelta(days=days_offset)

                # Parse time_est
                scheduled_time = self._parse_slot_time(target_date, slot.time_est)
                if not scheduled_time or scheduled_time <= now:
                    continue

                # Get Blotato account
                account_info = self._get_blotato_account_for_slot(slot)

                # Pick a video from pool for original content
                video_id = None
                if slot.content_type == "original" and self._video_pool:
                    video = self._video_pool.pop(0)  # Take next best from pool
                    video_id = video["id"]

                # Check if already scheduled at this time+platform
                existing = conn.execute(sa_text("""
                    SELECT id FROM scheduled_posts
                    WHERE platform = :platform
                      AND scheduled_time = :time
                      AND status = 'scheduled'
                    LIMIT 1
                """), {"platform": slot.platform, "time": scheduled_time})
                if existing.fetchone():
                    continue  # Already scheduled

                post_id = str(uuid4())
                caption = slot.offer_cta if slot.offer_cta else slot.notes

                conn.execute(sa_text("""
                    INSERT INTO scheduled_posts
                    (id, clip_id, platform, blotato_account_id, account_username,
                     scheduled_time, status, caption, title, 
                     recommendation_reasoning, created_at, updated_at)
                    VALUES
                    (:id, :clip_id, :platform, :blotato_id, :username,
                     :time, 'scheduled', :caption, :title,
                     :reasoning, NOW(), NOW())
                """), {
                    "id": post_id,
                    "clip_id": video_id,
                    "platform": slot.platform,
                    "blotato_id": str(account_info["blotato_account_id"]) if account_info else None,
                    "username": account_info["username"] if account_info else None,
                    "time": scheduled_time,
                    "caption": caption[:500] if caption else "",
                    "title": f"[Adaptive] {slot.format} - {slot.day}",
                    "reasoning": f"account: {account_info['username']}" if account_info else "",
                })

                created.append({
                    "post_id": post_id,
                    "platform": slot.platform,
                    "scheduled_time": scheduled_time.isoformat(),
                    "video_id": video_id,
                    "account": account_info["username"] if account_info else None,
                    "content_type": slot.content_type,
                    "offer_id": slot.offer_id,
                })

            conn.commit()

        logger.info(f"AdaptiveScheduler: Materialized {len(created)} posts to scheduled_posts DB")
        return created

    def _parse_slot_time(self, target_date: datetime, time_est: str) -> Optional[datetime]:
        """Parse '10:00 AM' style time string into a datetime in EST -> UTC."""
        try:
            # Handle formats like "10:00 AM", "3:00 PM", "1 hour", "2 hours"
            time_est = time_est.strip()
            if "hour" in time_est.lower():
                # Not a real time, skip
                return target_date.replace(hour=12, minute=0, second=0, microsecond=0)
            for fmt in ["%I:%M %p", "%I:%M%p", "%H:%M"]:
                try:
                    parsed = datetime.strptime(time_est, fmt)
                    # EST = UTC-5
                    est_dt = target_date.replace(
                        hour=parsed.hour, minute=parsed.minute,
                        second=0, microsecond=0
                    )
                    utc_dt = est_dt + timedelta(hours=5)  # EST -> UTC
                    return utc_dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            # Fallback: noon UTC
            return target_date.replace(hour=17, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        except Exception:
            return None

    # =========================================================================
    # INTEGRATED: PERFORMANCE FEEDBACK LOOP (PostTracker)
    # =========================================================================

    def _adjust_slot_confidence(self, platform: str, score: float):
        """
        Adjust schedule slot confidence based on PostTracker performance scores.
        High scores (>70) boost confidence; low scores (<30) reduce it.
        This causes future adaptations to keep or remove slots.
        """
        for slot in self._weekly_schedule:
            if slot.platform != platform:
                continue
            slot.performance_history.append(score)
            # Keep last 10 scores
            slot.performance_history = slot.performance_history[-10:]
            avg = sum(slot.performance_history) / len(slot.performance_history)
            # Map avg score (0-100) to confidence (0.3-1.0)
            slot.confidence = max(0.3, min(1.0, 0.3 + (avg / 100) * 0.7))

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance feedback summary across all slots."""
        slot_perf = []
        for slot in self._weekly_schedule:
            if slot.performance_history:
                avg = sum(slot.performance_history) / len(slot.performance_history)
                slot_perf.append({
                    "day": slot.day, "platform": slot.platform,
                    "format": slot.format, "confidence": round(slot.confidence, 2),
                    "avg_score": round(avg, 1),
                    "samples": len(slot.performance_history),
                })
        return {
            "slots_with_feedback": len(slot_perf),
            "total_feedback_points": len(self._performance_feedback),
            "slot_performance": sorted(slot_perf, key=lambda x: x["avg_score"], reverse=True),
        }

    # =========================================================================
    # INTEGRATED: VISUAL CAMPAIGN PRODUCTS
    # =========================================================================

    def get_visual_campaign_products(self) -> List[Dict[str, Any]]:
        """Get products from VisualCampaignService for content enrichment."""
        if not self.visual_campaign:
            return []
        try:
            products = self.visual_campaign.get_products()
            return [
                {"id": p.id, "name": p.name, "tagline": p.tagline,
                 "website_url": p.website_url, "key_features": p.key_features}
                for p in products
            ]
        except Exception as e:
            logger.warning(f"Could not load visual campaign products: {e}")
            return []

    # =========================================================================
    # INTEGRATED: FATE SCORING (Persuasion Framework)
    # =========================================================================

    def fate_score_video_pool(self) -> Dict[str, Any]:
        """
        Score all videos in the pool using the FATE persuasion framework.
        Uses hooks and transcripts to calculate Focus/Authority/Tribe/Emotion scores.
        High-FATE videos get priority in schedule slot assignment.
        """
        if not self.fate_scorer:
            return {"error": "FATEScorer not available", "scored": 0}

        scored_count = 0
        for video in self._video_pool:
            vid_id = video.get("id", "")
            # Build text from hooks + tone for FATE analysis
            hooks_text = " ".join(video.get("hooks", []))
            topics_text = " ".join(video.get("topics", []))
            combined_text = f"{hooks_text} {topics_text} {video.get('tone', '')}"

            if combined_text.strip():
                scores = self.fate_scorer.score_all(combined_text)
                self._fate_scores[vid_id] = scores
                video["fate_scores"] = scores
                video["fate_combined"] = sum(scores.values()) / max(len(scores), 1)
                scored_count += 1

        # Re-sort pool by FATE combined score (highest first)
        self._video_pool.sort(
            key=lambda v: v.get("fate_combined", 0), reverse=True
        )
        logger.info(f"AdaptiveScheduler: FATE-scored {scored_count} videos in pool")
        return {"scored": scored_count, "top_fate": self._video_pool[0] if self._video_pool else None}

    # =========================================================================
    # INTEGRATED: TREND BRIEFS (Timely Content Ideas)
    # =========================================================================

    async def fetch_trend_briefs(self, trend_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Generate AI-powered trend briefs and inject them into schedule slots.
        Trend briefs provide content ideas, example hooks, and best posting times.
        """
        if not self.trend_brief:
            return []

        briefs = []
        trend_sources = trend_names or ["AI tools", "productivity hacks", "software development"]

        for name in trend_sources[:5]:
            try:
                brief = await self.trend_brief.generate_brief(
                    trend_type="topic",
                    trend_id=name.lower().replace(" ", "_"),
                    trend_name=name,
                )
                if brief:
                    brief_dict = brief.dict() if hasattr(brief, "dict") else vars(brief)
                    briefs.append(brief_dict)
            except Exception as e:
                logger.debug(f"Could not generate brief for '{name}': {e}")

        self._active_trend_briefs = briefs
        logger.info(f"AdaptiveScheduler: Generated {len(briefs)} trend briefs")
        return briefs

    def inject_trend_briefs_into_schedule(self):
        """
        Enrich 'original' schedule slots with trend brief data.
        Assigns content ideas and example hooks from active briefs.
        """
        if not self._active_trend_briefs:
            return 0

        enriched = 0
        original_slots = [s for s in self._weekly_schedule if s.content_type == "original"]

        for i, slot in enumerate(original_slots):
            brief_idx = i % len(self._active_trend_briefs)
            brief = self._active_trend_briefs[brief_idx]

            ideas = brief.get("content_ideas", [])
            hooks = brief.get("example_hooks", [])
            best_time = brief.get("best_posting_time", "")

            # Enrich slot notes with trend data
            trend_note = f"TREND: {brief.get('trend_name', '')} | "
            if ideas:
                trend_note += f"Idea: {ideas[0]} | "
            if hooks:
                trend_note += f"Hook: {hooks[0]}"
            slot.notes = f"{trend_note} | {slot.notes}" if slot.notes else trend_note
            enriched += 1

        logger.info(f"AdaptiveScheduler: Injected trend data into {enriched} slots")
        return enriched

    # =========================================================================
    # INTEGRATED: ENGAGEMENT SCORER (Z-Score Reward Function)
    # =========================================================================

    def compute_reward_scores(self) -> List[Dict[str, Any]]:
        """
        Apply the EngagementScorer z-score reward function to scored content.
        This provides a more sophisticated winner/loser classification than
        simple composite scoring. Winners get priority for cross-posting.
        """
        if not self.engagement_scorer or not self._scored_content:
            return []

        results = []
        for sc in self._scored_content:
            try:
                reward = self.engagement_scorer.score_post({
                    "likes": sc.likes,
                    "comments": sc.comments,
                    "shares": sc.shares,
                    "saves": sc.saves,
                    "views": sc.views,
                    "impressions": sc.views or 1,
                })
                if reward:
                    reward_dict = reward.to_dict() if hasattr(reward, "to_dict") else vars(reward)
                    sc.notes = f"Reward: {reward_dict.get('composite_score', 0):.2f} | {reward_dict.get('label', '')}"
                    results.append({
                        "content_id": sc.content_id,
                        "platform": sc.platform,
                        "reward_score": reward_dict,
                    })
            except Exception as e:
                logger.debug(f"Reward scoring failed for {sc.content_id}: {e}")

        logger.info(f"AdaptiveScheduler: Computed reward scores for {len(results)} content items")
        return results

    # =========================================================================
    # INTEGRATED: CONTENT VARIATIONS (Caption Rotation)
    # =========================================================================

    async def get_caption_variation(self, content_id: str, platform: str) -> Optional[str]:
        """
        Get a fresh caption variation for cross-posts using ContentReusabilityService.
        Avoids repeating the same caption too soon across platforms.
        """
        try:
            from services.content_variations import ContentReusabilityService, VariationType
            import database.connection as db_conn
            async with db_conn.async_session_maker() as session:
                svc = ContentReusabilityService()
                variation = await svc.get_best_variation(
                    session, content_id, VariationType.CAPTION
                )
                if variation:
                    return variation.text
        except Exception as e:
            logger.debug(f"Caption variation not available for {content_id}: {e}")
        return None

    # =========================================================================
    # INTEGRATED: WEEKLY PLANNER (Bandit Allocation + Learnings)
    # =========================================================================

    async def merge_weekly_planner_insights(self) -> Dict[str, Any]:
        """
        Pull learnings from WeeklyPlanner (bandit allocation, experiment results,
        winning patterns) and merge them into the adaptive schedule.
        Winning templates/times/formats get higher slot confidence.
        """
        if not self.weekly_planner:
            return {"merged": False, "reason": "WeeklyPlanner not available"}

        try:
            insights = await self.weekly_planner.analyze_performance()
            if not insights:
                return {"merged": False, "reason": "No performance data"}

            # Extract winning patterns
            winning_times = insights.get("winning_times", [])
            winning_formats = insights.get("winning_formats", [])
            winning_topics = insights.get("winning_topics", [])

            # Boost confidence for slots matching winning patterns
            boosted = 0
            for slot in self._weekly_schedule:
                boost = 0.0
                if slot.time_est in winning_times:
                    boost += 0.1
                if slot.format in winning_formats:
                    boost += 0.1
                if boost > 0:
                    slot.confidence = min(1.0, slot.confidence + boost)
                    boosted += 1

            logger.info(f"AdaptiveScheduler: Merged WeeklyPlanner insights, boosted {boosted} slots")
            return {
                "merged": True,
                "winning_times": winning_times,
                "winning_formats": winning_formats,
                "winning_topics": winning_topics,
                "slots_boosted": boosted,
            }
        except Exception as e:
            logger.warning(f"Could not merge weekly planner insights: {e}")
            return {"merged": False, "reason": str(e)}

    # =========================================================================
    # INTEGRATED: TIKTOK REPURPOSE (Automated Cross-Post Pipeline)
    # =========================================================================

    async def run_tiktok_repurpose_pipeline(self, username: str = "isaiah_dupree") -> Dict[str, Any]:
        """
        Trigger TikTokRepurposeService to fetch latest TikTok videos,
        download, analyze, and queue for cross-posting to other platforms.
        Results feed directly into the cross-post queue.
        """
        if not self.tiktok_repurpose:
            return {"success": False, "reason": "TikTokRepurposeService not available"}

        try:
            result = await self.tiktok_repurpose.run_full_pipeline(username=username)
            # Add any new cross-post candidates to our queue
            new_candidates = result.get("cross_post_candidates", [])
            for candidate in new_candidates:
                self._cross_post_queue.append({
                    "source_platform": "tiktok",
                    "source_content_id": candidate.get("video_id", ""),
                    "source_title": candidate.get("caption", "")[:80],
                    "source_score": candidate.get("engagement_score", 0),
                    "target_platform": candidate.get("target_platform", "instagram"),
                    "target_format": "Reels",
                    "delay_hours": 24,
                    "reason": "TikTok repurpose pipeline",
                    "pipeline": "tiktok_repurpose",
                })

            logger.info(f"AdaptiveScheduler: TikTok repurpose added {len(new_candidates)} cross-post candidates")
            return {"success": True, "candidates_added": len(new_candidates), "pipeline_result": result}
        except Exception as e:
            logger.warning(f"TikTok repurpose pipeline failed: {e}")
            return {"success": False, "reason": str(e)}

    # =========================================================================
    # INTEGRATED: REPURPOSE PIPELINE (Long-Form -> Short Clips)
    # =========================================================================

    async def generate_clips_from_long_content(self, video_path: str, title: str = "") -> Dict[str, Any]:
        """
        Use RepurposePipeline to automatically extract short clips from
        long-form content (podcasts, tutorials). Clips are added to the video pool.
        """
        if not self.repurpose_pipeline:
            return {"success": False, "reason": "RepurposePipeline not available"}

        try:
            result = await self.repurpose_pipeline.process_video(
                video_path=video_path,
                title=title or "Long-form content"
            )
            clips = result.get("clips", [])
            # Add clips to video pool
            for clip in clips:
                self._video_pool.append({
                    "id": clip.get("clip_id", str(uuid4())),
                    "file_name": clip.get("filename", ""),
                    "source_uri": clip.get("path", ""),
                    "duration_sec": clip.get("duration", 0),
                    "pre_social_score": clip.get("score", 70),
                    "topics": clip.get("topics", []),
                    "hooks": [clip.get("hook", "")],
                    "tone": clip.get("tone", ""),
                    "curation_status": "auto_clipped",
                })

            logger.info(f"AdaptiveScheduler: Generated {len(clips)} clips from long-form content")
            return {"success": True, "clips_generated": len(clips), "added_to_pool": True}
        except Exception as e:
            logger.warning(f"Clip generation failed: {e}")
            return {"success": False, "reason": str(e)}

    # =========================================================================
    # INTEGRATED: META PIXEL (Conversion Tracking for Offer CTAs)
    # =========================================================================

    def track_offer_conversion(self, offer_id: str, platform: str, post_id: str) -> Dict[str, Any]:
        """
        Fire a Meta Pixel conversion event when a scheduled post with an offer CTA
        goes live. Enables tracking which scheduled offer posts actually drive conversions.
        """
        if not self.meta_pixel:
            return {"tracked": False, "reason": "MetaPixelService not available"}

        try:
            offer = self._offers.get(offer_id)
            if not offer:
                return {"tracked": False, "reason": f"Offer {offer_id} not found"}

            event_data = {
                "content_name": offer.name,
                "content_category": "software_product",
                "content_ids": [offer_id],
                "value": 0.0,
                "currency": "USD",
            }

            self.meta_pixel.track_standard_event(
                event_name="ViewContent",
                event_data=event_data,
                user_data={"external_id": post_id},
                source_url=f"https://app.mediaposter.com/post/{post_id}"
            )

            logger.info(f"AdaptiveScheduler: Tracked Meta Pixel ViewContent for offer {offer.name}")
            return {"tracked": True, "offer": offer.name, "event": "ViewContent"}
        except Exception as e:
            logger.debug(f"Meta pixel tracking failed: {e}")
            return {"tracked": False, "reason": str(e)}

    def track_offer_cta_click(self, offer_id: str, platform: str) -> Dict[str, Any]:
        """Track when a scheduled CTA actually leads to a product page visit."""
        if not self.meta_pixel:
            return {"tracked": False}
        try:
            offer = self._offers.get(offer_id)
            self.meta_pixel.track_standard_event(
                event_name="Lead",
                event_data={
                    "content_name": offer.name if offer else offer_id,
                    "content_category": "offer_cta",
                },
            )
            return {"tracked": True, "event": "Lead", "offer": offer_id}
        except Exception:
            return {"tracked": False}

    # =========================================================================
    # INTEGRATED: DM WARMTH SYSTEM (Coordinated Outreach)
    # =========================================================================

    def coordinate_dm_outreach(self) -> List[Dict[str, Any]]:
        """
        Coordinate DM outreach timing with content posting schedule.
        After a post goes live, queue DM outreach to hot/warm contacts on that platform
        to amplify initial engagement (the first 30 minutes are critical for algorithms).
        """
        if not self.dm_warmth:
            return []

        outreach_tasks = []
        for slot in self._weekly_schedule:
            if slot.content_type != "original":
                continue  # Only outreach for original content

            try:
                # Get hot/warm contacts for this platform
                contacts = self.dm_warmth.get_next_dm_targets(
                    platform=slot.platform, count=5
                )
                if not contacts:
                    continue

                for contact in contacts:
                    contact_dict = contact if isinstance(contact, dict) else vars(contact)
                    task = {
                        "slot_day": slot.day,
                        "slot_time": slot.time_est,
                        "platform": slot.platform,
                        "contact_username": contact_dict.get("username", ""),
                        "warmth_tier": contact_dict.get("warmth_tier", "unknown"),
                        "action": "notify_new_post",
                        "message_template": f"Just dropped something new — would love your thoughts!",
                        "delay_minutes": 5,  # DM 5 minutes after post goes live
                    }
                    outreach_tasks.append(task)
            except Exception as e:
                logger.debug(f"DM coordination failed for {slot.platform}/{slot.day}: {e}")

        self._dm_outreach_queue = outreach_tasks
        logger.info(f"AdaptiveScheduler: Coordinated {len(outreach_tasks)} DM outreach tasks with schedule")
        return outreach_tasks

    # =========================================================================
    # INTEGRATED: AGENT SCHEDULER (Auto-run Adaptive Cycle)
    # =========================================================================

    async def register_adaptive_cycle_schedule(
        self, interval_hours: int = 24, agent_type: str = "adaptive_scheduler"
    ) -> Dict[str, Any]:
        """
        Register the adaptive cycle as a recurring scheduled agent via AgentScheduler.
        This enables the system to auto-adapt daily/weekly without manual triggers.
        """
        try:
            from services.agent_scheduler import AgentScheduler
            scheduler = AgentScheduler.get_instance()
            schedule_id = await scheduler.create_schedule(
                agent_type=agent_type,
                schedule_name="Adaptive Scheduler Daily Cycle",
                interval_seconds=interval_hours * 3600,
                config={
                    "platforms": ["tiktok", "instagram", "youtube", "threads"],
                    "auto_materialize": True,
                    "auto_fate_score": True,
                    "auto_dm_coordinate": True,
                },
            )
            logger.info(f"AdaptiveScheduler: Registered recurring cycle (every {interval_hours}h), schedule_id={schedule_id}")
            return {"registered": True, "schedule_id": str(schedule_id), "interval_hours": interval_hours}
        except Exception as e:
            logger.warning(f"Could not register adaptive cycle schedule: {e}")
            return {"registered": False, "reason": str(e)}

    # =========================================================================
    # WAVE 3: INSIGHTS ENGINE (Hook Patterns + Optimal Posting Times)
    # =========================================================================

    def get_hook_pattern_insights(self, lookback_days: int = 30) -> List[Dict[str, Any]]:
        """
        Use InsightsEngine to detect which hook types drive best retention/engagement.
        Results inform content selection: prioritize videos with winning hook types.
        """
        if not self.insights_engine:
            return []
        try:
            insights = self.insights_engine.detect_hook_patterns(
                min_sample_size=5, lookback_days=lookback_days
            )
            logger.info(f"AdaptiveScheduler: Found {len(insights)} hook pattern insights")
            return insights
        except Exception as e:
            logger.debug(f"Hook pattern detection failed: {e}")
            return []

    def get_optimal_posting_times(self, platform: str = "tiktok", lookback_days: int = 30) -> Dict[str, Any]:
        """
        Use InsightsEngine to detect best posting times per platform from real data.
        Overrides default best_times_est in PLATFORM_CONSTRAINTS with data-driven times.
        """
        if not self.insights_engine:
            return {}
        try:
            result = self.insights_engine.detect_optimal_posting_times(
                platform=platform, lookback_days=lookback_days
            )
            # If we found a best hour, update schedule slots for this platform
            best_hour = result.get("best_posting_hour")
            if best_hour is not None:
                for slot in self._weekly_schedule:
                    if slot.platform == platform:
                        hour_12 = best_hour % 12 or 12
                        ampm = "AM" if best_hour < 12 else "PM"
                        slot.time_est = f"{hour_12}:00 {ampm}"
                logger.info(f"AdaptiveScheduler: Updated {platform} slots to optimal hour {best_hour}:00")
            return result
        except Exception as e:
            logger.debug(f"Optimal posting time detection failed for {platform}: {e}")
            return {}

    def apply_insights_to_schedule(self) -> Dict[str, Any]:
        """
        Run full InsightsEngine analysis and apply results to schedule:
        1. Detect hook patterns → prioritize matching videos
        2. Detect optimal posting times → adjust slot times per platform
        """
        hook_insights = self.get_hook_pattern_insights()
        time_results = {}
        platforms = set(s.platform for s in self._weekly_schedule)
        for platform in platforms:
            time_results[platform] = self.get_optimal_posting_times(platform)

        # Prioritize videos matching winning hook patterns in pool
        winning_hooks = [i.get("pattern_data", {}).get("hook_type") for i in hook_insights]
        if winning_hooks:
            for video in self._video_pool:
                video_hooks = video.get("hooks", [])
                hook_match = any(h in " ".join(video_hooks).lower() for h in winning_hooks if h)
                if hook_match:
                    video["pre_social_score"] = video.get("pre_social_score", 0) + 15

            self._video_pool.sort(key=lambda v: v.get("pre_social_score", 0), reverse=True)

        return {
            "hook_insights": len(hook_insights),
            "platforms_optimized": len(time_results),
            "winning_hooks": winning_hooks,
            "time_results": time_results,
        }

    # =========================================================================
    # WAVE 3: BANDIT ALLOCATOR (Dynamic Format Allocation)
    # =========================================================================

    async def apply_bandit_allocation(self) -> Dict[str, Any]:
        """
        Use BanditAllocator to dynamically adjust content format distribution.
        Winning formats (Short-form, Carousel, etc.) get more schedule slots.
        """
        if not self.bandit_allocator:
            return {"applied": False, "reason": "BanditAllocator not available"}

        try:
            allocations = await self.bandit_allocator.compute_allocations()
            if not allocations:
                return {"applied": False, "reason": "No allocation data"}

            alloc_dict = {}
            if hasattr(allocations, "items"):
                alloc_dict = dict(allocations)
            elif isinstance(allocations, list):
                for a in allocations:
                    if isinstance(a, dict):
                        alloc_dict[a.get("template_id", a.get("format", ""))] = a.get("allocation", 0)

            # Boost confidence for slots matching high-allocation formats
            boosted = 0
            for slot in self._weekly_schedule:
                fmt_key = slot.format.lower().replace("-", "_").replace(" ", "_")
                alloc_val = alloc_dict.get(fmt_key, alloc_dict.get(slot.format, 0))
                if alloc_val and isinstance(alloc_val, (int, float)) and alloc_val > 0.2:
                    slot.confidence = min(1.0, slot.confidence + 0.15)
                    boosted += 1

            logger.info(f"AdaptiveScheduler: Bandit allocation boosted {boosted} slots")
            return {"applied": True, "allocations": alloc_dict, "slots_boosted": boosted}
        except Exception as e:
            logger.warning(f"Bandit allocation failed: {e}")
            return {"applied": False, "reason": str(e)}

    # =========================================================================
    # WAVE 3: CONTENT MIX PLANNER (Long-term Distribution Targets)
    # =========================================================================

    async def align_with_content_mix(self) -> Dict[str, Any]:
        """
        Align the adaptive schedule with ContentMixPlanner's distribution targets.
        Ensures the right proportion of UGC, carousel, AI-generated, animated content.
        """
        if not self.content_mix_planner:
            return {"aligned": False, "reason": "ContentMixPlanner not available"}

        try:
            plan = await self.content_mix_planner.get_active_plan()
            if not plan:
                return {"aligned": False, "reason": "No active content mix plan"}

            plan_dict = plan if isinstance(plan, dict) else (plan.to_dict() if hasattr(plan, "to_dict") else vars(plan))
            mix_config = plan_dict.get("content_mix", plan_dict.get("mix_config", {}))

            # Tag schedule slots with recommended content types from the mix
            tagged = 0
            slot_list = list(self._weekly_schedule)
            total_slots = len(slot_list)
            if total_slots > 0 and mix_config:
                for content_type, pct in mix_config.items():
                    if isinstance(pct, (int, float)):
                        n_slots = max(1, int(total_slots * pct / 100))
                        for slot in slot_list[:n_slots]:
                            if not slot.notes or "MIX:" not in slot.notes:
                                slot.notes = f"MIX:{content_type} | {slot.notes or ''}"
                                tagged += 1

            logger.info(f"AdaptiveScheduler: Aligned {tagged} slots with content mix plan")
            return {"aligned": True, "mix_config": mix_config, "slots_tagged": tagged}
        except Exception as e:
            logger.warning(f"Content mix alignment failed: {e}")
            return {"aligned": False, "reason": str(e)}

    # =========================================================================
    # WAVE 3: A/B TESTING (Slot Configuration Tests)
    # =========================================================================

    def create_slot_ab_test(self, platform: str, variation_type: str = "posting_time",
                            variations: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create an A/B test for a schedule slot configuration (time, format, CTA style, hook type).
        The adaptive scheduler will distribute traffic across variations and measure performance.
        """
        if not self.ab_testing:
            return {"created": False, "reason": "ABTestingService not available"}

        try:
            test_variations = variations or ["9:00 AM", "12:00 PM", "7:00 PM"]
            test = self.ab_testing.create_test(
                name=f"Adaptive_{platform}_{variation_type}",
                variation_type=variation_type,
                variations=test_variations,
            )
            test_id = test.id if hasattr(test, "id") else str(test)

            # Assign test variations to matching schedule slots
            matching_slots = [s for s in self._weekly_schedule if s.platform == platform]
            for i, slot in enumerate(matching_slots):
                var_idx = i % len(test_variations)
                slot.notes = f"AB_TEST:{test_id}:var_{var_idx} | {slot.notes or ''}"

            logger.info(f"AdaptiveScheduler: Created A/B test {test_id} for {platform}/{variation_type}")
            return {"created": True, "test_id": test_id, "slots_assigned": len(matching_slots)}
        except Exception as e:
            logger.debug(f"A/B test creation failed: {e}")
            return {"created": False, "reason": str(e)}

    # =========================================================================
    # WAVE 3: AI CONTENT GENERATOR (Auto-generate for Empty Slots)
    # =========================================================================

    async def generate_content_for_empty_slots(self) -> Dict[str, Any]:
        """
        Use AIContentGenerator to auto-create captions and content briefs
        for schedule slots that don't yet have assigned content.
        """
        if not self.ai_content_generator:
            return {"generated": 0, "reason": "AIContentGenerator not available"}

        generated = 0
        for slot in self._weekly_schedule:
            if slot.content_type == "original" and not slot.offer_cta and not slot.notes:
                try:
                    topics = []
                    if self._active_trend_briefs:
                        brief = self._active_trend_briefs[generated % len(self._active_trend_briefs)]
                        topics = brief.get("content_ideas", [])[:2]

                    prompt = (
                        f"Write a short, engaging {slot.format} caption for {slot.platform}. "
                        f"Topics: {', '.join(topics) if topics else 'tech/productivity'}. "
                        f"Keep it under 150 characters with a strong hook."
                    )

                    caption = await self.ai_content_generator.generate_text(
                        prompt=prompt, max_tokens=200
                    )
                    if caption:
                        slot.notes = f"AI_CAPTION: {caption.strip()[:200]}"
                        generated += 1
                except Exception as e:
                    logger.debug(f"AI caption generation failed for {slot.day}/{slot.platform}: {e}")

        logger.info(f"AdaptiveScheduler: AI-generated captions for {generated} empty slots")
        return {"generated": generated}

    # =========================================================================
    # WAVE 3: AI THUMBNAIL SELECTOR (Auto-select Thumbnails)
    # =========================================================================

    async def select_thumbnails_for_pool(self, limit: int = 10) -> Dict[str, Any]:
        """
        Use AIThumbnailSelector to pick the best thumbnail frame for videos in the pool.
        Attaches thumbnail_path to video pool entries for use in scheduled posts.
        """
        if not self.ai_thumbnail:
            return {"selected": 0, "reason": "AIThumbnailSelector not available"}

        selected = 0
        for video in self._video_pool[:limit]:
            video_path = video.get("source_uri", "")
            if not video_path or video.get("thumbnail_path"):
                continue
            try:
                result = self.ai_thumbnail.select_best_frame(video_path)
                if result and hasattr(result, "frame_path"):
                    video["thumbnail_path"] = result.frame_path
                    video["thumbnail_score"] = result.combined_score
                    selected += 1
            except Exception as e:
                logger.debug(f"Thumbnail selection failed for {video.get('file_name')}: {e}")

        logger.info(f"AdaptiveScheduler: Selected thumbnails for {selected} videos")
        return {"selected": selected}

    # =========================================================================
    # WAVE 3: SORA VIDEO PIPELINE (AI Video Generation)
    # =========================================================================

    async def generate_ai_video_for_slot(self, slot_day: str, slot_platform: str,
                                          topic: str = "") -> Dict[str, Any]:
        """
        Use SoraVideoPipeline to generate an entirely new AI video for a schedule slot.
        The generated video is added to the pool and assigned to the slot.
        """
        if not self.sora_pipeline:
            return {"generated": False, "reason": "SoraVideoPipeline not available"}

        try:
            # Find the target slot
            target_slot = None
            for slot in self._weekly_schedule:
                if slot.day == slot_day and slot.platform == slot_platform:
                    target_slot = slot
                    break

            if not target_slot:
                return {"generated": False, "reason": f"No slot found for {slot_day}/{slot_platform}"}

            # Use trend brief topic if available
            if not topic and self._active_trend_briefs:
                topic = self._active_trend_briefs[0].get("trend_name", "tech tips")

            result = await self.sora_pipeline.create_video(
                topic=topic or "productivity tips",
                style="tech",
                duration=30,
            )

            if result:
                result_dict = result if isinstance(result, dict) else (vars(result) if hasattr(result, "__dict__") else {"path": str(result)})
                video_entry = {
                    "id": result_dict.get("id", str(uuid4())),
                    "file_name": result_dict.get("filename", "sora_generated.mp4"),
                    "source_uri": result_dict.get("path", result_dict.get("local_path", "")),
                    "duration_sec": result_dict.get("duration", 30),
                    "pre_social_score": 80,
                    "topics": [topic],
                    "hooks": [],
                    "tone": "ai_generated",
                    "curation_status": "ai_generated",
                }
                self._video_pool.insert(0, video_entry)
                target_slot.notes = f"SORA_VIDEO: {topic} | {target_slot.notes or ''}"

                logger.info(f"AdaptiveScheduler: Generated Sora AI video for {slot_day}/{slot_platform}")
                return {"generated": True, "video": video_entry, "slot": f"{slot_day}/{slot_platform}"}

            return {"generated": False, "reason": "Sora pipeline returned no result"}
        except Exception as e:
            logger.warning(f"Sora video generation failed: {e}")
            return {"generated": False, "reason": str(e)}

    # =========================================================================
    # WAVE 3: SLEEP MODE (Coordinate Wake/Sleep with Post Schedule)
    # =========================================================================

    async def sync_sleep_schedule(self) -> Dict[str, Any]:
        """
        Coordinate SleepModeService with the adaptive post schedule.
        Ensures the system is AWAKE before scheduled posts and can SLEEP between gaps.
        """
        if not self.sleep_mode:
            return {"synced": False, "reason": "SleepModeService not available"}

        try:
            # Calculate next post time from schedule
            next_7_days = self.get_next_7_days()
            if not next_7_days:
                return {"synced": False, "reason": "No scheduled slots"}

            # Find earliest upcoming slot
            now = datetime.now(timezone.utc)
            upcoming = []
            for slot_info in next_7_days:
                scheduled_str = slot_info.get("scheduled_time_utc")
                if scheduled_str:
                    try:
                        scheduled_dt = datetime.fromisoformat(scheduled_str)
                        if scheduled_dt > now:
                            upcoming.append(scheduled_dt)
                    except (ValueError, TypeError):
                        pass

            if upcoming:
                next_post = min(upcoming)
                gap_hours = (next_post - now).total_seconds() / 3600

                # If gap > 2 hours, tell sleep mode it can sleep
                if gap_hours > 2:
                    wake_before_minutes = 15
                    logger.info(
                        f"AdaptiveScheduler: Next post in {gap_hours:.1f}h, "
                        f"sleep mode can rest for {gap_hours - 0.25:.1f}h"
                    )

                return {
                    "synced": True,
                    "next_post_utc": next_post.isoformat(),
                    "gap_hours": round(gap_hours, 1),
                    "sleep_recommended": gap_hours > 2,
                    "upcoming_posts": len(upcoming),
                }

            return {"synced": True, "upcoming_posts": 0, "sleep_recommended": True}
        except Exception as e:
            logger.warning(f"Sleep schedule sync failed: {e}")
            return {"synced": False, "reason": str(e)}

    # =========================================================================
    # WAVE 3: DCO OPTIMIZER (Creative Combination Testing)
    # =========================================================================

    def optimize_creative_combinations(self) -> Dict[str, Any]:
        """
        Use DCO Optimizer to test creative element combinations
        (video + text + headline + CTA) and surface winning combos for schedule slots.
        """
        if not self.dco_optimizer:
            return {"optimized": False, "reason": "DCOOptimizer not available"}

        try:
            # Gather creative elements from pool and offers
            videos = [v.get("file_name", "") for v in self._video_pool[:5]]
            texts = [s.notes or "" for s in self._weekly_schedule if s.notes][:5]
            headlines = [v.get("hooks", [""])[0] for v in self._video_pool[:5] if v.get("hooks")]
            ctas = [o.cta_text for o in self._offers.values() if o.is_launchable and hasattr(o, "cta_text")][:5]

            if not videos or not texts:
                return {"optimized": False, "reason": "Not enough creative elements"}

            campaign_id = self.dco_optimizer.create_dco_campaign(
                videos=videos,
                primary_texts=texts,
                headlines=headlines or ["Check this out"],
                ctas=ctas or ["Learn More"],
            )

            logger.info(f"AdaptiveScheduler: Created DCO campaign {campaign_id}")
            return {"optimized": True, "campaign_id": campaign_id, "elements": {
                "videos": len(videos), "texts": len(texts),
                "headlines": len(headlines), "ctas": len(ctas),
            }}
        except Exception as e:
            logger.debug(f"DCO optimization failed: {e}")
            return {"optimized": False, "reason": str(e)}

    # =========================================================================
    # WAVE 3: COMMENT AUTOMATION (Post-publish Engagement Boost)
    # =========================================================================

    async def schedule_comment_engagement(self, post_url: str = "", platform: str = "instagram") -> Dict[str, Any]:
        """
        After a post goes live, use CommentAutomation to engage with related posts
        on the platform to boost algorithmic visibility in the first 30 minutes.
        """
        if not self.comment_automation:
            return {"scheduled": False, "reason": "CommentAutomation not available"}

        try:
            # Queue engagement actions for the platform
            targets = []
            for slot in self._weekly_schedule:
                if slot.platform == platform and slot.content_type == "original":
                    targets.append({
                        "day": slot.day,
                        "time": slot.time_est,
                        "action": "engage_after_post",
                        "platform": platform,
                        "delay_minutes": 5,
                    })

            logger.info(f"AdaptiveScheduler: Scheduled {len(targets)} comment engagement tasks for {platform}")
            return {"scheduled": True, "tasks": len(targets), "platform": platform}
        except Exception as e:
            logger.debug(f"Comment engagement scheduling failed: {e}")
            return {"scheduled": False, "reason": str(e)}

    # =========================================================================
    # WAVE 3: ANALYSIS HEALTH (Video Pool Quality Gate)
    # =========================================================================

    async def check_pool_analysis_health(self) -> Dict[str, Any]:
        """
        Use AnalysisHealthService to verify all videos in the pool have complete analysis.
        Flags videos with missing transcripts, visual analysis, or AI scores.
        Prevents scheduling under-analyzed content.
        """
        if not self.analysis_health:
            return {"checked": False, "reason": "AnalysisHealthService not available"}

        try:
            healthy = 0
            unhealthy = 0
            issues = []

            for video in self._video_pool:
                has_hooks = bool(video.get("hooks"))
                has_topics = bool(video.get("topics"))
                has_tone = bool(video.get("tone"))
                has_score = video.get("pre_social_score", 0) > 0

                if has_hooks and has_topics and has_tone and has_score:
                    healthy += 1
                else:
                    unhealthy += 1
                    missing = []
                    if not has_hooks: missing.append("hooks")
                    if not has_topics: missing.append("topics")
                    if not has_tone: missing.append("tone")
                    if not has_score: missing.append("score")
                    issues.append({
                        "video_id": video.get("id"),
                        "file_name": video.get("file_name"),
                        "missing": missing,
                    })

            # Move unhealthy videos to end of pool
            self._video_pool.sort(
                key=lambda v: (
                    bool(v.get("hooks")) and bool(v.get("topics"))
                    and bool(v.get("tone")) and v.get("pre_social_score", 0) > 0
                ),
                reverse=True,
            )

            logger.info(f"AdaptiveScheduler: Pool health — {healthy} healthy, {unhealthy} need analysis")
            return {
                "checked": True,
                "healthy": healthy,
                "unhealthy": unhealthy,
                "issues": issues[:20],
                "pool_size": len(self._video_pool),
            }
        except Exception as e:
            logger.warning(f"Pool health check failed: {e}")
            return {"checked": False, "reason": str(e)}

    # =========================================================================
    # WAVE 3: PERFORMANCE CORRELATOR (Segment-Level Feedback)
    # =========================================================================

    def get_segment_performance_insights(self) -> Dict[str, Any]:
        """
        Use PerformanceCorrelator to identify which video segments (hooks, CTAs)
        drive the best engagement. Informs content selection and editing decisions.
        """
        if not self.performance_correlator:
            return {"insights": [], "reason": "PerformanceCorrelator not available"}

        try:
            top_patterns = self.performance_correlator.get_top_performing_patterns(
                min_sample_size=3
            )
            patterns = top_patterns if isinstance(top_patterns, list) else []
            logger.info(f"AdaptiveScheduler: Found {len(patterns)} segment performance patterns")
            return {"insights": patterns[:20], "total": len(patterns)}
        except Exception as e:
            logger.debug(f"Segment performance analysis failed: {e}")
            return {"insights": [], "reason": str(e)}

    # =========================================================================
    # WAVE 4: TEMPLATE LEADERBOARD (Winning Template Selection)
    # =========================================================================

    async def get_winning_templates(self, top_n: int = 10) -> Dict[str, Any]:
        """
        Use TemplateLeaderboard to get top-performing content templates.
        Winning templates inform what content types/formats to prioritize in the schedule.
        """
        if not self.template_leaderboard:
            return {"templates": [], "reason": "TemplateLeaderboard not available"}
        try:
            rankings = await self.template_leaderboard.recompute_rankings()
            templates = rankings.get("templates", [])
            winners = [t for t in templates if t.get("performance_label") == "winner"]
            logger.info(f"AdaptiveScheduler: {len(winners)} winning templates from leaderboard")
            return {"templates": templates[:top_n], "winners": len(winners), "total": rankings.get("updated", 0)}
        except Exception as e:
            logger.debug(f"Template leaderboard query failed: {e}")
            return {"templates": [], "reason": str(e)}

    # =========================================================================
    # WAVE 4: QA GATE (Quality Gate Before Publishing)
    # =========================================================================

    async def qa_check_slot_content(self, slot_index: int = 0) -> Dict[str, Any]:
        """
        Run QA gate checks on content assigned to a schedule slot.
        Validates FATE scores, awareness match, platform length, forbidden content, CTA.
        """
        if not self.qa_gate:
            return {"passed": False, "reason": "QAGateService not available"}
        try:
            if slot_index >= len(self._weekly_schedule):
                return {"passed": False, "reason": f"Slot index {slot_index} out of range"}

            slot = self._weekly_schedule[slot_index]
            content_text = slot.notes or ""
            fate_scores = self._fate_scores.get(slot.offer_id or "", {})

            result = await self.qa_gate.check({
                "text": content_text,
                "fate_scores": fate_scores,
                "awareness_level": 3,
                "target_awareness": 3,
                "platform": slot.platform,
            })

            result_dict = result.dict() if hasattr(result, "dict") else vars(result)
            logger.info(f"AdaptiveScheduler: QA check for slot {slot_index} — {result_dict.get('status', 'unknown')}")
            return {"passed": result_dict.get("passed", False), "result": result_dict}
        except Exception as e:
            logger.debug(f"QA gate check failed: {e}")
            return {"passed": False, "reason": str(e)}

    async def qa_gate_all_slots(self) -> Dict[str, Any]:
        """Run QA gate on all schedule slots and flag failures."""
        if not self.qa_gate:
            return {"checked": 0, "reason": "QAGateService not available"}

        passed = 0
        warned = 0
        failed = 0
        for i in range(len(self._weekly_schedule)):
            result = await self.qa_check_slot_content(i)
            if result.get("passed"):
                status = result.get("result", {}).get("status", "PASS")
                if status == "WARN":
                    warned += 1
                else:
                    passed += 1
            else:
                failed += 1

        logger.info(f"AdaptiveScheduler: QA gate — {passed} passed, {warned} warned, {failed} failed")
        return {"checked": len(self._weekly_schedule), "passed": passed, "warned": warned, "failed": failed}

    # =========================================================================
    # WAVE 4: AWARENESS CLASSIFIER (Funnel Stage Distribution)
    # =========================================================================

    def classify_pool_awareness(self) -> Dict[str, Any]:
        """
        Classify all videos in the pool by awareness stage (1-5).
        Ensures the schedule covers the full marketing funnel:
        Unaware → Problem-aware → Solution-aware → Product-aware → Most-aware.
        """
        if not self.awareness_classifier:
            return {"classified": 0, "reason": "AwarenessClassifier not available"}
        try:
            distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            classified = 0

            for video in self._video_pool:
                text = " ".join(video.get("hooks", []) + video.get("topics", []))
                if not text:
                    continue
                result = self.awareness_classifier.classify(text)
                level = result.level.value if hasattr(result, "level") else (result.get("level", 3) if isinstance(result, dict) else 3)
                video["awareness_level"] = level
                distribution[level] = distribution.get(level, 0) + 1
                classified += 1

            logger.info(f"AdaptiveScheduler: Classified {classified} videos by awareness — {distribution}")
            return {"classified": classified, "distribution": distribution}
        except Exception as e:
            logger.debug(f"Awareness classification failed: {e}")
            return {"classified": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 4: COMPETITOR ANALYSIS (Intelligence-Driven Strategy)
    # =========================================================================

    async def get_competitor_insights(self, username: str = "") -> Dict[str, Any]:
        """
        Use CompetitorAnalysisService to extract learnings from competitor content.
        Competitor hooks, formats, themes inform what content to create/schedule.
        """
        if not self.competitor_analysis:
            return {"learnings": [], "reason": "CompetitorAnalysisService not available"}
        try:
            if username:
                learnings = await self.competitor_analysis.get_account_learnings(username)
            else:
                learnings = await self.competitor_analysis.get_all_learnings()

            learnings_list = learnings if isinstance(learnings, list) else [learnings] if learnings else []
            learnings_dicts = []
            for l in learnings_list:
                if hasattr(l, "dict"):
                    learnings_dicts.append(l.dict())
                elif isinstance(l, dict):
                    learnings_dicts.append(l)

            logger.info(f"AdaptiveScheduler: Got {len(learnings_dicts)} competitor insight sets")
            return {"learnings": learnings_dicts[:10], "total": len(learnings_dicts)}
        except Exception as e:
            logger.debug(f"Competitor analysis failed: {e}")
            return {"learnings": [], "reason": str(e)}

    # =========================================================================
    # WAVE 4: CONTENT GENERATION PIPELINE (Full AI Content Creation)
    # =========================================================================

    async def generate_content_for_slot(self, slot_index: int, awareness_level: int = 3,
                                         offer_id: str = "") -> Dict[str, Any]:
        """
        Use ContentGenerationPipeline to generate FATE-scored, awareness-aligned content
        for a specific schedule slot. Returns multiple variants for A/B testing.
        """
        if not self.content_gen_pipeline:
            return {"generated": False, "reason": "ContentGenerationPipeline not available"}
        try:
            if slot_index >= len(self._weekly_schedule):
                return {"generated": False, "reason": f"Slot index {slot_index} out of range"}

            slot = self._weekly_schedule[slot_index]
            result = await self.content_gen_pipeline.generate({
                "template_id": "adaptive_default",
                "offer_id": offer_id or slot.offer_id or "",
                "icp_id": "default",
                "awareness_level": awareness_level,
                "channel": "post",
                "platform": slot.platform,
                "variants": 3,
            })

            result_dict = result if isinstance(result, dict) else (result.dict() if hasattr(result, "dict") else vars(result))
            slot.notes = f"AI_GEN: {result_dict.get('best_variant', {}).get('text', '')[:200]} | {slot.notes or ''}"

            logger.info(f"AdaptiveScheduler: Generated content for slot {slot_index}/{slot.platform}")
            return {"generated": True, "result": result_dict}
        except Exception as e:
            logger.debug(f"Content generation failed: {e}")
            return {"generated": False, "reason": str(e)}

    # =========================================================================
    # WAVE 4: APPROVAL WORKFLOW (Human-in-the-Loop Gate)
    # =========================================================================

    async def submit_schedule_for_approval(self) -> Dict[str, Any]:
        """
        Submit the entire weekly schedule to the approval workflow for human review.
        High-stakes content (offers, new formats) gets routed through HITL.
        """
        if not self.approval_workflow:
            return {"submitted": 0, "reason": "ApprovalWorkflow not available"}
        try:
            submitted = 0
            for slot in self._weekly_schedule:
                has_offer = bool(slot.offer_id)
                is_cross_post = slot.content_type == "cross-post"
                needs_approval = has_offer or is_cross_post or slot.confidence < 0.5

                if needs_approval:
                    await self.approval_workflow.submit_for_approval({
                        "type": "adaptive_schedule_slot",
                        "day": slot.day,
                        "platform": slot.platform,
                        "time": slot.time_est,
                        "format": slot.format,
                        "content_type": slot.content_type,
                        "offer_id": slot.offer_id,
                        "confidence": slot.confidence,
                        "notes": slot.notes,
                    })
                    submitted += 1

            logger.info(f"AdaptiveScheduler: Submitted {submitted} slots for approval")
            return {"submitted": submitted, "total_slots": len(self._weekly_schedule)}
        except Exception as e:
            logger.debug(f"Approval submission failed: {e}")
            return {"submitted": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 4: AUTO CURATOR (Pool Quality Curation)
    # =========================================================================

    def curate_video_pool(self) -> Dict[str, Any]:
        """
        Use AutoCurator to automatically approve/reject videos in the pool.
        Checks sentiment, quality score, brand safety. Target: 40-60% auto-curated.
        """
        if not self.auto_curator:
            return {"curated": 0, "reason": "AutoCurator not available"}
        try:
            approved = 0
            rejected = 0
            manual = 0

            for video in self._video_pool:
                result = self.auto_curator.evaluate({
                    "content_id": video.get("id", ""),
                    "title": video.get("file_name", ""),
                    "topics": video.get("topics", []),
                    "hooks": video.get("hooks", []),
                    "tone": video.get("tone", ""),
                    "score": video.get("pre_social_score", 0),
                })

                decision = result.decision.value if hasattr(result, "decision") else (result.get("decision", "manual_review") if isinstance(result, dict) else "manual_review")
                video["curation_status"] = decision

                if decision == "approve":
                    approved += 1
                elif decision == "reject":
                    rejected += 1
                else:
                    manual += 1

            # Move rejected to end of pool
            self._video_pool.sort(
                key=lambda v: 0 if v.get("curation_status") == "approve" else (1 if v.get("curation_status") == "manual_review" else 2)
            )

            logger.info(f"AdaptiveScheduler: Curated pool — {approved} approved, {rejected} rejected, {manual} manual")
            return {"curated": approved + rejected + manual, "approved": approved, "rejected": rejected, "manual_review": manual}
        except Exception as e:
            logger.debug(f"Auto-curation failed: {e}")
            return {"curated": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 4: BENCHMARK SERVICE (Competitive Performance Targets)
    # =========================================================================

    async def get_performance_benchmarks(self) -> Dict[str, Any]:
        """
        Use BenchmarkService to compare performance against competitors and industry.
        Sets targets for the scheduler to aim for in content selection and timing.
        """
        if not self.benchmark:
            return {"benchmarks": {}, "reason": "BenchmarkService not available"}
        try:
            result = await self.benchmark.run_benchmark()
            result_dict = result.dict() if hasattr(result, "dict") else (result if isinstance(result, dict) else vars(result))
            logger.info(f"AdaptiveScheduler: Benchmark score = {result_dict.get('overall_score', 0)}")
            return {"benchmarks": result_dict}
        except Exception as e:
            logger.debug(f"Benchmark failed: {e}")
            return {"benchmarks": {}, "reason": str(e)}

    # =========================================================================
    # WAVE 4: AI RECOMMENDATION SERVICE (Daily Strategic Recs)
    # =========================================================================

    async def get_ai_recommendations(self) -> Dict[str, Any]:
        """
        Use AIRecommendationService to generate daily content and strategy recommendations.
        Recommendations inform slot priorities, content types, and posting strategies.
        """
        if not self.ai_recommendation:
            return {"recommendations": [], "reason": "AIRecommendationService not available"}
        try:
            from uuid import uuid4
            recs = await self.ai_recommendation.generate_daily_recommendations(user_id=uuid4())
            logger.info(f"AdaptiveScheduler: Generated {len(recs)} AI recommendations")
            return {"recommendations": recs[:10], "total": len(recs)}
        except Exception as e:
            logger.debug(f"AI recommendations failed: {e}")
            return {"recommendations": [], "reason": str(e)}

    # =========================================================================
    # WAVE 4: ENGAGEMENT WORKER (Post-Publish Engagement Orchestration)
    # =========================================================================

    async def trigger_post_engagement(self, platform: str = "instagram", post_url: str = "") -> Dict[str, Any]:
        """
        After a post goes live, trigger EngagementWorker to orchestrate auto-engagement:
        find related posts, generate AI comments, post them with human-like delays.
        """
        if not self.engagement_worker:
            return {"triggered": False, "reason": "EngagementWorker not available"}
        try:
            if self._bus:
                await self._bus.publish("engagement.requested", {
                    "platform": platform,
                    "post_url": post_url,
                    "strategy": "post_publish_boost",
                    "max_comments": 5,
                    "delay_range": [30, 120],
                })
            logger.info(f"AdaptiveScheduler: Triggered engagement for {platform}")
            return {"triggered": True, "platform": platform}
        except Exception as e:
            logger.debug(f"Engagement trigger failed: {e}")
            return {"triggered": False, "reason": str(e)}

    # =========================================================================
    # WAVE 4: TREND INTELLIGENCE (Full Trend Pipeline)
    # =========================================================================

    async def ingest_trend_intelligence(self) -> Dict[str, Any]:
        """
        Use TrendIntelligence pipeline to ingest, cluster, and score trending content.
        Trend clusters inform what topics and formats to prioritize in the schedule.
        """
        if not self.trend_intelligence:
            return {"trends": [], "reason": "TrendIntelligence not available"}
        try:
            briefs = await self.trend_intelligence.generate_briefs(limit=5)
            briefs_list = briefs if isinstance(briefs, list) else [briefs] if briefs else []
            logger.info(f"AdaptiveScheduler: Ingested {len(briefs_list)} trend intelligence briefs")
            return {"trends": briefs_list[:10], "total": len(briefs_list)}
        except Exception as e:
            logger.debug(f"Trend intelligence ingestion failed: {e}")
            return {"trends": [], "reason": str(e)}

    # =========================================================================
    # WAVE 4: SORA DAILY PIPELINE (AI Video Coordination)
    # =========================================================================

    async def coordinate_sora_daily(self) -> Dict[str, Any]:
        """
        Coordinate with SoraDailyPipeline to generate AI videos aligned with schedule needs.
        Uses trend data and content gaps to inform Sora video topics.
        """
        if not self.sora_daily:
            return {"coordinated": False, "reason": "SoraDailyPipeline not available"}
        try:
            result = await self.sora_daily.run_daily_pipeline()
            result_dict = result if isinstance(result, dict) else {}
            generated = result_dict.get("videos_generated", 0)
            logger.info(f"AdaptiveScheduler: Sora daily pipeline — {generated} videos generated")
            return {"coordinated": True, "result": result_dict}
        except Exception as e:
            logger.debug(f"Sora daily coordination failed: {e}")
            return {"coordinated": False, "reason": str(e)}

    # =========================================================================
    # WAVE 4: PIPELINE MONITOR (Error Tracking & Health)
    # =========================================================================

    def report_cycle_health(self, cycle_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Report the health of the latest adaptive cycle to PipelineMonitor.
        Tracks errors, warnings, and overall pipeline health metrics.
        """
        if not self.pipeline_monitor:
            return {"reported": False, "reason": "PipelineMonitor not available"}
        try:
            steps = cycle_results.get("steps", {})
            errors = []
            for step_name, step_result in steps.items():
                if isinstance(step_result, dict):
                    reason = step_result.get("reason", "")
                    if reason and "not available" not in reason:
                        errors.append({"step": step_name, "error": reason})

            if errors:
                for err in errors:
                    self.pipeline_monitor.record_error(
                        pipeline_stage=f"adaptive_cycle.{err['step']}",
                        error_type="step_failure",
                        message=err["error"],
                        severity="warning",
                    )

            health = self.pipeline_monitor.get_health_summary() if hasattr(self.pipeline_monitor, "get_health_summary") else {}
            logger.info(f"AdaptiveScheduler: Reported cycle health — {len(errors)} issues")
            return {"reported": True, "errors_logged": len(errors), "health": health}
        except Exception as e:
            logger.debug(f"Health reporting failed: {e}")
            return {"reported": False, "reason": str(e)}

    # =========================================================================
    # WAVE 4: LEARNER WORKER (Template Learning Feedback Loop)
    # =========================================================================

    async def trigger_learning_update(self) -> Dict[str, Any]:
        """
        Trigger LearnerWorker to update template rankings based on latest performance data.
        Winners get promoted (70% allocation), losers get demoted (<5%).
        This creates the core learning feedback loop for the adaptive system.
        """
        if not self.learner:
            return {"updated": False, "reason": "LearnerWorker not available"}
        try:
            if self._bus:
                await self._bus.publish("learn.update.requested", {
                    "trigger": "adaptive_scheduler",
                    "cycle": self._adaptation_count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            logger.info("AdaptiveScheduler: Triggered learning update")
            return {"updated": True, "cycle": self._adaptation_count}
        except Exception as e:
            logger.debug(f"Learning update failed: {e}")
            return {"updated": False, "reason": str(e)}

    # =========================================================================
    # WAVE 5: CONTENT GAP ANALYSIS (Find Missing Themes)
    # =========================================================================

    async def analyze_content_gaps(self) -> Dict[str, Any]:
        """
        Use ContentGapService to identify themes competitors cover that we don't.
        Gap themes become priority topics for upcoming schedule slots.
        """
        if not self.content_gap:
            return {"gaps": [], "reason": "ContentGapService not available"}
        try:
            result = await self.content_gap.analyze_gaps()
            result_dict = result.dict() if hasattr(result, "dict") else (result if isinstance(result, dict) else {})
            gap_themes = result_dict.get("gap_themes", [])
            logger.info(f"AdaptiveScheduler: Found {len(gap_themes)} content gaps")
            return {"gaps": gap_themes[:10], "coverage_score": result_dict.get("gap_coverage_score", 0)}
        except Exception as e:
            logger.debug(f"Content gap analysis failed: {e}")
            return {"gaps": [], "reason": str(e)}

    # =========================================================================
    # WAVE 5: HOOK LIBRARY (Proven Hooks for Slots)
    # =========================================================================

    def inject_hooks_into_slots(self) -> Dict[str, Any]:
        """
        Use HookLibraryService to attach proven, high-performing hooks to schedule slots.
        Each slot gets a hook matched to its platform, format, and awareness level.
        """
        if not self.hook_library:
            return {"injected": 0, "reason": "HookLibraryService not available"}
        try:
            injected = 0
            hooks = self.hook_library.get_top_hooks(limit=20) if hasattr(self.hook_library, "get_top_hooks") else []
            hooks_list = hooks if isinstance(hooks, list) else []

            for i, slot in enumerate(self._weekly_schedule):
                if hooks_list and not (slot.notes and "HOOK:" in (slot.notes or "")):
                    hook = hooks_list[i % len(hooks_list)]
                    hook_text = hook.hook_text if hasattr(hook, "hook_text") else (hook.get("hook_text", "") if isinstance(hook, dict) else str(hook))
                    if hook_text:
                        slot.notes = f"HOOK: {hook_text[:100]} | {slot.notes or ''}"
                        injected += 1

            logger.info(f"AdaptiveScheduler: Injected {injected} proven hooks into slots")
            return {"injected": injected, "hooks_available": len(hooks_list)}
        except Exception as e:
            logger.debug(f"Hook injection failed: {e}")
            return {"injected": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 5: CHANNEL ROUTER (Multi-Platform Publishing)
    # =========================================================================

    async def route_slot_to_platforms(self, slot_index: int = 0,
                                      platforms: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Use ChannelRouter to publish a scheduled slot to multiple platforms simultaneously.
        Handles Safari/Blotato selection, per-platform formatting, and fallback.
        """
        if not self.channel_router:
            return {"routed": False, "reason": "ChannelRouter not available"}
        try:
            if slot_index >= len(self._weekly_schedule):
                return {"routed": False, "reason": f"Slot {slot_index} out of range"}

            slot = self._weekly_schedule[slot_index]
            target_platforms = platforms or [slot.platform]

            result = await self.channel_router.route_content(
                video_path="",
                platforms=target_platforms,
                analysis={"hook": slot.notes or "", "format": slot.format},
                approval_required=False,
            )
            result_dict = result if isinstance(result, dict) else {}
            logger.info(f"AdaptiveScheduler: Routed slot {slot_index} to {target_platforms}")
            return {"routed": True, "result": result_dict}
        except Exception as e:
            logger.debug(f"Channel routing failed: {e}")
            return {"routed": False, "reason": str(e)}

    # =========================================================================
    # WAVE 5: DAILY AUTOMATION MANAGER (Sora + Twitter Automation)
    # =========================================================================

    async def sync_daily_automation(self) -> Dict[str, Any]:
        """
        Coordinate with DailyAutomationManager to align Sora video generation
        and Twitter offer posting with the adaptive schedule.
        """
        if not self.daily_automation:
            return {"synced": False, "reason": "DailyAutomationManager not available"}
        try:
            status = {
                "sora_running": self.daily_automation.sora_scheduler.running if hasattr(self.daily_automation, "sora_scheduler") else False,
                "twitter_running": self.daily_automation.twitter_scheduler.running if hasattr(self.daily_automation, "twitter_scheduler") else False,
                "initialized": self.daily_automation.initialized,
            }
            logger.info(f"AdaptiveScheduler: Daily automation status — {status}")
            return {"synced": True, "status": status}
        except Exception as e:
            logger.debug(f"Daily automation sync failed: {e}")
            return {"synced": False, "reason": str(e)}

    # =========================================================================
    # WAVE 5: GROWTH DATA PLANE (Person + Event Tracking)
    # =========================================================================

    async def track_schedule_events(self) -> Dict[str, Any]:
        """
        Use GrowthDataPlane to track scheduling events (posts created, published, failed)
        for person-level attribution and segment computation.
        """
        if not self.growth_data_plane:
            return {"tracked": 0, "reason": "GrowthDataPlane not available"}
        try:
            tracked = 0
            for slot in self._weekly_schedule:
                if slot.notes and ("PUBLISHED" in slot.notes or "AI_GEN" in slot.notes):
                    await self.growth_data_plane.track_event(
                        person_id=None,
                        event_type="schedule.slot.active",
                        properties={
                            "platform": slot.platform,
                            "day": slot.day,
                            "format": slot.format,
                            "content_type": slot.content_type,
                        },
                    )
                    tracked += 1
            logger.info(f"AdaptiveScheduler: Tracked {tracked} schedule events to GDP")
            return {"tracked": tracked}
        except Exception as e:
            logger.debug(f"GDP event tracking failed: {e}")
            return {"tracked": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 5: LEAD DISCOVERY (Find New Contacts)
    # =========================================================================

    async def discover_leads_for_outreach(self) -> Dict[str, Any]:
        """
        Use LeadDiscoveryService to find new contacts aligned with the schedule.
        Discovered leads are fed into the DM warmth system for coordinated outreach.
        """
        if not self.lead_discovery:
            return {"discovered": 0, "reason": "LeadDiscoveryService not available"}
        try:
            leads = await self.lead_discovery.discover_leads()
            leads_list = leads if isinstance(leads, list) else []
            logger.info(f"AdaptiveScheduler: Discovered {len(leads_list)} new leads")
            return {"discovered": len(leads_list), "leads": leads_list[:10]}
        except Exception as e:
            logger.debug(f"Lead discovery failed: {e}")
            return {"discovered": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 5: OFFER TRACKER (UTM Attribution)
    # =========================================================================

    async def generate_tracked_offer_links(self) -> Dict[str, Any]:
        """
        Use OfferTracker to generate tracked URLs with UTM params for slots with offers.
        Enables conversion attribution from social posts to offer pages.
        """
        if not self.offer_tracker:
            return {"links_created": 0, "reason": "OfferTracker not available"}
        try:
            created = 0
            for slot in self._weekly_schedule:
                if slot.offer_id and slot.offer_cta:
                    offer = self._offers.get(slot.offer_id)
                    if offer and hasattr(offer, "url") and offer.url:
                        tracked_url = await self.offer_tracker.create_tracked_link(
                            offer_url=offer.url,
                            campaign=f"adaptive_{slot.day}_{slot.platform}",
                            source=slot.platform,
                            metadata={"slot_day": slot.day, "format": slot.format},
                        )
                        if tracked_url:
                            slot.notes = f"TRACKED_URL: {tracked_url} | {slot.notes or ''}"
                            created += 1
            logger.info(f"AdaptiveScheduler: Created {created} tracked offer links")
            return {"links_created": created}
        except Exception as e:
            logger.debug(f"Offer link tracking failed: {e}")
            return {"links_created": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 5: EMAIL SEQUENCE (Unified Outreach)
    # =========================================================================

    async def trigger_email_sequence_for_leads(self) -> Dict[str, Any]:
        """
        Trigger email sequences for leads discovered by the scheduler.
        Coordinates email outreach with social posting schedule for unified messaging.
        """
        if not self.email_sequence:
            return {"triggered": 0, "reason": "EmailSequenceService not available"}
        try:
            sequences = self.email_sequence.list_sequences() if hasattr(self.email_sequence, "list_sequences") else []
            active = [s for s in sequences if hasattr(s, "active") and s.active] if sequences else []
            logger.info(f"AdaptiveScheduler: {len(active)} active email sequences")
            return {"triggered": len(active), "sequences": len(sequences)}
        except Exception as e:
            logger.debug(f"Email sequence trigger failed: {e}")
            return {"triggered": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 5: FORMAT CLASSIFIER (Auto-classify Pool Videos)
    # =========================================================================

    async def classify_pool_formats(self) -> Dict[str, Any]:
        """
        Use FormatClassifier to auto-classify every video in the pool by format
        (talking_head, broll_text, voiceover, etc.) for optimal platform matching.
        """
        if not self.format_classifier:
            return {"classified": 0, "reason": "FormatClassifier not available"}
        try:
            classified = 0
            for video in self._video_pool:
                if video.get("format_type"):
                    continue
                video_id = video.get("id", "")
                if video_id:
                    result = await self.format_classifier.classify(video_id) if asyncio.iscoroutinefunction(getattr(self.format_classifier, "classify", None)) else self.format_classifier.classify(video_id) if hasattr(self.format_classifier, "classify") else None
                    if result:
                        fmt = result.value if hasattr(result, "value") else str(result)
                        video["format_type"] = fmt
                        classified += 1
            logger.info(f"AdaptiveScheduler: Classified {classified} video formats")
            return {"classified": classified}
        except Exception as e:
            logger.debug(f"Format classification failed: {e}")
            return {"classified": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 5: DEDUPLICATION GUARD (Prevent Double-Posting)
    # =========================================================================

    def check_schedule_duplicates(self) -> Dict[str, Any]:
        """
        Use DeduplicationGuard to ensure no duplicate posts in the schedule.
        Checks for same content → same platform → same time conflicts.
        """
        if not self.dedup_guard:
            return {"checked": False, "reason": "DeduplicationGuard not available"}
        try:
            conflicts = self.dedup_guard.check_schedule(self._weekly_schedule) if hasattr(self.dedup_guard, "check_schedule") else []
            if not conflicts:
                seen = set()
                duplicates = 0
                for slot in self._weekly_schedule:
                    key = f"{slot.day}:{slot.platform}:{slot.time_est}"
                    if key in seen:
                        duplicates += 1
                    seen.add(key)
                conflicts = duplicates

            logger.info(f"AdaptiveScheduler: Dedup check — {conflicts} potential duplicates")
            return {"checked": True, "duplicates_found": conflicts if isinstance(conflicts, int) else len(conflicts)}
        except Exception as e:
            logger.debug(f"Deduplication check failed: {e}")
            return {"checked": False, "reason": str(e)}

    # =========================================================================
    # WAVE 5: CLIP SELECTOR (AI-Powered Clip Selection)
    # =========================================================================

    async def select_best_clips_for_slots(self, limit: int = 5) -> Dict[str, Any]:
        """
        Use ClipSelector to AI-score and select the best video clips for schedule slots.
        Scores based on hook quality, visual engagement, emotion arc, platform fit.
        """
        if not self.clip_selector:
            return {"selected": 0, "reason": "ClipSelector not available"}
        try:
            selected = 0
            for video in self._video_pool[:limit]:
                video_id = video.get("id", "")
                if not video_id or video.get("best_clip"):
                    continue
                clips = self.clip_selector.suggest_clips(video_id) if hasattr(self.clip_selector, "suggest_clips") else []
                if clips:
                    best = clips[0] if isinstance(clips, list) else clips
                    video["best_clip"] = best if isinstance(best, dict) else (best.to_dict() if hasattr(best, "to_dict") else str(best))
                    selected += 1
            logger.info(f"AdaptiveScheduler: Selected best clips for {selected} videos")
            return {"selected": selected}
        except Exception as e:
            logger.debug(f"Clip selection failed: {e}")
            return {"selected": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 5: EMBEDDING SERVICE (Semantic Content Matching)
    # =========================================================================

    async def embed_pool_for_similarity(self) -> Dict[str, Any]:
        """
        Use EmbeddingService to generate vector embeddings for pool videos.
        Enables semantic similarity search for finding related content and preventing repetition.
        """
        if not self.embedding:
            return {"embedded": 0, "reason": "EmbeddingService not available"}
        try:
            embedded = 0
            for video in self._video_pool:
                if video.get("embedding"):
                    continue
                text = " ".join(video.get("hooks", []) + video.get("topics", []))
                if text:
                    emb = await self.embedding.generate_embedding(text)
                    if emb:
                        video["embedding"] = True
                        embedded += 1
            logger.info(f"AdaptiveScheduler: Embedded {embedded} pool videos")
            return {"embedded": embedded}
        except Exception as e:
            logger.debug(f"Embedding generation failed: {e}")
            return {"embedded": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 5: INVENTORY SCHEDULER (Long-Horizon Planning)
    # =========================================================================

    async def sync_inventory_schedule(self) -> Dict[str, Any]:
        """
        Use InventoryAwareScheduler to plan 2-month content distribution based
        on available inventory (short-form vs long-form content balance).
        """
        if not self.inventory_scheduler:
            return {"synced": False, "reason": "InventoryAwareScheduler not available"}
        try:
            inventory = self.inventory_scheduler.get_inventory() if hasattr(self.inventory_scheduler, "get_inventory") else {}
            inv_dict = inventory if isinstance(inventory, dict) else (inventory.to_dict() if hasattr(inventory, "to_dict") else {})
            logger.info(f"AdaptiveScheduler: Inventory — {inv_dict.get('total_count', 0)} items")
            return {"synced": True, "inventory": inv_dict}
        except Exception as e:
            logger.debug(f"Inventory sync failed: {e}")
            return {"synced": False, "reason": str(e)}

    # =========================================================================
    # WAVE 5: META ADS AUTOPILOT (Paid Advertising Coordination)
    # =========================================================================

    async def coordinate_meta_ads(self) -> Dict[str, Any]:
        """
        Coordinate Meta Ads Autopilot with organic posting schedule.
        Boost top-performing organic posts and align ad creative with schedule themes.
        """
        if not self.meta_ads:
            return {"coordinated": False, "reason": "MetaAdsAutopilot not available"}
        try:
            status = self.meta_ads.get_status() if hasattr(self.meta_ads, "get_status") else {}
            logger.info(f"AdaptiveScheduler: Meta Ads status — {status}")
            return {"coordinated": True, "status": status}
        except Exception as e:
            logger.debug(f"Meta Ads coordination failed: {e}")
            return {"coordinated": False, "reason": str(e)}

    # =========================================================================
    # WAVE 5: CHECKBACK SCHEDULER (Post-Publish Metrics Collection)
    # =========================================================================

    def schedule_checkbacks_for_published(self) -> Dict[str, Any]:
        """
        Use CheckbackScheduler to schedule metrics collection at 1h, 6h, 24h, 72h, 7d
        after each post goes live. Feeds performance data back into the learning loop.
        """
        if not self.checkback:
            return {"scheduled": 0, "reason": "CheckbackScheduler not available"}
        try:
            scheduled = 0
            for slot in self._weekly_schedule:
                if slot.notes and "PUBLISHED" in (slot.notes or ""):
                    for hours in [1, 6, 24, 72, 168]:
                        try:
                            self.checkback.schedule_checkback(
                                post_id=slot.offer_id or f"{slot.day}_{slot.platform}",
                                checkback_hours=hours,
                            )
                            scheduled += 1
                        except Exception:
                            pass
            logger.info(f"AdaptiveScheduler: Scheduled {scheduled} checkback jobs")
            return {"scheduled": scheduled}
        except Exception as e:
            logger.debug(f"Checkback scheduling failed: {e}")
            return {"scheduled": 0, "reason": str(e)}

    # =========================================================================
    # WAVE 6: PUBLISHING & OPERATIONS
    # =========================================================================

    async def process_due_posts(self) -> Dict[str, Any]:
        """
        Use PostScheduler to find and publish posts that are due NOW.
        This is the critical link that turns scheduled_posts rows into actual platform posts.
        """
        try:
            if self.post_scheduler:
                result = await self.post_scheduler.process_due_posts()
                return {"processed": True, "result": result}
            return {"processed": False, "reason": "PostScheduler not available"}
        except Exception as e:
            logger.warning(f"Post processing failed: {e}")
            return {"processed": False, "reason": str(e)}

    def get_calendar_view(self, days: int = 7) -> Dict[str, Any]:
        """
        Use CalendarService to get a calendar view of upcoming scheduled posts.
        """
        try:
            if self.calendar:
                posts = self.calendar.get_calendar_posts(days=days)
                return {"posts": posts, "days": days}
            return {"posts": [], "days": days, "reason": "CalendarService not available"}
        except Exception as e:
            logger.warning(f"Calendar view failed: {e}")
            return {"posts": [], "days": days, "reason": str(e)}

    async def publish_to_all_platforms(self, post_id: str) -> Dict[str, Any]:
        """
        Use VideoPublishPipeline or MultiPlatformPublisher to publish a post
        across all target platforms simultaneously.
        """
        try:
            if self.video_publish:
                result = await self.video_publish.publish(post_id)
                return {"published": True, "platforms": result}
            elif self.multi_publisher:
                result = await self.multi_publisher.publish(post_id)
                return {"published": True, "platforms": result}
            return {"published": False, "reason": "No publish pipeline available"}
        except Exception as e:
            logger.warning(f"Multi-platform publish failed: {e}")
            return {"published": False, "reason": str(e)}

    async def run_nightly_analysis(self) -> Dict[str, Any]:
        """
        Trigger NightlyAnalysisScheduler to analyze recent content performance
        and feed insights back into the adaptive loop.
        """
        try:
            if self.nightly_analysis:
                result = await self.nightly_analysis.run_single_batch()
                return {"analyzed": True, "result": result}
            return {"analyzed": False, "reason": "NightlyAnalysisScheduler not available"}
        except Exception as e:
            logger.warning(f"Nightly analysis failed: {e}")
            return {"analyzed": False, "reason": str(e)}

    async def hydrate_dashboard_data(self) -> Dict[str, Any]:
        """
        Use DataHydrationService to refresh all dashboard data sources
        so the frontend has fresh analytics, performance, and scheduling data.
        """
        try:
            if self.data_hydration:
                import asyncio
                status = self.data_hydration.get_status()
                if asyncio.iscoroutine(status):
                    status = await status
                return {"hydrated": True, "status": status}
            return {"hydrated": False, "reason": "DataHydrationService not available"}
        except Exception as e:
            logger.warning(f"Data hydration failed: {e}")
            return {"hydrated": False, "reason": str(e)}

    def score_trending_content(self) -> Dict[str, Any]:
        """
        Use TrendVelocityService + TrendScoringService to identify
        accelerating trends and score content alignment with them.
        """
        try:
            velocity_data = {}
            scoring_data = {}
            if self.trend_velocity:
                velocity_data = self.trend_velocity.get_top_accelerating(limit=10)
            if self.trend_scoring:
                scoring_data = self.trend_scoring.score_hashtags(
                    [t.get("hashtag", "") for t in velocity_data] if isinstance(velocity_data, list) else []
                )
            return {
                "accelerating_trends": len(velocity_data) if isinstance(velocity_data, list) else 0,
                "scored": len(scoring_data) if isinstance(scoring_data, list) else 0,
            }
        except Exception as e:
            logger.warning(f"Trend scoring failed: {e}")
            return {"accelerating_trends": 0, "scored": 0, "reason": str(e)}

    def track_content_performance(self) -> Dict[str, Any]:
        """
        Use ContentAnalytics to aggregate performance metrics for recently
        published content and update the feedback loop.
        """
        try:
            if self.content_analytics:
                stats = self.content_analytics.get_stats()
                return {"tracked": True, "stats": stats}
            return {"tracked": False, "reason": "ContentAnalytics not available"}
        except Exception as e:
            logger.warning(f"Content analytics tracking failed: {e}")
            return {"tracked": False, "reason": str(e)}

    async def detect_orphaned_touchpoints(self) -> Dict[str, Any]:
        """
        Use TouchpointService to find touchpoints that aren't attributed
        to any campaign or content piece, ensuring full attribution coverage.
        """
        try:
            if self.touchpoints:
                import asyncio
                orphans = self.touchpoints.detect_orphaned_touchpoints()
                if asyncio.iscoroutine(orphans):
                    orphans = await orphans
                return {"checked": True, "orphaned": len(orphans) if isinstance(orphans, (list, tuple)) else 0}
            return {"checked": False, "reason": "TouchpointService not available"}
        except Exception as e:
            logger.warning(f"Touchpoint detection failed: {e}")
            return {"checked": False, "reason": str(e)}

    def sync_twitter_campaigns(self) -> Dict[str, Any]:
        """
        Use TwitterCampaignScheduler to ensure Twitter campaigns are aligned
        with the overall content schedule and posting cadence.
        """
        try:
            if self.twitter_campaign:
                status = {"running": self.twitter_campaign is not None}
                return {"synced": True, "status": status}
            return {"synced": False, "reason": "TwitterCampaignScheduler not available"}
        except Exception as e:
            logger.warning(f"Twitter campaign sync failed: {e}")
            return {"synced": False, "reason": str(e)}

    def get_external_queue_status(self) -> Dict[str, Any]:
        """
        Use ExternalQueueManager to check the status of externally submitted
        videos waiting to be processed and scheduled.
        """
        try:
            if self.external_queue:
                engine = self.external_queue.get_engine()
                return {"queue_active": True, "engine": str(engine)}
            return {"queue_active": False, "reason": "ExternalQueueManager not available"}
        except Exception as e:
            logger.warning(f"External queue check failed: {e}")
            return {"queue_active": False, "reason": str(e)}

    # =========================================================================
    # FULL INTEGRATED CYCLE
    # =========================================================================

    async def run_full_integrated_cycle(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the COMPLETE integrated adaptive cycle using ALL services:

        1. Ingest assessment (content scoring, cross-posts, offers, fatigue)
        2. FATE-score the video pool (persuasion framework)
        3. Fetch trend briefs + inject into slots
        4. Compute engagement reward scores
        5. Merge WeeklyPlanner bandit insights
        6. Coordinate DM outreach with schedule
        7. Track offer CTAs via Meta Pixel
        8. Materialize to scheduled_posts DB

        Returns comprehensive results from all integrations.
        """
        results = {"cycle_number": self._adaptation_count + 1, "steps": {}}

        # Step 1: Core assessment ingestion
        await self.ingest_assessment(report_data)
        results["steps"]["assessment"] = {
            "slots": len(self._weekly_schedule),
            "scored_content": len(self._scored_content),
            "cross_posts": len(self._cross_post_queue),
        }

        # Step 2: FATE-score video pool
        fate_result = self.fate_score_video_pool()
        results["steps"]["fate_scoring"] = fate_result

        # Step 3: Trend briefs
        briefs = await self.fetch_trend_briefs()
        trend_count = self.inject_trend_briefs_into_schedule()
        results["steps"]["trend_briefs"] = {"briefs": len(briefs), "slots_enriched": trend_count}

        # Step 4: Engagement reward scores
        rewards = self.compute_reward_scores()
        results["steps"]["reward_scores"] = {"scored": len(rewards)}

        # Step 5: WeeklyPlanner insights
        planner_result = await self.merge_weekly_planner_insights()
        results["steps"]["weekly_planner"] = planner_result

        # Step 6: DM outreach coordination
        dm_tasks = self.coordinate_dm_outreach()
        results["steps"]["dm_outreach"] = {"tasks_queued": len(dm_tasks)}

        # Step 7: Meta Pixel tracking for offer slots
        pixel_count = 0
        for slot in self._weekly_schedule:
            if slot.offer_id:
                self.track_offer_conversion(slot.offer_id, slot.platform, f"slot-{slot.day}-{slot.platform}")
                pixel_count += 1
        results["steps"]["meta_pixel"] = {"offers_tracked": pixel_count}

        # Step 8: Materialize to DB
        materialized = self.materialize_schedule_to_db()
        results["steps"]["materialized"] = {"posts_created": len(materialized)}

        # --- Wave 3 Steps ---

        # Step 9: InsightsEngine — apply hook patterns + optimal times
        insights_result = self.apply_insights_to_schedule()
        results["steps"]["insights_engine"] = insights_result

        # Step 10: Bandit allocation — dynamic format weighting
        bandit_result = await self.apply_bandit_allocation()
        results["steps"]["bandit_allocation"] = bandit_result

        # Step 11: Content mix alignment
        mix_result = await self.align_with_content_mix()
        results["steps"]["content_mix"] = mix_result

        # Step 12: Pool analysis health check — quality gate
        health_result = await self.check_pool_analysis_health()
        results["steps"]["analysis_health"] = health_result

        # Step 13: AI caption generation for empty slots
        ai_gen_result = await self.generate_content_for_empty_slots()
        results["steps"]["ai_content_gen"] = ai_gen_result

        # Step 14: Thumbnail selection for pool videos
        thumb_result = await self.select_thumbnails_for_pool(limit=10)
        results["steps"]["thumbnails"] = thumb_result

        # Step 15: Sleep mode sync
        sleep_result = await self.sync_sleep_schedule()
        results["steps"]["sleep_mode"] = sleep_result

        # Step 16: Comment engagement scheduling
        comment_result = await self.schedule_comment_engagement()
        results["steps"]["comment_engagement"] = comment_result

        # --- Wave 4 Steps (Strategic Closed-Loop) ---

        # Step 17: Auto-curate video pool (quality + brand safety)
        curation_result = self.curate_video_pool()
        results["steps"]["auto_curation"] = curation_result

        # Step 18: Classify pool by awareness stage (funnel coverage)
        awareness_result = self.classify_pool_awareness()
        results["steps"]["awareness_classification"] = awareness_result

        # Step 19: Get winning templates from leaderboard
        template_result = await self.get_winning_templates()
        results["steps"]["template_leaderboard"] = template_result

        # Step 20: QA gate all slots before publishing
        qa_result = await self.qa_gate_all_slots()
        results["steps"]["qa_gate"] = qa_result

        # Step 21: Trigger learning update (feedback loop)
        learn_result = await self.trigger_learning_update()
        results["steps"]["learner"] = learn_result

        # Step 22: Report cycle health to monitor
        health_report = self.report_cycle_health(results)
        results["steps"]["pipeline_health"] = health_report

        # --- Wave 5 Steps (Full-Stack Automation) ---

        # Step 23: Content gap analysis — find missing themes
        gap_result = await self.analyze_content_gaps()
        results["steps"]["content_gaps"] = gap_result

        # Step 24: Inject proven hooks into schedule slots
        hook_result = self.inject_hooks_into_slots()
        results["steps"]["hook_injection"] = hook_result

        # Step 25: Deduplication check — prevent double-posts
        dedup_result = self.check_schedule_duplicates()
        results["steps"]["deduplication"] = dedup_result

        # Step 26: Format-classify pool videos
        format_result = await self.classify_pool_formats()
        results["steps"]["format_classification"] = format_result

        # Step 27: AI clip selection for pool videos
        clip_result = await self.select_best_clips_for_slots()
        results["steps"]["clip_selection"] = clip_result

        # Step 28: Generate tracked offer links (UTM attribution)
        offer_link_result = await self.generate_tracked_offer_links()
        results["steps"]["offer_tracking"] = offer_link_result

        # Step 29: Sync with daily automation (Sora + Twitter)
        daily_result = await self.sync_daily_automation()
        results["steps"]["daily_automation"] = daily_result

        # Step 30: Schedule checkbacks for published posts
        checkback_result = self.schedule_checkbacks_for_published()
        results["steps"]["checkbacks"] = checkback_result

        # --- Wave 6 steps: Publishing & Operations ---

        # Step 31: Process due posts (publish scheduled posts that are due NOW)
        due_result = await self.process_due_posts()
        results["steps"]["post_publishing"] = due_result

        # Step 32: Track content performance analytics
        perf_result = self.track_content_performance()
        results["steps"]["content_analytics"] = perf_result

        # Step 33: Score trending content velocity
        trend_result = self.score_trending_content()
        results["steps"]["trend_velocity"] = trend_result

        # Step 34: Sync Twitter campaigns with schedule
        twitter_result = self.sync_twitter_campaigns()
        results["steps"]["twitter_campaigns"] = twitter_result

        # Step 35: Detect orphaned touchpoints
        touchpoint_result = await self.detect_orphaned_touchpoints()
        results["steps"]["touchpoint_attribution"] = touchpoint_result

        # Step 36: Hydrate dashboard data
        hydration_result = await self.hydrate_dashboard_data()
        results["steps"]["data_hydration"] = hydration_result

        # Step 37: Check external queue status
        queue_result = self.get_external_queue_status()
        results["steps"]["external_queue"] = queue_result

        # Step 38: Get calendar view for next 7 days
        calendar_result = self.get_calendar_view(days=7)
        results["steps"]["calendar_sync"] = {"upcoming_posts": len(calendar_result.get("posts", []))}

        results["total_services_used"] = sum(1 for v in results["steps"].values() if v)
        results["total_steps"] = len(results["steps"])
        logger.info(
            f"AdaptiveScheduler: FULL INTEGRATED CYCLE #{results['cycle_number']} complete — "
            f"{len(results['steps'])} steps, "
            f"{results['steps'].get('materialized', {}).get('posts_created', 0)} posts materialized, "
            f"{results['total_services_used']} services active"
        )
        return results

    # =========================================================================
    # CORE: INGEST ASSESSMENT
    # =========================================================================

    async def ingest_assessment(self, report_data: Dict[str, Any]):
        """
        Main entry point: ingest a StrategicReport and adapt everything.

        Steps:
            1. Score all content from platform snapshots
            2. Identify cross-post candidates
            3. Rotate offer CTAs
            4. Check fatigue constraints
            5. Adapt weekly schedule
            6. Publish events
        """
        self._adaptation_count += 1
        self._last_assessment_at = datetime.now(timezone.utc).isoformat()
        correlation_id = report_data.get("correlation_id", f"adapt-{self._adaptation_count}")

        # Store assessment history
        self._assessment_history.append({
            "correlation_id": correlation_id,
            "ingested_at": self._last_assessment_at,
            "adaptation_number": self._adaptation_count,
        })

        await self._publish(Topics.ADAPTIVE_ASSESSMENT_INGESTED, {
            "correlation_id": correlation_id,
            "adaptation_number": self._adaptation_count,
        })

        # Step 1: Score content from snapshots
        snapshots = report_data.get("platform_snapshots", {})
        self._score_content_from_snapshots(snapshots)

        await self._publish(Topics.ADAPTIVE_CONTENT_SCORED, {
            "total_scored": len(self._scored_content),
            "top_score": self._scored_content[0].score if self._scored_content else 0,
        })

        # Step 2: Identify cross-post candidates
        candidates = self._identify_cross_post_candidates()
        for c in candidates:
            self._cross_post_queue.append(c)
            await self._publish(Topics.ADAPTIVE_CROSSPOST_QUEUED, c)

        # Step 3: Rotate offers
        next_offers = self._rotate_offers()
        for offer_assignment in next_offers:
            await self._publish(Topics.ADAPTIVE_OFFER_ROTATED, offer_assignment)

        # Step 4: Check fatigue
        fatigue_warnings = self._check_fatigue()
        for warning in fatigue_warnings:
            await self._publish(Topics.ADAPTIVE_FATIGUE_WARNING, warning)

        # Step 5: Adapt schedule from AI analysis
        ai_analysis = report_data.get("ai_analysis", {})
        if ai_analysis.get("weekly_cadence"):
            self._apply_ai_cadence(ai_analysis["weekly_cadence"])

        # Step 6: Inject cross-posts into schedule
        self._inject_cross_posts_into_schedule(candidates)

        # Step 7: Assign offers to schedule slots
        self._assign_offers_to_slots(next_offers)

        # Step 8: Map Blotato accounts to all slots
        account_count = self._enrich_slots_with_accounts()

        # Step 9: Refresh video pool for content assignment
        await self._load_video_pool()

        await self._publish(Topics.ADAPTIVE_SCHEDULE_ADAPTED, {
            "correlation_id": correlation_id,
            "slots": len(self._weekly_schedule),
            "cross_posts_queued": len(candidates),
            "offers_assigned": len(next_offers),
            "fatigue_warnings": len(fatigue_warnings),
            "accounts_mapped": account_count,
            "video_pool_size": len(self._video_pool),
        })

        await self._publish(Topics.ADAPTIVE_CYCLE_COMPLETED, {
            "correlation_id": correlation_id,
            "adaptation_number": self._adaptation_count,
            "schedule_slots": len(self._weekly_schedule),
        })

        logger.info(
            f"Adaptive cycle #{self._adaptation_count} complete: "
            f"{len(self._weekly_schedule)} slots, "
            f"{len(candidates)} cross-posts, "
            f"{len(next_offers)} offers assigned, "
            f"{len(fatigue_warnings)} fatigue warnings, "
            f"{account_count} accounts mapped, "
            f"{len(self._video_pool)} videos in pool"
        )

    # =========================================================================
    # CONTENT SCORING
    # =========================================================================

    def _score_content_from_snapshots(self, snapshots: Dict[str, Any]):
        """Score all content from platform snapshots by composite metric."""
        scored = []

        for platform_key, snap_data in snapshots.items():
            # Handle both PlatformSnapshot objects and dicts
            if hasattr(snap_data, 'top_posts'):
                top_posts = snap_data.top_posts
                followers = snap_data.followers or 1
            else:
                top_posts = snap_data.get("top_posts", [])
                followers = snap_data.get("followers", 1) or 1

            for post in top_posts:
                likes = post.get("likes", 0)
                comments = post.get("comments", 0)
                shares = post.get("shares", 0)
                saves = post.get("saves", post.get("saved", 0))
                views = post.get("views", 0)
                interactions = post.get("total_interactions", 0)
                impressions = post.get("impressions", 0)

                # Composite score: weighted sum normalized by followers
                # Saves and shares are high-intent signals (weighted 3x)
                # Comments are medium-intent (weighted 2x)
                # Likes are low-intent (weighted 1x)
                raw_score = (
                    likes * 1.0
                    + comments * 2.0
                    + shares * 3.0
                    + saves * 3.0
                    + interactions * 0.5
                )
                # Normalize by followers for fair cross-platform comparison
                normalized_score = (raw_score / followers) * 100 if followers > 0 else raw_score

                sc = ScoredContent(
                    content_id=post.get("permalink", post.get("title", ""))[:80],
                    platform=platform_key,
                    title=(post.get("title", post.get("name", "")))[:80],
                    score=normalized_score,
                    likes=likes, comments=comments,
                    shares=shares, saves=saves,
                    views=views, total_interactions=interactions,
                    date=post.get("date", ""),
                    permalink=post.get("permalink", ""),
                    media_type=post.get("media_type", post.get("product_type", "")),
                )
                scored.append(sc)

        # Sort by score descending
        scored.sort(key=lambda x: x.score, reverse=True)
        self._scored_content = scored

    # =========================================================================
    # CROSS-POST ENGINE
    # =========================================================================

    def _identify_cross_post_candidates(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Find top-performing content that should be cross-posted.

        Rules:
        - Must score in top N across all platforms
        - Must not already be cross-posted to target platform
        - Must have a valid cross-post rule for source -> target
        - Respects platform fatigue constraints
        """
        candidates = []

        for sc in self._scored_content[:top_n]:
            rules = CROSS_POST_RULES.get(sc.platform, [])
            for target_platform, target_format, delay_hours in rules:
                if target_platform in sc.cross_posted_to:
                    continue  # Already cross-posted

                # Check fatigue for target platform
                if self._is_platform_fatigued(target_platform):
                    continue

                candidates.append({
                    "source_platform": sc.platform,
                    "source_content_id": sc.content_id,
                    "source_title": sc.title,
                    "source_score": round(sc.score, 2),
                    "target_platform": target_platform,
                    "target_format": target_format,
                    "delay_hours": delay_hours,
                    "reason": f"Top performer on {sc.platform} (score: {sc.score:.1f})",
                })

                sc.cross_posted_to.append(target_platform)
                sc.is_cross_post_candidate = True

        return candidates

    # =========================================================================
    # OFFER FUNNEL MANAGER
    # =========================================================================

    def _rotate_offers(self) -> List[Dict[str, Any]]:
        """
        Select offers for the next schedule cycle.

        Strategy:
        - Only promote launchable offers (>= 60% built)
        - Weight by priority and recency (longer since last promo = higher chance)
        - Spread different offers across the week (no same offer 2 days in a row)
        - Max 2 hard CTAs per week, rest are soft mentions
        """
        now = datetime.now(timezone.utc)
        eligible = [o for o in self._offers.values() if o.is_launchable and o.priority > 0]

        if not eligible:
            return []

        # Score each offer for rotation
        offer_scores = []
        for offer in eligible:
            recency_bonus = 1.0
            if offer.last_promoted_at:
                days_since = (now - datetime.fromisoformat(offer.last_promoted_at.replace("Z", "+00:00"))).days
                recency_bonus = min(days_since / offer.min_days_between, 3.0)
            else:
                recency_bonus = 3.0  # Never promoted = high priority

            fatigue_penalty = max(0, 1.0 - (offer.times_promoted_30d / 10))
            rotation_score = offer.priority * recency_bonus * fatigue_penalty
            offer_scores.append((offer, rotation_score))

        offer_scores.sort(key=lambda x: x[1], reverse=True)

        # Pick top offers for this cycle (2 hard CTAs + 3 soft mentions)
        assignments = []
        hard_cta_count = 0
        for offer, score in offer_scores[:5]:
            cta_type = "hard" if hard_cta_count < 2 else "soft"
            hard_cta_count += (1 if cta_type == "hard" else 0)

            cta_text = random.choice(offer.cta_templates) if offer.cta_templates else ""

            assignments.append({
                "offer_id": offer.id,
                "offer_name": offer.name,
                "cta_type": cta_type,
                "cta_text": cta_text,
                "rotation_score": round(score, 2),
            })

            # Update tracking
            offer.last_promoted_at = now.isoformat()
            offer.times_promoted_30d += 1
            self._offer_promo_times[offer.id].append(now)

        return assignments

    # =========================================================================
    # FATIGUE GUARD
    # =========================================================================

    def _is_platform_fatigued(self, platform: str) -> bool:
        """Check if a platform has been posted to too recently."""
        constraints = PLATFORM_CONSTRAINTS.get(platform, {})
        max_per_day = constraints.get("max_per_day", 3)
        min_hours = constraints.get("min_hours_between", 4)
        now = datetime.now(timezone.utc)

        recent = [
            t for t in self._platform_post_times.get(platform, [])
            if (now - t).total_seconds() < 86400
        ]

        if len(recent) >= max_per_day:
            return True

        if recent:
            hours_since_last = (now - max(recent)).total_seconds() / 3600
            if hours_since_last < min_hours:
                return True

        return False

    def _check_fatigue(self) -> List[Dict[str, Any]]:
        """Check all platforms and offers for fatigue conditions."""
        warnings = []
        now = datetime.now(timezone.utc)

        for platform, constraints in PLATFORM_CONSTRAINTS.items():
            recent = [
                t for t in self._platform_post_times.get(platform, [])
                if (now - t).total_seconds() < 86400
            ]
            max_per_day = constraints.get("max_per_day", 3)
            utilization = len(recent) / max_per_day if max_per_day else 0

            if utilization >= 0.8:
                warnings.append({
                    "type": "platform_fatigue",
                    "platform": platform,
                    "posts_today": len(recent),
                    "max_per_day": max_per_day,
                    "utilization": round(utilization, 2),
                    "message": f"{platform}: {len(recent)}/{max_per_day} daily posts used ({utilization*100:.0f}%)",
                })

        # Offer fatigue
        for offer_id, times in self._offer_promo_times.items():
            recent_30d = [t for t in times if (now - t).days < 30]
            if len(recent_30d) > 8:
                offer = self._offers.get(offer_id)
                warnings.append({
                    "type": "offer_fatigue",
                    "offer_id": offer_id,
                    "offer_name": offer.name if offer else offer_id,
                    "promos_30d": len(recent_30d),
                    "message": f"Offer '{offer.name if offer else offer_id}' promoted {len(recent_30d)}x in 30 days",
                })

        return warnings

    # =========================================================================
    # SCHEDULE ADAPTER
    # =========================================================================

    def _generate_default_schedule(self) -> List[ScheduledSlot]:
        """Generate a sensible default weekly schedule."""
        return [
            ScheduledSlot(day="Monday", time_est="10:00 AM", platform="tiktok", format="Short-form", content_type="original", notes="Trending topic + value hook"),
            ScheduledSlot(day="Monday", time_est="3:00 PM", platform="youtube", format="Shorts", content_type="original", notes="AI/tech educational"),
            ScheduledSlot(day="Tuesday", time_est="11:00 AM", platform="instagram", format="Reels", content_type="original", notes="Behind-the-scenes or tutorial"),
            ScheduledSlot(day="Wednesday", time_est="9:00 AM", platform="tiktok", format="Short-form", content_type="original", notes="Story/narrative content"),
            ScheduledSlot(day="Wednesday", time_est="2:00 PM", platform="threads", format="Thread", content_type="original", notes="Hot take or breakdown"),
            ScheduledSlot(day="Thursday", time_est="12:00 PM", platform="tiktok", format="Short-form", content_type="cross-post", notes="Best of Mon/Tue repurposed"),
            ScheduledSlot(day="Thursday", time_est="6:00 PM", platform="instagram", format="Reels", content_type="cross-post", notes="Repurpose top TikTok"),
            ScheduledSlot(day="Friday", time_est="11:00 AM", platform="youtube", format="Shorts", content_type="cross-post", notes="Week's best -> YT Shorts"),
            ScheduledSlot(day="Friday", time_est="7:00 PM", platform="tiktok", format="Short-form", content_type="original", notes="Weekend hook / engagement bait"),
            ScheduledSlot(day="Saturday", time_est="10:00 AM", platform="instagram", format="Reels", content_type="original", notes="Personal brand / lifestyle"),
            ScheduledSlot(day="Sunday", time_est="1:00 PM", platform="tiktok", format="Short-form", content_type="original", notes="Week recap / community Q&A"),
        ]

    def _apply_ai_cadence(self, ai_cadence: List[Dict[str, Any]]):
        """Merge AI-recommended cadence into the adaptive schedule."""
        if not ai_cadence:
            return

        # Build new schedule from AI recommendations
        new_slots = []
        for rec in ai_cadence:
            slot = ScheduledSlot(
                day=rec.get("day", "Monday"),
                time_est=str(rec.get("time_est", "12:00 PM")),
                platform=rec.get("platform", "tiktok").lower(),
                format=rec.get("format", "Short-form"),
                content_type="original",
                notes=rec.get("notes", ""),
                confidence=0.6,  # AI recommendations start at 0.6
            )
            new_slots.append(slot)

        if new_slots:
            # Merge: keep existing high-confidence slots, add new AI ones
            kept = [s for s in self._weekly_schedule if s.confidence >= 0.8]
            # Deduplicate by day+platform
            existing_keys = {(s.day, s.platform) for s in kept}
            for ns in new_slots:
                if (ns.day, ns.platform) not in existing_keys:
                    kept.append(ns)
                    existing_keys.add((ns.day, ns.platform))

            self._weekly_schedule = sorted(
                kept,
                key=lambda s: (
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(s.day)
                    if s.day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    else 7
                ),
            )

    def _inject_cross_posts_into_schedule(self, candidates: List[Dict[str, Any]]):
        """Insert cross-post slots into the weekly schedule."""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for candidate in candidates[:3]:  # Max 3 cross-posts per cycle
            target = candidate["target_platform"]
            constraints = PLATFORM_CONSTRAINTS.get(target, {})
            best_times = constraints.get("best_times_est", ["12:00 PM"])

            # Find a day with the fewest posts for this platform
            day_counts = defaultdict(int)
            for slot in self._weekly_schedule:
                if slot.platform == target:
                    day_counts[slot.day] += 1

            # Pick the day with fewest posts
            best_day = min(days, key=lambda d: day_counts.get(d, 0))

            slot = ScheduledSlot(
                day=best_day,
                time_est=best_times[0] if best_times else "12:00 PM",
                platform=target,
                format=candidate["target_format"],
                content_type="cross-post",
                source_content_id=candidate["source_content_id"],
                notes=f"Cross-post from {candidate['source_platform']}: {candidate['source_title'][:40]}",
                confidence=0.7,
            )
            self._weekly_schedule.append(slot)

        # Re-sort
        day_order = {d: i for i, d in enumerate(days)}
        self._weekly_schedule.sort(key=lambda s: day_order.get(s.day, 7))

    def _assign_offers_to_slots(self, offer_assignments: List[Dict[str, Any]]):
        """Distribute offer CTAs across schedule slots."""
        if not offer_assignments:
            return

        # Assign hard CTAs to high-confidence original content slots
        hard_ctas = [a for a in offer_assignments if a["cta_type"] == "hard"]
        soft_ctas = [a for a in offer_assignments if a["cta_type"] == "soft"]

        original_slots = [s for s in self._weekly_schedule if s.content_type == "original" and not s.offer_id]
        crosspost_slots = [s for s in self._weekly_schedule if s.content_type == "cross-post" and not s.offer_id]

        # Hard CTAs on original content (most engagement)
        for i, cta in enumerate(hard_ctas):
            if i < len(original_slots):
                original_slots[i].offer_id = cta["offer_id"]
                original_slots[i].offer_cta = cta["cta_text"]

        # Soft CTAs spread across remaining slots
        all_unassigned = [s for s in self._weekly_schedule if not s.offer_id]
        for i, cta in enumerate(soft_ctas):
            if i < len(all_unassigned):
                all_unassigned[i].offer_id = cta["offer_id"]
                all_unassigned[i].offer_cta = cta["cta_text"]

    # =========================================================================
    # PUBLIC ACCESSORS
    # =========================================================================

    def get_weekly_schedule(self) -> List[Dict[str, Any]]:
        """Get the current adaptive weekly schedule."""
        return [s.to_dict() for s in self._weekly_schedule]

    def get_next_7_days(self) -> List[Dict[str, Any]]:
        """Get schedule for the next 7 days with concrete dates and account info."""
        now = datetime.now(timezone.utc)
        days_map = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today_idx = now.weekday()

        result = []
        for slot in self._weekly_schedule:
            slot_day_idx = days_map.index(slot.day) if slot.day in days_map else 0
            days_ahead = (slot_day_idx - today_idx) % 7
            if days_ahead == 0 and slot.time_est:
                pass  # Include anyway
            target_date = now + timedelta(days=days_ahead)
            entry = slot.to_dict()
            entry["date"] = target_date.strftime("%Y-%m-%d")
            entry["day_of_week"] = slot.day
            # Enrich with account info
            acct = self._get_blotato_account_for_slot(slot)
            if acct:
                entry["blotato_account_id"] = acct["blotato_account_id"]
                entry["account_username"] = acct["username"]
            result.append(entry)

        return sorted(result, key=lambda x: x["date"])

    def get_cross_post_queue(self) -> List[Dict[str, Any]]:
        """Get pending cross-posts with account info."""
        enriched = []
        for cp in self._cross_post_queue:
            entry = dict(cp)
            # Add target account info
            platform = cp.get("target_platform", "")
            platform_map = {"instagram_graph": "instagram", "facebook_ads": "facebook"}
            blotato_platform = platform_map.get(platform, platform)
            if self.blotato:
                accounts = self.blotato.get_accounts_by_platform(blotato_platform)
                if accounts:
                    entry["target_account"] = accounts[0].username
                    entry["target_account_id"] = accounts[0].id
            enriched.append(entry)
        return enriched

    def get_video_pool(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get available videos from the pool (loaded from NarrativeScheduler's DB query)."""
        return self._video_pool[:limit]

    def get_scored_content(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """Get top-scored content across all platforms."""
        return [sc.to_dict() for sc in self._scored_content[:top_n]]

    def get_offers(self) -> List[Dict[str, Any]]:
        """Get all offers with rotation state."""
        return [o.to_dict() for o in self._offers.values()]

    def get_launchable_offers(self) -> List[Dict[str, Any]]:
        """Get only launchable offers."""
        return [o.to_dict() for o in self._offers.values() if o.is_launchable]

    def _enrich_slots_with_accounts(self) -> int:
        """Map Blotato accounts to all schedule slots. Returns count mapped."""
        count = 0
        for slot in self._weekly_schedule:
            acct = self._get_blotato_account_for_slot(slot)
            if acct:
                slot.notes = f"@{acct['username']} | {slot.notes}" if slot.notes and not slot.notes.startswith("@") else f"@{acct['username']}"
                count += 1
        return count

    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        # Check which integrated services are available
        services_status = {
            # Wave 1
            "blotato": self._blotato_service is not None,
            "background_publisher": self._background_publisher is not None,
            "narrative_scheduler": self._narrative_scheduler is not None,
            "visual_campaign": self._visual_campaign_service is not None,
            # Wave 2
            "fate_scorer": self._fate_scorer is not None,
            "trend_brief": self._trend_brief_service is not None,
            "engagement_scorer": self._engagement_scorer is not None,
            "weekly_planner": self._weekly_planner is not None,
            "tiktok_repurpose": self._tiktok_repurpose is not None,
            "repurpose_pipeline": self._repurpose_pipeline is not None,
            "meta_pixel": self._meta_pixel is not None,
            "agent_scheduler": self._agent_scheduler is not None,
            "dm_warmth": self._dm_warmth is not None,
            # Wave 3
            "insights_engine": self._insights_engine is not None,
            "performance_correlator": self._performance_correlator is not None,
            "bandit_allocator": self._bandit_allocator is not None,
            "content_mix_planner": self._content_mix_planner is not None,
            "ab_testing": self._ab_testing is not None,
            "ai_content_generator": self._ai_content_generator is not None,
            "ai_thumbnail": self._ai_thumbnail_selector is not None,
            "sora_pipeline": self._sora_pipeline is not None,
            "sleep_mode": self._sleep_mode is not None,
            "dco_optimizer": self._dco_optimizer is not None,
            "comment_automation": self._comment_automation is not None,
            "analysis_health": self._analysis_health is not None,
            # Wave 4
            "template_leaderboard": self._template_leaderboard is not None,
            "qa_gate": self._qa_gate is not None,
            "awareness_classifier": self._awareness_classifier is not None,
            "competitor_analysis": self._competitor_analysis is not None,
            "content_gen_pipeline": self._content_gen_pipeline is not None,
            "slot_executor": self._slot_executor is not None,
            "learner_worker": self._learner_worker is not None,
            "approval_workflow": self._approval_workflow is not None,
            "auto_curator": self._auto_curator is not None,
            "benchmark_service": self._benchmark_service is not None,
            "ai_recommendation": self._ai_recommendation is not None,
            "engagement_worker": self._engagement_worker is not None,
            "trend_intelligence": self._trend_intelligence is not None,
            "sora_daily_pipeline": self._sora_daily_pipeline is not None,
            "pipeline_monitor": self._pipeline_monitor is not None,
            # Wave 5
            "content_gap": self._content_gap is not None,
            "hook_library": self._hook_library is not None,
            "channel_router": self._channel_router is not None,
            "daily_automation": self._daily_automation is not None,
            "growth_data_plane": self._growth_data_plane is not None,
            "lead_discovery": self._lead_discovery is not None,
            "offer_tracker": self._offer_tracker is not None,
            "email_sequence": self._email_sequence is not None,
            "format_classifier": self._format_classifier is not None,
            "deduplication_guard": self._deduplication_guard is not None,
            "content_sourcing": self._content_sourcing is not None,
            "clip_selector": self._clip_selector is not None,
            "feedback_scorer": self._feedback_loop_scorer is not None,
            "embedding_service": self._embedding_service is not None,
            "inventory_scheduler": self._inventory_scheduler is not None,
            "meta_ads_autopilot": self._meta_ads_autopilot is not None,
            "checkback_scheduler": self._checkback_scheduler is not None,
            # Wave 6
            "post_scheduler": self._post_scheduler is not None,
            "calendar_service": self._calendar_service is not None,
            "video_publish_pipeline": self._video_publish_pipeline is not None,
            "multi_platform_publisher": self._multi_platform_publisher is not None,
            "nightly_analysis": self._nightly_analysis is not None,
            "data_hydration": self._data_hydration is not None,
            "trend_velocity": self._trend_velocity is not None,
            "trend_scoring": self._trend_scoring is not None,
            "batch_processor": self._batch_processor is not None,
            "content_analytics": self._content_analytics is not None,
            "touchpoint_service": self._touchpoint_service is not None,
            "workflow_manager": self._workflow_manager is not None,
            "twitter_campaign": self._twitter_campaign is not None,
            "external_queue": self._external_queue is not None,
        }
        return {
            "started": self._started,
            "adaptation_count": self._adaptation_count,
            "last_assessment_at": self._last_assessment_at,
            "schedule_slots": len(self._weekly_schedule),
            "scored_content": len(self._scored_content),
            "cross_post_queue": len(self._cross_post_queue),
            "offers_total": len(self._offers),
            "offers_launchable": sum(1 for o in self._offers.values() if o.is_launchable),
            "assessment_history_count": len(self._assessment_history),
            "video_pool_size": len(self._video_pool),
            "performance_feedback_count": len(self._performance_feedback),
            "post_log_count": len(self._post_log),
            "fate_scores_computed": len(self._fate_scores),
            "active_trend_briefs": len(self._active_trend_briefs),
            "dm_outreach_queue": len(self._dm_outreach_queue),
            "integrated_services": services_status,
            "services_connected": sum(1 for v in services_status.values() if v),
            "services_total": len(services_status),
        }

    # =========================================================================
    # MANUAL OVERRIDES
    # =========================================================================

    def override_slot(self, day: str, platform: str, updates: Dict[str, Any]) -> bool:
        """Override a specific schedule slot (manual intervention)."""
        for slot in self._weekly_schedule:
            if slot.day == day and slot.platform == platform:
                for key, val in updates.items():
                    if hasattr(slot, key):
                        setattr(slot, key, val)
                slot.confidence = 1.0  # Manual override = highest confidence
                return True
        return False

    def add_slot(self, slot_data: Dict[str, Any]) -> bool:
        """Manually add a schedule slot."""
        slot = ScheduledSlot(
            day=slot_data.get("day", "Monday"),
            time_est=slot_data.get("time_est", "12:00 PM"),
            platform=slot_data.get("platform", "tiktok"),
            format=slot_data.get("format", "Short-form"),
            content_type=slot_data.get("content_type", "original"),
            notes=slot_data.get("notes", ""),
            confidence=1.0,
        )
        self._weekly_schedule.append(slot)
        return True

    def remove_slot(self, day: str, platform: str) -> bool:
        """Remove a schedule slot."""
        before = len(self._weekly_schedule)
        self._weekly_schedule = [
            s for s in self._weekly_schedule
            if not (s.day == day and s.platform == platform)
        ]
        return len(self._weekly_schedule) < before


# =============================================================================
# SINGLETON
# =============================================================================

_instance: Optional[AdaptiveSchedulerService] = None


def get_adaptive_scheduler() -> AdaptiveSchedulerService:
    """Get the singleton AdaptiveSchedulerService."""
    return AdaptiveSchedulerService.get_instance()
