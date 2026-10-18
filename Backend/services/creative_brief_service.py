"""
Creative Brief Service
Generates human-readable creative briefs and T2V prompts from AngleInsightSnapshots
Supports short-form (TikTok/Reels) and long-form (YouTube) content
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

from models.creative_brief_models import (
    AngleInsightSnapshot,
    VideoFormat,
    AspectRatio,
    SceneRole,
    CreativeBrief,
    BriefSection,
    ShotDescription,
    VideoPrompt,
    ProductPerformanceSnapshot,
    VideoAnalysisSnapshot,
    SceneAnalysis
)


class CreativeBriefService:
    """
    Generates creative briefs and video prompts from insight snapshots
    """
    
    # Format-specific templates
    FORMAT_CONFIGS = {
        VideoFormat.SHORT_FORM: {
            "duration_range": (15, 60),
            "default_duration": 30,
            "aspect_ratio": AspectRatio.VERTICAL,
            "style": "realistic_ugc",
            "platforms": ["TikTok", "Instagram Reels", "YouTube Shorts"]
        },
        VideoFormat.LONG_FORM: {
            "duration_range": (120, 900),
            "default_duration": 300,
            "aspect_ratio": AspectRatio.HORIZONTAL,
            "style": "professional",
            "platforms": ["YouTube", "Facebook"]
        },
        VideoFormat.AD_CREATIVE: {
            "duration_range": (15, 45),
            "default_duration": 30,
            "aspect_ratio": AspectRatio.VERTICAL,
            "style": "polished_ugc",
            "platforms": ["TikTok Ads", "Meta Ads"]
        },
        VideoFormat.UGC: {
            "duration_range": (15, 90),
            "default_duration": 45,
            "aspect_ratio": AspectRatio.VERTICAL,
            "style": "realistic_ugc",
            "platforms": ["TikTok", "Instagram"]
        }
    }
    
    # Niche-specific style guides
    NICHE_STYLES = {
        "skincare": {
            "color_palette": ["soft white", "pastel pink", "clean clinical"],
            "lighting": "soft natural or bathroom lighting",
            "setting": "bathroom, vanity, bedroom",
            "tone": "aspirational, self-care, transformation"
        },
        "fitness": {
            "color_palette": ["energetic", "high contrast", "sweat-glow"],
            "lighting": "gym lighting or outdoor golden hour",
            "setting": "gym, home workout, outdoors",
            "tone": "motivational, transformation, routine"
        },
        "tech": {
            "color_palette": ["clean whites", "dark mode", "neon accents"],
            "lighting": "studio or screen-lit",
            "setting": "desk setup, office, studio",
            "tone": "informative, review-style, comparison"
        },
        "food": {
            "color_palette": ["warm, appetizing", "rich colors"],
            "lighting": "natural daylight or warm kitchen",
            "setting": "kitchen, restaurant, table",
            "tone": "satisfying, ASMR-adjacent, recipe"
        },
        "fashion": {
            "color_palette": ["neutral, monochrome", "seasonal"],
            "lighting": "natural or studio",
            "setting": "mirror, closet, street",
            "tone": "trend-focused, GRWM, styling tips"
        },
        "default": {
            "color_palette": ["neutral", "brand-aligned"],
            "lighting": "natural",
            "setting": "contextual",
            "tone": "authentic"
        }
    }
    
    @classmethod
    def build_creative_brief(
        cls,
        snapshot: AngleInsightSnapshot,
        format_type: VideoFormat = VideoFormat.SHORT_FORM,
        target_duration: Optional[int] = None,
        niche: str = "default"
    ) -> CreativeBrief:
        """
        Generate a human-readable creative brief from an insight snapshot
        
        Args:
            snapshot: The AngleInsightSnapshot containing product + video data
            format_type: Target video format
            target_duration: Target duration in seconds (uses format default if not specified)
            niche: Content niche for style guidance
        """
        config = cls.FORMAT_CONFIGS.get(format_type, cls.FORMAT_CONFIGS[VideoFormat.SHORT_FORM])
        niche_style = cls.NICHE_STYLES.get(niche, cls.NICHE_STYLES["default"])
        
        if target_duration is None:
            target_duration = config["default_duration"]
        
        product = snapshot.product
        video = snapshot.video
        
        # Build brief sections
        brief = CreativeBrief(
            title=cls._generate_brief_title(video.extracted_angles, format_type),
            format=format_type,
            duration_target_sec=target_duration,
            aspect_ratio=config["aspect_ratio"],
            
            product_summary=cls._build_product_section(product),
            performance_rationale=cls._build_performance_section(product, video),
            target_audience=cls._build_audience_section(video.extracted_angles, niche),
            core_insight=cls._build_insight_section(video.extracted_angles),
            key_message=cls._build_key_message_section(video.extracted_angles),
            
            shots=cls._build_shots(video.scenes, format_type),
            
            look_and_feel=cls._build_style_section(niche_style, video),
            offer_and_cta=cls._build_cta_section(video.extracted_angles),
            
            generated_at=datetime.now().isoformat(),
            source_snapshot_id=video.video_id
        )
        
        # Add chapter outline for long-form
        if format_type == VideoFormat.LONG_FORM:
            brief.chapter_outline = cls._build_chapter_outline(video.scenes, target_duration)
        
        return brief
    
    @classmethod
    def build_video_prompt(
        cls,
        snapshot: AngleInsightSnapshot,
        output_format: str = "text",
        style: str = "realistic_ugc",
        include_safety: bool = True
    ) -> VideoPrompt:
        """
        Generate a text-to-video prompt from an insight snapshot
        
        Args:
            snapshot: The AngleInsightSnapshot
            output_format: "text" for single prompt, "json" for structured
            style: Visual style directive
            include_safety: Include safety/moderation flags
        """
        video = snapshot.video
        
        prompt = VideoPrompt(
            duration_seconds=int(video.duration_sec),
            aspect_ratio=video.aspect_ratio,
            style=style
        )
        
        # Build shots from scenes
        for scene in video.scenes:
            shot_prompt = cls._scene_to_prompt(scene, style)
            prompt.shots.append({
                "start": scene.start_sec,
                "end": scene.end_sec,
                "prompt": shot_prompt
            })
        
        # Build full prompt
        prompt.full_prompt = cls._build_full_prompt(
            video,
            snapshot.product,
            style,
            include_safety
        )
        
        return prompt
    
    @classmethod
    def _generate_brief_title(cls, angles: Any, format_type: VideoFormat) -> str:
        """Generate brief title from angles"""
        if angles.core_promise:
            base = angles.core_promise[:50]
        elif angles.hook_lines:
            base = angles.hook_lines[0][:50]
        else:
            base = "Creative Brief"
        
        format_labels = {
            VideoFormat.SHORT_FORM: "Short-Form",
            VideoFormat.LONG_FORM: "Long-Form Tutorial",
            VideoFormat.AD_CREATIVE: "Ad Creative",
            VideoFormat.UGC: "UGC"
        }
        
        return f"{base} ({format_labels.get(format_type, 'Video')})"
    
    @classmethod
    def _build_product_section(cls, product: ProductPerformanceSnapshot) -> BriefSection:
        """Build product summary section"""
        price_str = ""
        if product.price_range:
            if product.price_range.max_price:
                price_str = f"${product.price_range.min_price:.0f}-${product.price_range.max_price:.0f}"
            else:
                price_str = f"${product.price_range.min_price:.0f}"
        
        return BriefSection(
            title="Product",
            content=product.product_name,
            bullet_points=[
                f"Category: {product.category or 'N/A'}",
                f"Price: {price_str or 'N/A'}",
                f"Launch: {product.launch_date or 'N/A'}"
            ]
        )
    
    @classmethod
    def _build_performance_section(cls, product: ProductPerformanceSnapshot, video: VideoAnalysisSnapshot) -> BriefSection:
        """Build performance rationale section"""
        bullets = []
        
        if product.metrics_30d:
            m = product.metrics_30d
            if m.revenue_usd:
                bullets.append(f"${m.revenue_usd/1000000:.2f}M revenue in last 30 days")
            if m.items_sold:
                bullets.append(f"{m.items_sold:,} units sold")
            if m.revenue_growth_rate_pct:
                bullets.append(f"{m.revenue_growth_rate_pct:.0f}% revenue growth")
        
        if product.affiliate:
            a = product.affiliate
            if a.creator_count:
                bullets.append(f"{a.creator_count:,} active creators")
            if a.creator_conversion_ratio_pct:
                bullets.append(f"{a.creator_conversion_ratio_pct:.0f}% creator conversion ratio")
        
        if video.performance.revenue_contribution_usd:
            bullets.append(f"Top video contributed ~${video.performance.revenue_contribution_usd/1000:.0f}K revenue")
        
        return BriefSection(
            title="Why This Product? (Performance Rationale)",
            content="We're not guessing with this creative: we're rebuilding a **proven angle**.",
            bullet_points=bullets
        )
    
    @classmethod
    def _build_audience_section(cls, angles: Any, niche: str) -> BriefSection:
        """Build target audience section"""
        pain_points = angles.primary_pain_points or ["common problems in this category"]
        drivers = angles.emotional_drivers or ["core motivations"]
        
        return BriefSection(
            title="Target Audience",
            content=f"People who experience: {', '.join(pain_points)}",
            bullet_points=[
                f"Pain points: {', '.join(pain_points)}",
                f"Motivated by: {', '.join(drivers)}",
                f"Niche: {niche.title()}"
            ]
        )
    
    @classmethod
    def _build_insight_section(cls, angles: Any) -> BriefSection:
        """Build core insight section"""
        return BriefSection(
            title="Core Insight",
            content=angles.core_promise or "Key transformation or benefit",
            bullet_points=angles.angle_types or []
        )
    
    @classmethod
    def _build_key_message_section(cls, angles: Any) -> BriefSection:
        """Build key message section"""
        hook = angles.hook_lines[0] if angles.hook_lines else "Main hook line"
        return BriefSection(
            title="Key Message",
            content=f'"{hook}"',
            bullet_points=[]
        )
    
    @classmethod
    def _build_shots(cls, scenes: List[SceneAnalysis], format_type: VideoFormat) -> List[ShotDescription]:
        """Build shot descriptions from scenes"""
        shots = []
        
        for i, scene in enumerate(scenes):
            shot = ShotDescription(
                shot_number=i + 1,
                start_sec=scene.start_sec,
                end_sec=scene.end_sec,
                camera_direction=f"{scene.frame_tags.shot_type} shot, {scene.frame_tags.camera_type}",
                action=scene.semantics.mini_summary,
                voiceover="",  # Would be extracted from transcript
                on_screen_text=scene.frame_tags.on_screen_text or "",
                reference_notes=f"Setting: {scene.frame_tags.setting}, Emotion: {scene.semantics.emotion}"
            )
            shots.append(shot)
        
        return shots
    
    @classmethod
    def _build_style_section(cls, niche_style: Dict, video: VideoAnalysisSnapshot) -> BriefSection:
        """Build look and feel section"""
        return BriefSection(
            title="Look & Feel",
            content=f"Style: {niche_style['tone']}",
            bullet_points=[
                f"Lighting: {niche_style['lighting']}",
                f"Setting: {niche_style['setting']}",
                f"Color palette: {', '.join(niche_style['color_palette'])}"
            ]
        )
    
    @classmethod
    def _build_cta_section(cls, angles: Any) -> BriefSection:
        """Build CTA section"""
        return BriefSection(
            title="Offer & CTA",
            content=angles.cta_style or "Clear call to action",
            bullet_points=[
                "Tie into current offer/promotion",
                "Keep CTA visible and actionable"
            ]
        )
    
    @classmethod
    def _build_chapter_outline(cls, scenes: List[SceneAnalysis], duration: int) -> List[Dict]:
        """Build chapter outline for long-form content"""
        chapters = []
        current_chapter = None
        
        for scene in scenes:
            if scene.chapter_title:
                if current_chapter:
                    chapters.append(current_chapter)
                current_chapter = {
                    "title": scene.chapter_title,
                    "start": scene.start_sec,
                    "scenes": []
                }
            
            if current_chapter:
                current_chapter["scenes"].append({
                    "role": scene.role.value,
                    "summary": scene.semantics.mini_summary
                })
        
        if current_chapter:
            chapters.append(current_chapter)
        
        return chapters
    
    @classmethod
    def _scene_to_prompt(cls, scene: SceneAnalysis, style: str) -> str:
        """Convert a scene to a T2V prompt segment"""
        parts = []
        
        # Setting and camera
        if scene.frame_tags.setting:
            parts.append(scene.frame_tags.setting)
        
        if scene.frame_tags.camera_type:
            parts.append(f"{scene.frame_tags.camera_type}")
        
        if scene.frame_tags.shot_type:
            parts.append(f"{scene.frame_tags.shot_type} shot")
        
        # Objects
        if scene.frame_tags.main_objects:
            parts.append(f"showing {', '.join(scene.frame_tags.main_objects)}")
        
        # Action
        if scene.semantics.mini_summary:
            parts.append(scene.semantics.mini_summary)
        
        # On-screen text
        if scene.frame_tags.on_screen_text:
            parts.append(f'On-screen text: "{scene.frame_tags.on_screen_text}"')
        
        # Style
        parts.append(f"{style} style, vertical 9:16 video")
        
        return ". ".join(parts)
    
    @classmethod
    def _build_full_prompt(
        cls,
        video: VideoAnalysisSnapshot,
        product: ProductPerformanceSnapshot,
        style: str,
        include_safety: bool
    ) -> str:
        """Build a complete single-prompt for T2V"""
        lines = [
            f"Create a {int(video.duration_sec)}-second vertical {video.aspect_ratio} video.",
            f"Style: {style}, realistic smartphone footage, natural lighting.",
            ""
        ]
        
        # Add core concept
        if video.extracted_angles.core_promise:
            lines.append(f"Theme: {video.extracted_angles.core_promise}")
            lines.append("")
        
        # Add scenes
        for i, scene in enumerate(video.scenes):
            scene_prompt = cls._scene_to_prompt(scene, style)
            lines.append(f"Scene {i+1} ({scene.start_sec:.0f}-{scene.end_sec:.0f}s):")
            lines.append(f"- {scene_prompt}")
            lines.append("")
        
        # Safety
        if include_safety:
            lines.append("Important: No logos, brand names, celebrities, or watermarks.")
        
        return "\n".join(lines)
    
    @classmethod
    def brief_to_markdown(cls, brief: CreativeBrief) -> str:
        """Convert CreativeBrief to markdown format"""
        lines = [
            f"# Creative Brief – {brief.title}",
            "",
            f"**Format:** {brief.format.value.replace('_', ' ').title()}",
            f"**Duration:** {brief.duration_target_sec}s",
            f"**Aspect Ratio:** {brief.aspect_ratio.value}",
            "",
            "---",
            ""
        ]
        
        # Sections
        for section_name in ["product_summary", "performance_rationale", "target_audience", 
                           "core_insight", "key_message", "look_and_feel", "offer_and_cta"]:
            section = getattr(brief, section_name)
            if section.title:
                lines.append(f"### {section.title}")
                if section.content:
                    lines.append(section.content)
                for bullet in section.bullet_points:
                    lines.append(f"- {bullet}")
                lines.append("")
        
        # Shots
        if brief.shots:
            lines.append("### Shot Treatment")
            lines.append("")
            for shot in brief.shots:
                lines.append(f"**Scene {shot.shot_number}** ({shot.start_sec:.0f}–{shot.end_sec:.0f}s)")
                lines.append(f"- Camera: {shot.camera_direction}")
                lines.append(f"- Action: {shot.action}")
                if shot.on_screen_text:
                    lines.append(f"- Text: `{shot.on_screen_text}`")
                lines.append("")
        
        lines.append("---")
        lines.append(f"*Generated: {brief.generated_at}*")
        
        return "\n".join(lines)
