"""
AI Reply Suggestions Service
=============================
Generate AI-powered reply suggestions for comments, DMs, and mentions.

This service integrates with the Community Inbox to provide intelligent,
context-aware reply suggestions using the existing FATE framework and
brand voice guidelines.

Implements INBOX-004: AI Reply Suggestions
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from loguru import logger
from enum import Enum
import json

from services.ai_client import AIClient
from config.model_registry import ModelConfig, ModelRegistry, TaskType


class MessageType(Enum):
    """Types of messages that can receive replies"""
    COMMENT = "comment"
    DM = "dm"
    MENTION = "mention"
    STORY_REPLY = "story_reply"
    REVIEW = "review"


class SentimentType(Enum):
    """Message sentiment classification"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    QUESTION = "question"


class ReplySuggestion:
    """A single reply suggestion with metadata"""

    def __init__(
        self,
        text: str,
        tone: str,
        confidence: float,
        reasoning: str,
        includes_link: bool = False,
        requires_permission: bool = False
    ):
        self.text = text
        self.tone = tone
        self.confidence = confidence
        self.reasoning = reasoning
        self.includes_link = includes_link
        self.requires_permission = requires_permission

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "text": self.text,
            "tone": self.tone,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "includes_link": self.includes_link,
            "requires_permission": self.requires_permission
        }


class ReplySuggestionsService:
    """
    AI Reply Suggestions Service

    Generates intelligent reply suggestions for social media messages
    using GPT-4o and brand voice guidelines.

    Features:
    - Context-aware suggestions (3 options with different tones)
    - Sentiment analysis
    - DM permission awareness
    - Brand voice consistency
    - Link detection and warnings

    Usage:
        service = ReplySuggestionsService.get_instance()
        suggestions = await service.generate_suggestions(
            message="Love this video!",
            message_type=MessageType.COMMENT,
            platform="instagram",
            context={"post_title": "5 Tips for Productivity"}
        )
    """

    _instance: Optional["ReplySuggestionsService"] = None

    def __init__(self):
        """Initialize the reply suggestions service"""
        if ReplySuggestionsService._instance is not None:
            raise RuntimeError("Use ReplySuggestionsService.get_instance()")

        # Get AI model configuration for comment generation (replies are similar to comments)
        self.ai_config = ModelRegistry.get_model_config(TaskType.COMMENT_GENERATION)
        self.ai_client = AIClient(self.ai_config)

        # Default brand voice guidelines (can be customized per brand)
        self.brand_voice = {
            "tone": "friendly, helpful, authentic",
            "style": "conversational but professional",
            "values": "transparency, creativity, empowerment",
            "avoid": "corporate jargon, excessive emojis, overly promotional"
        }

        logger.info("💬 Reply Suggestions Service initialized")

    @classmethod
    def get_instance(cls) -> "ReplySuggestionsService":
        """Get or create singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def generate_suggestions(
        self,
        message: str,
        message_type: MessageType,
        platform: str,
        context: Optional[Dict[str, Any]] = None,
        brand_id: Optional[str] = None,
        num_suggestions: int = 3
    ) -> List[ReplySuggestion]:
        """
        Generate AI reply suggestions for a message.

        Args:
            message: The incoming message text
            message_type: Type of message (comment, DM, etc.)
            platform: Social platform (instagram, tiktok, twitter, youtube, threads)
            context: Additional context (original post, user profile, conversation history)
            brand_id: Optional brand ID for custom voice guidelines
            num_suggestions: Number of suggestions to generate (default 3)

        Returns:
            List of ReplySuggestion objects ranked by appropriateness
        """
        logger.info(f"Generating {num_suggestions} reply suggestions for {message_type.value} on {platform}")

        # Classify message sentiment
        sentiment = await self._classify_sentiment(message)

        # Build context for AI
        context_str = self._build_context_string(context)

        # Generate suggestions using AI
        suggestions = await self._generate_with_ai(
            message=message,
            message_type=message_type,
            platform=platform,
            sentiment=sentiment,
            context_str=context_str,
            num_suggestions=num_suggestions
        )

        # Post-process suggestions
        processed_suggestions = []
        for suggestion_data in suggestions:
            # Detect links
            includes_link = self._contains_link(suggestion_data["text"])

            # Check if DM permission required
            requires_permission = (
                message_type == MessageType.DM and includes_link
            )

            suggestion = ReplySuggestion(
                text=suggestion_data["text"],
                tone=suggestion_data["tone"],
                confidence=suggestion_data.get("confidence", 0.8),
                reasoning=suggestion_data.get("reasoning", ""),
                includes_link=includes_link,
                requires_permission=requires_permission
            )

            processed_suggestions.append(suggestion)

        # Rank by confidence
        processed_suggestions.sort(key=lambda x: x.confidence, reverse=True)

        logger.success(f"Generated {len(processed_suggestions)} reply suggestions")
        return processed_suggestions

    async def _classify_sentiment(self, message: str) -> SentimentType:
        """
        Classify message sentiment.

        Args:
            message: Message text

        Returns:
            SentimentType enum
        """
        # Simple keyword-based classification (can be enhanced with AI)
        message_lower = message.lower()

        # Question detection
        if "?" in message or any(q in message_lower for q in ["how", "what", "when", "where", "why", "can you", "do you"]):
            return SentimentType.QUESTION

        # Positive indicators
        positive_words = ["love", "great", "awesome", "amazing", "thanks", "thank", "best", "excellent", "fantastic"]
        if any(word in message_lower for word in positive_words):
            return SentimentType.POSITIVE

        # Negative indicators
        negative_words = ["hate", "bad", "terrible", "worst", "disappointed", "spam", "scam", "fake"]
        if any(word in message_lower for word in negative_words):
            return SentimentType.NEGATIVE

        return SentimentType.NEUTRAL

    def _build_context_string(self, context: Optional[Dict[str, Any]]) -> str:
        """Build context string for AI prompt"""
        if not context:
            return "No additional context provided."

        context_parts = []

        if "post_title" in context:
            context_parts.append(f"Original post: {context['post_title']}")

        if "post_description" in context:
            context_parts.append(f"Post description: {context['post_description']}")

        if "user_name" in context:
            context_parts.append(f"User: {context['user_name']}")

        if "conversation_history" in context:
            context_parts.append(f"Previous messages: {context['conversation_history']}")

        return " | ".join(context_parts) if context_parts else "No additional context."

    async def _generate_with_ai(
        self,
        message: str,
        message_type: MessageType,
        platform: str,
        sentiment: SentimentType,
        context_str: str,
        num_suggestions: int
    ) -> List[Dict[str, Any]]:
        """
        Generate reply suggestions using AI.

        Args:
            message: Incoming message
            message_type: Type of message
            platform: Social platform
            sentiment: Message sentiment
            context_str: Context string
            num_suggestions: Number of suggestions

        Returns:
            List of suggestion dictionaries
        """
        # Build AI prompt
        prompt = self._build_ai_prompt(
            message=message,
            message_type=message_type,
            platform=platform,
            sentiment=sentiment,
            context_str=context_str,
            num_suggestions=num_suggestions
        )

        # Call AI
        try:
            response = self.ai_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,  # Moderate creativity
                max_tokens=1000
            )

            # Parse JSON response
            suggestions = json.loads(response)

            # Validate response structure
            if not isinstance(suggestions, list):
                logger.warning("AI response is not a list, wrapping in list")
                suggestions = [suggestions]

            return suggestions

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
            # Return fallback suggestion
            return [{
                "text": "Thanks for reaching out! I'll get back to you soon.",
                "tone": "neutral",
                "confidence": 0.5,
                "reasoning": "Fallback response due to AI parsing error"
            }]

        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return [{
                "text": "Thank you for your message!",
                "tone": "neutral",
                "confidence": 0.3,
                "reasoning": "Fallback response due to AI error"
            }]

    def _get_system_prompt(self) -> str:
        """Get system prompt for AI"""
        return f"""You are an expert social media manager helping generate reply suggestions.

Your brand voice:
- Tone: {self.brand_voice['tone']}
- Style: {self.brand_voice['style']}
- Values: {self.brand_voice['values']}
- Avoid: {self.brand_voice['avoid']}

Guidelines:
1. Always be authentic and helpful
2. Match the energy of the incoming message
3. Keep replies concise (under 280 characters for comments)
4. For questions, provide direct answers
5. For compliments, show genuine appreciation
6. For complaints, show empathy and offer solutions
7. Never include links in first DM unless asked
8. Use emojis sparingly and naturally

Output format: JSON array of suggestion objects with:
- text: The suggested reply
- tone: The tone used (friendly/professional/empathetic/enthusiastic)
- confidence: Your confidence in this suggestion (0.0-1.0)
- reasoning: Brief explanation of why this reply is appropriate"""

    def _build_ai_prompt(
        self,
        message: str,
        message_type: MessageType,
        platform: str,
        sentiment: SentimentType,
        context_str: str,
        num_suggestions: int
    ) -> str:
        """Build user prompt for AI"""
        return f"""Generate {num_suggestions} reply suggestions for this social media message.

Platform: {platform}
Message type: {message_type.value}
Sentiment: {sentiment.value}
Context: {context_str}

Incoming message:
"{message}"

Provide {num_suggestions} different reply options with varying tones (friendly, professional, empathetic, etc.).
Return as JSON array."""

    def _contains_link(self, text: str) -> bool:
        """Check if text contains a link"""
        link_indicators = [
            "http://",
            "https://",
            "www.",
            ".com",
            ".net",
            ".org",
            "bit.ly",
            "link in bio"
        ]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in link_indicators)

    def update_brand_voice(
        self,
        brand_id: str,
        tone: Optional[str] = None,
        style: Optional[str] = None,
        values: Optional[str] = None,
        avoid: Optional[str] = None
    ):
        """
        Update brand voice guidelines.

        Args:
            brand_id: Brand identifier
            tone: Brand tone description
            style: Communication style
            values: Brand values
            avoid: Things to avoid
        """
        if tone:
            self.brand_voice["tone"] = tone
        if style:
            self.brand_voice["style"] = style
        if values:
            self.brand_voice["values"] = values
        if avoid:
            self.brand_voice["avoid"] = avoid

        logger.info(f"Updated brand voice for brand {brand_id}")

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "service": "reply_suggestions",
            "status": "operational",
            "ai_model": self.ai_config.model,
            "ai_provider": self.ai_config.provider,
            "brand_voice": self.brand_voice,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Convenience function for quick access
def get_reply_suggestions_service() -> ReplySuggestionsService:
    """Get the reply suggestions service instance"""
    return ReplySuggestionsService.get_instance()
