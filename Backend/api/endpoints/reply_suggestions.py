"""
Reply Suggestions API Endpoints
================================
API for generating AI-powered reply suggestions for community inbox messages.

Implements INBOX-004: AI Reply Suggestions
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

from services.reply_suggestions import (
    ReplySuggestionsService,
    MessageType,
    ReplySuggestion
)


router = APIRouter(prefix="/api/inbox/suggestions", tags=["Community Inbox"])


# Request/Response Models
class GenerateSuggestionsRequest(BaseModel):
    """Request to generate reply suggestions"""
    message: str = Field(..., description="The incoming message text")
    message_type: str = Field(..., description="Type of message: comment, dm, mention, story_reply, review")
    platform: str = Field(..., description="Social platform: instagram, tiktok, twitter, youtube, threads")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context (post title, user name, etc.)")
    brand_id: Optional[str] = Field(None, description="Brand ID for custom voice guidelines")
    num_suggestions: int = Field(3, ge=1, le=5, description="Number of suggestions (1-5)")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "This is exactly what I needed! When will the next video drop?",
                "message_type": "comment",
                "platform": "instagram",
                "context": {
                    "post_title": "5 Productivity Tips for Creators",
                    "user_name": "@productivityguru"
                },
                "num_suggestions": 3
            }
        }


class SuggestionResponse(BaseModel):
    """A single reply suggestion"""
    text: str
    tone: str
    confidence: float
    reasoning: str
    includes_link: bool
    requires_permission: bool


class GenerateSuggestionsResponse(BaseModel):
    """Response with generated suggestions"""
    suggestions: List[SuggestionResponse]
    message_type: str
    platform: str
    sentiment: str
    generated_at: str


class UpdateBrandVoiceRequest(BaseModel):
    """Request to update brand voice guidelines"""
    tone: Optional[str] = Field(None, description="Brand tone (e.g., 'friendly, helpful, authentic')")
    style: Optional[str] = Field(None, description="Communication style")
    values: Optional[str] = Field(None, description="Brand values")
    avoid: Optional[str] = Field(None, description="Things to avoid")

    class Config:
        json_schema_extra = {
            "example": {
                "tone": "friendly, empowering, creative",
                "style": "conversational and inspiring",
                "values": "authenticity, growth, community",
                "avoid": "corporate speak, excessive jargon"
            }
        }


# Endpoints
@router.post("/generate", response_model=GenerateSuggestionsResponse)
async def generate_reply_suggestions(request: GenerateSuggestionsRequest):
    """
    Generate AI-powered reply suggestions for a message.

    This endpoint analyzes an incoming message and generates contextual
    reply suggestions using GPT-4o. Each suggestion includes:
    - The suggested reply text
    - The tone used (friendly, professional, empathetic, etc.)
    - Confidence score (0.0-1.0)
    - Reasoning for why this reply is appropriate
    - Link detection and permission warnings

    **Example use cases:**
    - Comment replies: Generate friendly responses to Instagram/TikTok comments
    - DM responses: Create personalized DM replies with permission awareness
    - Question handling: Provide helpful answers to common questions
    - Complaint management: Generate empathetic responses to negative feedback

    **Flow:**
    1. Classify message sentiment (positive, negative, neutral, question)
    2. Build context from original post, user info, conversation history
    3. Generate 3 reply options with different tones
    4. Rank by appropriateness and confidence
    5. Flag replies requiring DM consent (if they contain links)
    """
    try:
        # Validate message type
        try:
            msg_type = MessageType(request.message_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid message_type. Must be one of: {[t.value for t in MessageType]}"
            )

        # Get service instance
        service = ReplySuggestionsService.get_instance()

        # Generate suggestions
        suggestions = await service.generate_suggestions(
            message=request.message,
            message_type=msg_type,
            platform=request.platform,
            context=request.context,
            brand_id=request.brand_id,
            num_suggestions=request.num_suggestions
        )

        # Classify sentiment for response
        sentiment = await service._classify_sentiment(request.message)

        # Convert to response model
        suggestion_responses = [
            SuggestionResponse(
                text=s.text,
                tone=s.tone,
                confidence=s.confidence,
                reasoning=s.reasoning,
                includes_link=s.includes_link,
                requires_permission=s.requires_permission
            )
            for s in suggestions
        ]

        return GenerateSuggestionsResponse(
            suggestions=suggestion_responses,
            message_type=request.message_type,
            platform=request.platform,
            sentiment=sentiment.value,
            generated_at=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to generate reply suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate suggestions: {str(e)}"
        )


@router.post("/brand-voice/{brand_id}")
async def update_brand_voice(brand_id: str, request: UpdateBrandVoiceRequest):
    """
    Update brand voice guidelines for reply generation.

    Brand voice settings control how the AI generates replies:
    - **Tone**: The emotional character (friendly, professional, casual)
    - **Style**: Communication patterns (conversational, formal, witty)
    - **Values**: Core brand values to reflect in replies
    - **Avoid**: Things to never include (jargon, slang, etc.)

    **Example:**
    ```json
    {
      "tone": "friendly, empowering, creative",
      "style": "conversational and inspiring",
      "values": "authenticity, growth, community",
      "avoid": "corporate speak, excessive jargon, pushy sales language"
    }
    ```

    These guidelines are used in the AI prompt to ensure brand consistency
    across all generated replies.
    """
    try:
        service = ReplySuggestionsService.get_instance()

        service.update_brand_voice(
            brand_id=brand_id,
            tone=request.tone,
            style=request.style,
            values=request.values,
            avoid=request.avoid
        )

        return {
            "success": True,
            "brand_id": brand_id,
            "message": "Brand voice updated successfully",
            "updated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to update brand voice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update brand voice: {str(e)}"
        )


@router.get("/status")
async def get_service_status():
    """
    Get reply suggestions service status.

    Returns current service configuration including:
    - AI model being used
    - AI provider (OpenAI, Groq, Google)
    - Current brand voice settings
    - Service health status
    """
    try:
        service = ReplySuggestionsService.get_instance()
        return service.get_status()

    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for reply suggestions service.

    Returns a simple health status to verify the service is running.
    """
    return {
        "service": "reply_suggestions",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
