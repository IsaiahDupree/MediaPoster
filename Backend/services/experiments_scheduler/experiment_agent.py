"""
Experiment Agent
================
AI-powered agent that plans, executes, and learns from experiments.
"""

import os
import logging
import json
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from enum import Enum

from .models import (
    Experiment,
    Hypothesis,
    ContentPattern,
    ExperimentStatus,
    HypothesisStatus,
    PostOrigin,
    OriginType,
)

logger = logging.getLogger(__name__)


class AgentActionType(str, Enum):
    """Available actions for the experiment agent."""
    
    # Content Discovery
    BROWSE_UGC_LIBRARY = "browse_ugc_library"
    SEARCH_BY_TOPIC = "search_by_topic"
    FILTER_BY_SCORE = "filter_by_score"
    
    # Content Analysis
    ANALYZE_VIDEO_HOOKS = "analyze_video_hooks"
    ANALYZE_PACING = "analyze_pacing"
    ANALYZE_AUDIO = "analyze_audio"
    DETECT_TRENDS = "detect_trends"
    
    # Content Editing
    TRIM_CLIP = "trim_clip"
    ADD_HOOK = "add_hook"
    CHANGE_MUSIC = "change_music"
    ADD_SUBTITLES = "add_subtitles"
    ADJUST_PACING = "adjust_pacing"
    CREATE_THUMBNAIL = "create_thumbnail"
    
    # AI Content Creation
    GENERATE_SCRIPT = "generate_script"
    GENERATE_VOICEOVER = "generate_voiceover"
    GENERATE_B_ROLL = "generate_b_roll"
    REMIX_CONTENT = "remix_content"
    
    # Scheduling
    SCHEDULE_POST = "schedule_post"
    SET_CAPTION = "set_caption"
    SET_HASHTAGS = "set_hashtags"
    TARGET_TIME_SLOT = "target_time_slot"
    
    # Experiment Management
    CREATE_HYPOTHESIS = "create_hypothesis"
    DEFINE_SUCCESS_CRITERIA = "define_success_criteria"
    TAG_EXPERIMENT = "tag_experiment"
    COMPARE_VARIANTS = "compare_variants"
    ANALYZE_RESULTS = "analyze_results"


@dataclass
class AgentAction:
    """An action taken by the experiment agent."""
    id: str = field(default_factory=lambda: str(uuid4()))
    experiment_id: str = ""
    action_type: AgentActionType = AgentActionType.BROWSE_UGC_LIBRARY
    action_params: Dict[str, Any] = field(default_factory=dict)
    
    # Execution
    status: str = "pending"  # pending, executing, completed, failed
    result: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    
    # Reasoning
    reasoning: str = ""
    expected_outcome: str = ""
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "action_type": self.action_type.value,
            "action_params": self.action_params,
            "status": self.status,
            "result": self.result,
            "error_message": self.error_message,
            "reasoning": self.reasoning,
            "expected_outcome": self.expected_outcome,
            "created_at": self.created_at.isoformat()
        }


class ExperimentAgent:
    """
    AI agent that plans and executes content experiments.
    
    The agent:
    - Creates hypotheses based on goals
    - Selects content and tools to test hypotheses
    - Schedules variants with proper tagging
    - Analyzes results and determines pass/fail
    - Learns patterns for future experiments
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.action_history: List[AgentAction] = []
    
    async def plan_experiment(
        self,
        goal: str,
        available_resources: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> Experiment:
        """
        Plan an experiment to achieve a goal.
        
        Args:
            goal: What we want to learn or achieve
            available_resources: Content, tools, accounts available
            constraints: Budget, time, risk limits
        
        Returns:
            Experiment with hypotheses and execution plan
        """
        experiment = Experiment(
            name=f"Experiment: {goal[:50]}",
            goal=goal,
            status=ExperimentStatus.DRAFT,
            resource_types=available_resources.get("types", ["ugc"])
        )
        
        # Generate hypotheses using AI
        hypotheses = await self._generate_hypotheses(goal, available_resources)
        experiment.hypotheses = hypotheses
        
        # Define success criteria
        experiment.success_criteria = {
            "min_improvement": 0.2,  # 20% improvement
            "min_confidence": 0.8,   # 80% confidence
            "min_sample_size": 10
        }
        
        logger.info(f"[ExperimentAgent] Planned experiment with {len(hypotheses)} hypotheses")
        
        return experiment
    
    async def _generate_hypotheses(
        self,
        goal: str,
        resources: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate testable hypotheses for a goal."""
        
        if not self.openai_api_key:
            return self._generate_basic_hypotheses(goal)
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            prompt = f"""Generate 3 testable hypotheses for this content experiment goal:

GOAL: {goal}

AVAILABLE RESOURCES:
- Content types: {resources.get('types', ['ugc'])}
- Tools: clip editing, subtitle generation, AI voiceover, thumbnail creation
- Platforms: TikTok, Instagram

For each hypothesis, provide:
1. Statement (what you're testing)
2. Independent variable (what you'll change)
3. Dependent variable (what you'll measure)
4. Control approach (baseline)
5. Variant approach (test)
6. Success metric (views, engagement_rate, watch_time)
7. Success threshold (e.g., 1.3 = 30% improvement)

Return as JSON array:
[
  {{
    "statement": "Videos with question hooks get more views",
    "independent_variable": "hook_type",
    "dependent_variable": "view_count",
    "control_description": "Statement hook",
    "variant_description": "Question hook",
    "success_metric": "view_count",
    "success_threshold": 1.3
  }}
]"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at designing content experiments."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            
            # Parse JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            hypotheses_data = json.loads(result_text.strip())
            
            hypotheses = []
            for data in hypotheses_data:
                h = Hypothesis(
                    statement=data.get("statement", ""),
                    independent_variable=data.get("independent_variable", ""),
                    dependent_variable=data.get("dependent_variable", ""),
                    control_description=data.get("control_description", ""),
                    variant_description=data.get("variant_description", ""),
                    success_metric=data.get("success_metric", "view_count"),
                    success_threshold=float(data.get("success_threshold", 1.2))
                )
                hypotheses.append(h)
            
            return hypotheses
            
        except Exception as e:
            logger.error(f"AI hypothesis generation failed: {e}")
            return self._generate_basic_hypotheses(goal)
    
    def _generate_basic_hypotheses(self, goal: str) -> List[Hypothesis]:
        """Generate basic hypotheses without AI."""
        return [
            Hypothesis(
                statement="Question hooks increase engagement",
                independent_variable="hook_type",
                dependent_variable="engagement_rate",
                control_description="Statement opening",
                variant_description="Question opening",
                success_metric="engagement_rate",
                success_threshold=1.2
            ),
            Hypothesis(
                statement="Subtitles improve watch time",
                independent_variable="subtitles",
                dependent_variable="avg_watch_time",
                control_description="No subtitles",
                variant_description="Word-level subtitles",
                success_metric="avg_watch_time",
                success_threshold=1.15
            )
        ]
    
    async def select_content_for_experiment(
        self,
        hypothesis: Hypothesis,
        content_pool: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """
        Select content for control and variant groups.
        
        Returns:
            Tuple of (control_video_ids, variant_video_ids)
        """
        # For A/B testing, we need similar content for both groups
        # Sort by score and alternate assignment
        sorted_content = sorted(
            content_pool,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        control_ids = []
        variant_ids = []
        
        for i, content in enumerate(sorted_content[:20]):  # Top 20
            if i % 2 == 0:
                control_ids.append(content.get("id"))
            else:
                variant_ids.append(content.get("id"))
        
        return control_ids, variant_ids
    
    async def execute_action(
        self,
        action: AgentAction
    ) -> AgentAction:
        """Execute an agent action."""
        action.status = "executing"
        action.executed_at = datetime.now()
        
        try:
            # Route to appropriate handler
            if action.action_type == AgentActionType.BROWSE_UGC_LIBRARY:
                action.result = await self._browse_ugc_library(action.action_params)
            
            elif action.action_type == AgentActionType.SEARCH_BY_TOPIC:
                action.result = await self._search_by_topic(action.action_params)
            
            elif action.action_type == AgentActionType.SCHEDULE_POST:
                action.result = await self._schedule_post(action.action_params)
            
            elif action.action_type == AgentActionType.ANALYZE_RESULTS:
                action.result = await self._analyze_results(action.action_params)
            
            elif action.action_type == AgentActionType.ADD_SUBTITLES:
                action.result = await self._add_subtitles(action.action_params)
            
            else:
                # Generic handler for unimplemented actions
                action.result = {"status": "not_implemented", "action": action.action_type.value}
            
            action.status = "completed"
            
        except Exception as e:
            action.status = "failed"
            action.error_message = str(e)
            logger.error(f"Action failed: {action.action_type.value} - {e}")
        
        action.completed_at = datetime.now()
        self.action_history.append(action)
        
        return action
    
    async def _browse_ugc_library(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Browse UGC library for content."""
        from sqlalchemy import create_engine, text
        
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
        engine = create_engine(DATABASE_URL)
        
        min_score = params.get("min_score", 60)
        limit = params.get("limit", 20)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT v.id, v.title, va.pre_social_score, va.topics
                FROM videos v
                JOIN video_analysis va ON va.video_id = v.id
                WHERE va.pre_social_score >= :min_score
                ORDER BY va.pre_social_score DESC
                LIMIT :limit
            """), {"min_score": min_score, "limit": limit})
            
            videos = [
                {
                    "id": str(row[0]),
                    "title": row[1],
                    "score": row[2],
                    "topics": row[3]
                }
                for row in result
            ]
        
        return {"videos": videos, "count": len(videos)}
    
    async def _search_by_topic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search content by topic."""
        topic = params.get("topic", "")
        # Implementation would search video_analysis.topics
        return {"videos": [], "topic": topic}
    
    async def _schedule_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a post with experiment tagging."""
        from sqlalchemy import create_engine, text
        
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
        engine = create_engine(DATABASE_URL)
        
        video_id = params.get("video_id")
        experiment_id = params.get("experiment_id")
        hypothesis_id = params.get("hypothesis_id")
        variant = params.get("variant", "control")
        platform = params.get("platform", "tiktok")
        scheduled_at = params.get("scheduled_at", datetime.now().isoformat())
        
        post_id = str(uuid4())
        
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO scheduled_posts (id, video_id, platform, scheduled_at, 
                    status, origin_type, experiment_id, hypothesis_id, variant)
                VALUES (:id, :video_id, :platform, :scheduled_at, 
                    'pending', 'experiments', :experiment_id, :hypothesis_id, :variant)
            """), {
                "id": post_id,
                "video_id": video_id,
                "platform": platform,
                "scheduled_at": scheduled_at,
                "experiment_id": experiment_id,
                "hypothesis_id": hypothesis_id,
                "variant": variant
            })
            conn.commit()
        
        return {"post_id": post_id, "scheduled": True}
    
    async def _analyze_results(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze experiment results."""
        experiment_id = params.get("experiment_id")
        hypothesis_id = params.get("hypothesis_id")
        
        # Would fetch metrics and calculate improvement
        return {
            "experiment_id": experiment_id,
            "hypothesis_id": hypothesis_id,
            "analysis": "pending_implementation"
        }
    
    async def _add_subtitles(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add subtitles to a video."""
        from services.clip_extraction import SubtitleGenerator, SubtitleConfig
        
        video_path = params.get("video_path")
        text = params.get("text", "")
        
        config = SubtitleConfig(words_per_subtitle=4)
        generator = SubtitleGenerator(config=config)
        
        success, output_path = await generator.add_subtitles_to_clip(
            video_path=video_path,
            text=text,
            start_time=0,
            end_time=30
        )
        
        return {"success": success, "output_path": output_path}
    
    def get_available_actions(self) -> List[Dict[str, str]]:
        """Get list of available actions with descriptions."""
        return [
            {"action": a.value, "category": self._get_action_category(a)}
            for a in AgentActionType
        ]
    
    def _get_action_category(self, action: AgentActionType) -> str:
        """Get category for an action type."""
        categories = {
            "discovery": ["browse_ugc_library", "search_by_topic", "filter_by_score"],
            "analysis": ["analyze_video_hooks", "analyze_pacing", "analyze_audio", "detect_trends"],
            "editing": ["trim_clip", "add_hook", "change_music", "add_subtitles", "adjust_pacing", "create_thumbnail"],
            "creation": ["generate_script", "generate_voiceover", "generate_b_roll", "remix_content"],
            "scheduling": ["schedule_post", "set_caption", "set_hashtags", "target_time_slot"],
            "experiment": ["create_hypothesis", "define_success_criteria", "tag_experiment", "compare_variants", "analyze_results"]
        }
        
        for category, actions in categories.items():
            if action.value in actions:
                return category
        return "other"
