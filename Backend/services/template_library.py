"""
Template Library Service
========================
Build and manage a template library from high-performing videos.
Extracts reusable patterns, beat sheets, and style fingerprints.

Addresses gap #4 from ANALYSIS_TO_GENERATION_DATA_AUDIT.md:
"Create template library from high-performing videos"
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from loguru import logger

from openai import OpenAI
from sqlalchemy import create_engine, text


@dataclass
class BeatTemplate:
    """Reusable beat/segment template"""
    role: str  # hook, problem, solution, proof, cta, transition
    duration_range: tuple  # (min_sec, max_sec)
    description: str
    emotion_cue: str
    visual_cue: str
    audio_cue: str
    text_overlay: Optional[str] = None


@dataclass
class VideoTemplate:
    """Complete video template derived from high-performing content"""
    template_id: Optional[str] = None
    
    # Identity
    name: str = ""
    slug: str = ""
    category: str = ""  # tutorial, story, listicle, transformation, etc.
    
    # Source
    source_video_ids: List[str] = field(default_factory=list)
    source_platform: str = ""
    
    # Performance metrics (aggregated from source videos)
    avg_engagement_rate: float = 0.0
    avg_views: int = 0
    avg_completion_rate: float = 0.0
    
    # Template structure
    target_duration_sec: int = 30
    beat_sheet: List[BeatTemplate] = field(default_factory=list)
    
    # Style fingerprint
    style: Dict[str, Any] = field(default_factory=dict)
    
    # Visual guidelines
    color_palette: List[str] = field(default_factory=list)
    dominant_shot_type: str = ""
    lighting_style: str = ""
    
    # Audio guidelines
    music_mood: str = ""
    music_tempo: str = ""
    voiceover_style: str = ""
    
    # Text/Caption style
    caption_style: str = ""
    hook_patterns: List[str] = field(default_factory=list)
    cta_patterns: List[str] = field(default_factory=list)
    
    # Usage guidance
    best_for: List[str] = field(default_factory=list)
    difficulty: str = "intermediate"
    estimated_production_time: str = "30 minutes"
    
    # Metadata
    times_used: int = 0
    avg_output_performance: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class TemplateMatch:
    """Result of matching content to a template"""
    template_id: str
    template_name: str
    match_score: float  # 0-100
    match_reasons: List[str]
    suggested_modifications: List[str]


class TemplateLibrary:
    """
    Manages a library of video templates extracted from high-performing content.
    Enables users to replicate successful formats with their own content.
    """
    
    # Standard beat structures by content type
    STANDARD_STRUCTURES = {
        "hook_problem_solution": [
            BeatTemplate("hook", (0, 3), "Attention grabber", "curiosity", "close-up or pattern interrupt", "sound effect or music drop"),
            BeatTemplate("problem", (3, 8), "State the problem", "frustration", "medium shot or b-roll", "tension music"),
            BeatTemplate("solution", (8, 25), "Deliver value", "relief/excitement", "mix of shots", "upbeat music"),
            BeatTemplate("cta", (25, 30), "Call to action", "urgency", "direct to camera", "music fade")
        ],
        "listicle": [
            BeatTemplate("hook", (0, 3), "Preview the list", "curiosity", "text overlay with number", "energetic intro"),
            BeatTemplate("item_1", (3, 10), "First point", "interest", "demonstrate or show", "consistent background"),
            BeatTemplate("item_2", (10, 17), "Second point", "building", "demonstrate or show", "maintain energy"),
            BeatTemplate("item_3", (17, 24), "Third point", "climax", "best example", "peak energy"),
            BeatTemplate("cta", (24, 30), "Wrap up and CTA", "satisfaction", "summary visual", "conclusive music")
        ],
        "story_transformation": [
            BeatTemplate("hook", (0, 3), "Tease the transformation", "curiosity", "before glimpse or reaction", "suspense music"),
            BeatTemplate("before", (3, 10), "Show the problem state", "empathy", "authentic footage", "somber tone"),
            BeatTemplate("journey", (10, 20), "The transformation process", "hope", "progress montage", "building music"),
            BeatTemplate("after", (20, 27), "Show the result", "triumph", "reveal shot", "triumphant music"),
            BeatTemplate("cta", (27, 30), "Inspire action", "motivation", "direct address", "uplifting close")
        ],
        "tutorial_quick": [
            BeatTemplate("hook", (0, 2), "What you'll learn", "promise", "end result preview", "attention sound"),
            BeatTemplate("step_1", (2, 10), "First step", "clarity", "close-up of action", "instructional tone"),
            BeatTemplate("step_2", (10, 18), "Second step", "progress", "close-up of action", "maintain pace"),
            BeatTemplate("step_3", (18, 26), "Final step", "achievement", "completion shot", "approaching end"),
            BeatTemplate("result", (26, 30), "Show result + CTA", "satisfaction", "final result beauty shot", "success music")
        ],
        "myth_bust": [
            BeatTemplate("hook", (0, 4), "State the common belief", "surprise", "text overlay of myth", "dramatic sting"),
            BeatTemplate("reveal", (4, 10), "Reveal it's wrong", "shock", "reaction or proof", "tension release"),
            BeatTemplate("truth", (10, 24), "Explain the reality", "education", "evidence and examples", "explanatory tone"),
            BeatTemplate("takeaway", (24, 30), "What to do instead", "empowerment", "actionable advice", "confident close")
        ]
    }
    
    def __init__(
        self,
        db_url: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
        self.engine = create_engine(self.db_url)
        
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
    
    async def create_template_from_video(
        self,
        video_id: str,
        analysis_data: Dict[str, Any],
        performance_metrics: Dict[str, Any]
    ) -> VideoTemplate:
        """
        Create a template from a high-performing video's analysis.
        
        Args:
            video_id: Source video ID
            analysis_data: Deep analysis including beat sheet, style, etc.
            performance_metrics: Engagement metrics for the video
            
        Returns:
            VideoTemplate ready to save
        """
        logger.info(f"Creating template from video {video_id}")
        
        # Extract key components
        beat_sheet = analysis_data.get("beat_sheet", analysis_data.get("scene_structure", []))
        visual_analysis = analysis_data.get("visual_analysis", {})
        hooks = analysis_data.get("hooks", [])
        tone = analysis_data.get("tone", "")
        music = analysis_data.get("music_suggestion", {})
        
        # Determine category from content type
        content_type = analysis_data.get("content_type", "general")
        category = self._map_content_type_to_category(content_type)
        
        # Build beat templates from analysis
        beats = []
        if beat_sheet:
            for beat in beat_sheet:
                beats.append(BeatTemplate(
                    role=beat.get("role", "content"),
                    duration_range=(
                        beat.get("start_sec", 0),
                        beat.get("end_sec", beat.get("start_sec", 0) + 5)
                    ),
                    description=beat.get("summary", ""),
                    emotion_cue=beat.get("emotion", "neutral"),
                    visual_cue=beat.get("visual_description", ""),
                    audio_cue=beat.get("audio_cue", "")
                ))
        else:
            # Use standard structure based on category
            beats = self.STANDARD_STRUCTURES.get(category, self.STANDARD_STRUCTURES["hook_problem_solution"])
        
        # Generate template name
        template_name = await self._generate_template_name(
            category, hooks, tone, performance_metrics
        )
        
        return VideoTemplate(
            name=template_name,
            slug=self._slugify(template_name),
            category=category,
            source_video_ids=[video_id],
            source_platform=analysis_data.get("platform", ""),
            avg_engagement_rate=performance_metrics.get("engagement_rate", 0),
            avg_views=performance_metrics.get("views", 0),
            avg_completion_rate=performance_metrics.get("completion_rate", 0),
            target_duration_sec=int(analysis_data.get("transcription_duration_sec", 30)),
            beat_sheet=beats,
            style={
                "tone": tone,
                "pacing": analysis_data.get("pacing", "medium"),
                "energy": self._determine_energy(tone, music),
                "format_tags": analysis_data.get("format_tags", [])
            },
            color_palette=visual_analysis.get("color_palette", []),
            dominant_shot_type=visual_analysis.get("dominant_shot_type", "medium"),
            lighting_style=visual_analysis.get("dominant_lighting", "natural"),
            music_mood=music.get("mood", "upbeat"),
            music_tempo=music.get("tempo", "medium"),
            voiceover_style=tone,
            caption_style=visual_analysis.get("caption_style", "default"),
            hook_patterns=hooks[:3] if hooks else [],
            cta_patterns=self._extract_cta_patterns(analysis_data),
            best_for=self._determine_best_for(category, analysis_data),
            difficulty=self._assess_difficulty(beats, visual_analysis),
            estimated_production_time=self._estimate_production_time(beats)
        )
    
    def _map_content_type_to_category(self, content_type: str) -> str:
        """Map content type to template category"""
        mapping = {
            "tutorial": "tutorial_quick",
            "how-to": "tutorial_quick",
            "educational": "hook_problem_solution",
            "tips": "listicle",
            "list": "listicle",
            "story": "story_transformation",
            "transformation": "story_transformation",
            "before-after": "story_transformation",
            "myth": "myth_bust",
            "debunk": "myth_bust",
            "reaction": "hook_problem_solution",
            "review": "hook_problem_solution"
        }
        
        content_lower = content_type.lower()
        for key, category in mapping.items():
            if key in content_lower:
                return category
        
        return "hook_problem_solution"  # Default
    
    def _determine_energy(self, tone: str, music: Dict) -> str:
        """Determine energy level from tone and music"""
        high_energy_words = ["exciting", "energetic", "fast", "upbeat", "enthusiastic"]
        low_energy_words = ["calm", "peaceful", "slow", "relaxed", "chill"]
        
        combined = f"{tone} {music.get('mood', '')} {music.get('tempo', '')}".lower()
        
        if any(w in combined for w in high_energy_words):
            return "high"
        elif any(w in combined for w in low_energy_words):
            return "low"
        return "medium"
    
    def _extract_cta_patterns(self, analysis_data: Dict) -> List[str]:
        """Extract CTA patterns from analysis"""
        patterns = []
        
        cta = analysis_data.get("call_to_action", {})
        if cta:
            if cta.get("text"):
                patterns.append(cta["text"])
            if cta.get("type"):
                patterns.append(f"CTA Type: {cta['type']}")
        
        return patterns
    
    def _determine_best_for(self, category: str, analysis_data: Dict) -> List[str]:
        """Determine what this template is best for"""
        best_for = []
        
        category_uses = {
            "tutorial_quick": ["educational content", "how-to videos", "quick tips"],
            "listicle": ["roundups", "top X lists", "recommendations"],
            "story_transformation": ["success stories", "before/after", "journeys"],
            "hook_problem_solution": ["problem-solving", "value content", "tips"],
            "myth_bust": ["controversial takes", "myth debunking", "education"]
        }
        
        best_for.extend(category_uses.get(category, []))
        
        # Add from pillar tags
        pillars = analysis_data.get("pillar_tags", [])
        for pillar in pillars[:2]:
            best_for.append(f"{pillar} content")
        
        return best_for[:5]
    
    def _assess_difficulty(self, beats: List[BeatTemplate], visual: Dict) -> str:
        """Assess production difficulty"""
        score = 0
        
        # More beats = more complex
        score += len(beats) * 5
        
        # Complex visuals
        if visual.get("dominant_shot_type") in ["overhead", "tracking"]:
            score += 15
        
        # Multiple text overlays
        if visual.get("caption_style") == "fast_captions":
            score += 10
        
        if score > 30:
            return "advanced"
        elif score > 15:
            return "intermediate"
        return "beginner"
    
    def _estimate_production_time(self, beats: List[BeatTemplate]) -> str:
        """Estimate production time"""
        beat_count = len(beats) if isinstance(beats, list) else 4
        
        if beat_count <= 3:
            return "15-20 minutes"
        elif beat_count <= 5:
            return "25-35 minutes"
        else:
            return "45-60 minutes"
    
    def _slugify(self, name: str) -> str:
        """Convert name to URL-safe slug"""
        import re
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        return slug.strip('-')
    
    async def _generate_template_name(
        self,
        category: str,
        hooks: List[str],
        tone: str,
        metrics: Dict
    ) -> str:
        """Generate a descriptive template name"""
        if not self.client:
            # Fallback name
            return f"{category.replace('_', ' ').title()} Template"
        
        prompt = f"""Generate a short, memorable template name (3-5 words) for a video template.

Category: {category}
Sample hooks: {hooks[:2] if hooks else 'N/A'}
Tone: {tone}
Performance: {metrics.get('engagement_rate', 0):.1%} engagement

The name should describe the format/style, not the specific content topic.
Examples: "Quick Tutorial Hook", "3-Point Listicle", "Story Transformation Arc"

Return just the name, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.7
            )
            return response.choices[0].message.content.strip().strip('"')
        except:
            return f"{category.replace('_', ' ').title()} Template"
    
    async def match_content_to_template(
        self,
        content_analysis: Dict[str, Any]
    ) -> List[TemplateMatch]:
        """
        Find best matching templates for given content.
        
        Args:
            content_analysis: Analysis of user's content
            
        Returns:
            List of matching templates sorted by match score
        """
        matches = []
        
        # Get all templates
        templates = await self.list_templates(limit=50)
        
        content_type = content_analysis.get("content_type", "")
        tone = content_analysis.get("tone", "")
        topics = content_analysis.get("topics", [])
        duration = content_analysis.get("transcription_duration_sec", 30)
        
        for template in templates:
            score = 0
            reasons = []
            modifications = []
            
            # Category match
            if template.get("category") in content_type.lower():
                score += 30
                reasons.append("Content type matches template category")
            
            # Tone match
            if template.get("style", {}).get("tone", "").lower() == tone.lower():
                score += 20
                reasons.append("Matching tone/energy")
            
            # Duration match
            template_duration = template.get("target_duration_sec", 30)
            duration_diff = abs(duration - template_duration)
            if duration_diff < 5:
                score += 20
                reasons.append("Similar duration")
            elif duration_diff < 15:
                score += 10
                modifications.append(f"Adjust duration from {duration:.0f}s to {template_duration}s")
            
            # Beat count compatibility
            beat_count = len(template.get("beat_sheet", []))
            if beat_count > 0:
                score += 10
                reasons.append(f"{beat_count}-beat structure available")
            
            # High performance bonus
            if template.get("avg_engagement_rate", 0) > 0.05:
                score += 10
                reasons.append("High-performing format")
            
            if score > 20:  # Minimum threshold
                matches.append(TemplateMatch(
                    template_id=template.get("template_id", ""),
                    template_name=template.get("name", "Unknown"),
                    match_score=min(100, score),
                    match_reasons=reasons,
                    suggested_modifications=modifications
                ))
        
        # Sort by match score
        matches.sort(key=lambda m: m.match_score, reverse=True)
        
        return matches[:5]  # Top 5 matches
    
    async def save_template(self, template: VideoTemplate) -> str:
        """Save template to database"""
        try:
            with self.engine.connect() as conn:
                # Convert beat sheet to JSON-serializable format
                beat_sheet_json = []
                for beat in template.beat_sheet:
                    if isinstance(beat, BeatTemplate):
                        beat_sheet_json.append({
                            "role": beat.role,
                            "duration_range": beat.duration_range,
                            "description": beat.description,
                            "emotion_cue": beat.emotion_cue,
                            "visual_cue": beat.visual_cue,
                            "audio_cue": beat.audio_cue,
                            "text_overlay": beat.text_overlay
                        })
                    else:
                        beat_sheet_json.append(beat)
                
                result = conn.execute(text("""
                    INSERT INTO video_template_library (
                        name, slug, category, source_video_ids, source_platform,
                        avg_engagement_rate, avg_views, avg_completion_rate,
                        target_duration_sec, beat_sheet, style,
                        color_palette, dominant_shot_type, lighting_style,
                        music_mood, music_tempo, voiceover_style,
                        caption_style, hook_patterns, cta_patterns,
                        best_for, difficulty, estimated_production_time
                    ) VALUES (
                        :name, :slug, :category, :source_ids, :platform,
                        :engagement, :views, :completion,
                        :duration, :beat_sheet, :style,
                        :colors, :shot_type, :lighting,
                        :music_mood, :music_tempo, :voiceover,
                        :caption, :hooks, :ctas,
                        :best_for, :difficulty, :production_time
                    )
                    ON CONFLICT (slug) DO UPDATE SET
                        avg_engagement_rate = :engagement,
                        avg_views = :views,
                        updated_at = NOW()
                    RETURNING template_id
                """), {
                    "name": template.name,
                    "slug": template.slug,
                    "category": template.category,
                    "source_ids": template.source_video_ids,
                    "platform": template.source_platform,
                    "engagement": template.avg_engagement_rate,
                    "views": template.avg_views,
                    "completion": template.avg_completion_rate,
                    "duration": template.target_duration_sec,
                    "beat_sheet": beat_sheet_json,
                    "style": template.style,
                    "colors": template.color_palette,
                    "shot_type": template.dominant_shot_type,
                    "lighting": template.lighting_style,
                    "music_mood": template.music_mood,
                    "music_tempo": template.music_tempo,
                    "voiceover": template.voiceover_style,
                    "caption": template.caption_style,
                    "hooks": template.hook_patterns,
                    "ctas": template.cta_patterns,
                    "best_for": template.best_for,
                    "difficulty": template.difficulty,
                    "production_time": template.estimated_production_time
                })
                conn.commit()
                row = result.fetchone()
                template.template_id = str(row[0])
                return template.template_id
        except Exception as e:
            logger.error(f"Failed to save template: {e}")
            raise
    
    async def list_templates(
        self,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """List templates from library"""
        query = """
            SELECT template_id, name, slug, category, 
                   avg_engagement_rate, avg_views, target_duration_sec,
                   beat_sheet, style, best_for, difficulty,
                   times_used, created_at
            FROM video_template_library
            WHERE 1=1
        """
        params = {"limit": limit}
        
        if category:
            query += " AND category = :category"
            params["category"] = category
        
        query += " ORDER BY avg_engagement_rate DESC, times_used DESC LIMIT :limit"
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                templates = []
                for row in result:
                    templates.append({
                        "template_id": str(row[0]),
                        "name": row[1],
                        "slug": row[2],
                        "category": row[3],
                        "avg_engagement_rate": row[4],
                        "avg_views": row[5],
                        "target_duration_sec": row[6],
                        "beat_sheet": row[7],
                        "style": row[8],
                        "best_for": row[9],
                        "difficulty": row[10],
                        "times_used": row[11],
                        "created_at": row[12].isoformat() if row[12] else None
                    })
                return templates
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM video_template_library
                    WHERE template_id = :template_id
                """), {"template_id": template_id})
                
                row = result.fetchone()
                if row:
                    return dict(row._mapping)
                return None
        except Exception as e:
            logger.error(f"Failed to get template: {e}")
            return None
    
    async def auto_populate_from_top_videos(
        self,
        min_engagement_rate: float = 0.05,
        limit: int = 10
    ) -> int:
        """
        Automatically create templates from top-performing analyzed videos.
        
        Args:
            min_engagement_rate: Minimum engagement rate threshold
            limit: Max templates to create
            
        Returns:
            Number of templates created
        """
        logger.info(f"Auto-populating templates from videos with >{min_engagement_rate:.0%} engagement")
        
        try:
            with self.engine.connect() as conn:
                # Find high-performing videos with analysis
                result = conn.execute(text("""
                    SELECT 
                        v.id,
                        v.pre_social_score,
                        v.transcript,
                        v.topics,
                        v.hooks,
                        v.tone,
                        v.pacing,
                        v.music_suggestion,
                        v.transcription_duration_sec,
                        v.beat_sheet,
                        v.visual_analysis,
                        v.pillar_tags,
                        v.format_tags,
                        v.content_type,
                        v.call_to_action
                    FROM video_analysis v
                    WHERE v.pre_social_score >= :min_score
                    AND v.beat_sheet IS NOT NULL
                    ORDER BY v.pre_social_score DESC
                    LIMIT :limit
                """), {
                    "min_score": min_engagement_rate * 100,
                    "limit": limit
                })
                
                created = 0
                for row in result:
                    analysis_data = {
                        "beat_sheet": row[9] or [],
                        "visual_analysis": row[10] or {},
                        "hooks": row[4] or [],
                        "tone": row[5] or "",
                        "pacing": row[6] or "",
                        "music_suggestion": row[7] or {},
                        "transcription_duration_sec": row[8] or 30,
                        "pillar_tags": row[11] or [],
                        "format_tags": row[12] or [],
                        "content_type": row[13] or "",
                        "call_to_action": row[14] or {}
                    }
                    
                    performance = {
                        "engagement_rate": (row[1] or 0) / 100,
                        "views": 0,
                        "completion_rate": 0
                    }
                    
                    template = await self.create_template_from_video(
                        video_id=str(row[0]),
                        analysis_data=analysis_data,
                        performance_metrics=performance
                    )
                    
                    await self.save_template(template)
                    created += 1
                    logger.info(f"Created template: {template.name}")
                
                return created
                
        except Exception as e:
            logger.error(f"Auto-populate failed: {e}")
            return 0
