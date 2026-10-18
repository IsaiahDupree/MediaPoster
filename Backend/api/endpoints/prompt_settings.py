"""
Prompt Generation Settings API

Manages user preferences for AI content generation including:
- Voice/tone settings
- Style preferences
- Platform-specific limits
- Custom instructions
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from loguru import logger

from database.connection import get_db
from services.event_bus import EventBus, Topics
from config.platform_limits import (
    get_platform_limits,
    get_all_platforms,
    PLATFORM_LIMITS,
    DEFAULT_PROMPT_SETTINGS,
    PROMPT_TEMPLATES,
    TONE_MODIFIERS,
    STYLE_MODIFIERS,
    CTA_TEMPLATES,
)

router = APIRouter(prefix="/prompt-settings", tags=["Prompt Settings"])


class PromptSettingsUpdate(BaseModel):
    """Request to update prompt generation settings"""
    voice: Optional[str] = None  # conversational, professional, casual, humorous, inspirational
    tone: Optional[str] = None  # engaging, informative, persuasive, friendly, authoritative
    style: Optional[str] = None  # concise, detailed, storytelling, listicle, question-based
    emoji_usage: Optional[str] = None  # none, minimal, moderate, heavy
    hashtag_style: Optional[str] = None  # relevant, trending, branded, mixed
    cta_style: Optional[str] = None  # none, soft, direct, urgency
    language: Optional[str] = None
    custom_instructions: Optional[str] = None


class PlatformLimitResponse(BaseModel):
    """Platform limit information"""
    platform: str
    title_max: int
    title_target: int
    description_max: int
    description_target: int
    hashtags_max: int
    hashtags_recommended: int


@router.get("/")
async def get_prompt_settings():
    """Get current prompt generation settings"""
    # In a full implementation, this would load from database per user
    # For now, return defaults with documentation
    return {
        "settings": DEFAULT_PROMPT_SETTINGS,
        "options": {
            "voice": list(PROMPT_TEMPLATES.keys()),
            "tone": list(TONE_MODIFIERS.keys()),
            "style": list(STYLE_MODIFIERS.keys()),
            "emoji_usage": ["none", "minimal", "moderate", "heavy"],
            "hashtag_style": ["relevant", "trending", "branded", "mixed"],
            "cta_style": list(CTA_TEMPLATES.keys()),
        },
        "descriptions": {
            "voice": PROMPT_TEMPLATES,
            "tone": TONE_MODIFIERS,
            "style": STYLE_MODIFIERS,
            "cta": CTA_TEMPLATES,
        }
    }


@router.put("/")
async def update_prompt_settings(request: PromptSettingsUpdate):
    """Update prompt generation settings"""
    # In a full implementation, this would save to database per user
    updated_settings = DEFAULT_PROMPT_SETTINGS.copy()
    
    if request.voice:
        updated_settings["voice"] = request.voice
    if request.tone:
        updated_settings["tone"] = request.tone
    if request.style:
        updated_settings["style"] = request.style
    if request.emoji_usage:
        updated_settings["emoji_usage"] = request.emoji_usage
    if request.hashtag_style:
        updated_settings["hashtag_style"] = request.hashtag_style
    if request.cta_style:
        updated_settings["cta_style"] = request.cta_style
    if request.language:
        updated_settings["language"] = request.language
    if request.custom_instructions is not None:
        updated_settings["custom_instructions"] = request.custom_instructions
    
    logger.info(f"[PromptSettings] Updated settings: {updated_settings}")
    
    return {
        "success": True,
        "settings": updated_settings
    }


@router.get("/platform-limits")
async def get_all_platform_limits():
    """Get character limits for all supported platforms"""
    platforms = get_all_platforms()
    
    result = {}
    for name, limits in platforms.items():
        result[name] = {
            "platform": limits.platform,
            "title": {
                "max": limits.title_max,
                "target": limits.title_target,
                "buffer_percent": 20,
            },
            "description": {
                "max": limits.description_max,
                "target": limits.description_target,
                "buffer_percent": 20,
            },
            "hashtags": {
                "max": limits.hashtags_max,
                "recommended": limits.hashtags_recommended,
            },
        }
    
    return {
        "platforms": result,
        "note": "Target values are 80% of max (20% safety buffer)"
    }


@router.get("/platform-limits/{platform}")
async def get_platform_limit(platform: str):
    """Get character limits for a specific platform"""
    limits = get_platform_limits(platform)
    
    return {
        "platform": limits.platform,
        "title": {
            "max": limits.title_max,
            "target": limits.title_target,
            "buffer_percent": 20,
        },
        "description": {
            "max": limits.description_max,
            "target": limits.description_target,
            "buffer_percent": 20,
        },
        "hashtags": {
            "max": limits.hashtags_max,
            "recommended": limits.hashtags_recommended,
        },
        "bio_max": limits.bio_max,
        "comment_max": limits.comment_max,
    }


@router.post("/generate-preview")
async def generate_preview(
    text: str,
    platform: str = "instagram",
    voice: str = "conversational",
    tone: str = "engaging",
    style: str = "concise",
):
    """Preview how text would be generated with current settings"""
    limits = get_platform_limits(platform)
    
    # Apply truncation
    if len(text) > limits.description_target:
        truncated = text[:limits.description_target - 3].rsplit(' ', 1)[0] + "..."
    else:
        truncated = text
    
    return {
        "original": text,
        "original_length": len(text),
        "truncated": truncated,
        "truncated_length": len(truncated),
        "platform": platform,
        "limit": limits.description_target,
        "within_limit": len(truncated) <= limits.description_target,
        "settings_applied": {
            "voice": voice,
            "tone": tone,
            "style": style,
        }
    }
