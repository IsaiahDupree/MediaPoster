"""
RF-006: Fit Signal Detection
Detects when to offer specific products/services based on conversation patterns.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# =============================================================================
# FIT SIGNAL DEFINITIONS
# =============================================================================

FIT_SIGNALS = {
    "relationship_crm": {
        "name": "Relationship CRM / Personal CRM",
        "signals": [
            "i keep forgetting to follow up",
            "my network is messy",
            "i lost track of mentors/clients",
            "i hate feeling like i'm spamming people",
            "i don't know who to reach out to",
            "my contacts are all over the place",
            "i need to be better at staying in touch"
        ],
        "offer_line": "i built a relationship OS for this—want a quick look when it's ready?"
    },
    "content_analytics": {
        "name": "Content Analytics / Performance Tracking",
        "signals": [
            "my posts aren't converting",
            "i don't know what content is working",
            "i need a repeatable system",
            "i can't tell what's performing",
            "my engagement is inconsistent",
            "i'm posting blindly"
        ],
        "offer_line": "want me to show you a simple way to track what's actually moving the needle?"
    },
    "keyword_research": {
        "name": "Keyword Research / Topic Discovery",
        "signals": [
            "i don't know what to post",
            "i need better topics/hooks",
            "seo feels random",
            "i'm stuck on content ideas",
            "what should i write about",
            "i need trending topics"
        ],
        "offer_line": "want a list of topics/hooks tailored to your niche that you can post this week?"
    },
    "automation_services": {
        "name": "Automation / Systems Building",
        "signals": [
            "this is taking me forever",
            "i'm drowning in manual work",
            "i need a system",
            "i'm doing everything myself",
            "i wish this was automated",
            "i spend too much time on repetitive tasks"
        ],
        "offer_line": "if you want, i can either (a) give you a quick blueprint, or (b) build the automation with you."
    },
    "video_editing": {
        "name": "Video Editing / Content Creation",
        "signals": [
            "editing takes forever",
            "i need help with video",
            "my videos don't look professional",
            "i can't keep up with content",
            "video production is killing me"
        ],
        "offer_line": "i've got a streamlined video workflow—want me to show you how it works?"
    },
    "social_media_management": {
        "name": "Social Media Management",
        "signals": [
            "i can't keep up with all the platforms",
            "posting everywhere is exhausting",
            "i need to be more consistent",
            "scheduling is a nightmare",
            "i'm always behind on content"
        ],
        "offer_line": "want me to show you a way to post everywhere without the headache?"
    }
}


@dataclass
class FitSignalMatch:
    """Detected fit signal match."""
    offer_type: str
    offer_name: str
    matched_signals: List[str]
    confidence: float  # 0-1
    offer_line: str
    context: str
    detected_at: datetime


class FitSignalDetector:
    """
    Detects fit signals in conversations to identify offer opportunities.
    
    Golden Trigger Rules:
    - Same pain shows up 2-3 times
    - They've accepted help before
    - They ask "what would you do?"
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key and OpenAI else None
        self.fit_signals = FIT_SIGNALS
        logger.info("✅ FitSignalDetector initialized")
    
    def detect_signals_simple(
        self,
        messages: List[str],
        contact_context: Dict
    ) -> List[FitSignalMatch]:
        """
        Simple keyword-based signal detection.
        Fast but less accurate than AI-based detection.
        """
        matches = []
        text = " ".join(messages).lower()
        
        for offer_type, config in self.fit_signals.items():
            matched_signals = []
            for signal in config["signals"]:
                if signal.lower() in text:
                    matched_signals.append(signal)
            
            if matched_signals:
                confidence = min(len(matched_signals) / 3.0, 1.0)  # Cap at 1.0
                matches.append(FitSignalMatch(
                    offer_type=offer_type,
                    offer_name=config["name"],
                    matched_signals=matched_signals,
                    confidence=confidence,
                    offer_line=config["offer_line"],
                    context=f"Found {len(matched_signals)} matching signals",
                    detected_at=datetime.now(timezone.utc)
                ))
        
        return sorted(matches, key=lambda x: x.confidence, reverse=True)
    
    async def detect_signals_ai(
        self,
        messages: List[str],
        contact_context: Dict
    ) -> List[FitSignalMatch]:
        """
        AI-powered fit signal detection.
        More accurate, understands context and nuance.
        """
        if not self.client:
            logger.warning("OpenAI client not available, falling back to simple detection")
            return self.detect_signals_simple(messages, contact_context)
        
        try:
            # Build the conversation context
            conversation = "\n".join([f"- {msg}" for msg in messages[-20:]])  # Last 20 messages
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are analyzing a conversation to detect "fit signals" - indicators that someone might benefit from a specific product or service.

Available offers and their fit signals:
{json.dumps(self.fit_signals, indent=2)}

Contact context:
- What they're building: {contact_context.get('building', 'unknown')}
- Their struggles: {contact_context.get('struggles', 'unknown')}
- Their values: {contact_context.get('values', 'unknown')}

Analyze the conversation and identify ANY fit signals. Look for:
1. Explicit mentions of problems we can solve
2. Implicit frustrations or pain points
3. Questions that suggest a need
4. Repeated themes (same pain mentioned multiple times = stronger signal)

Return JSON array of matches:
[
  {{
    "offer_type": "key from fit signals",
    "matched_signals": ["specific signals detected"],
    "confidence": 0.0-1.0,
    "reasoning": "why this is a fit"
  }}
]

Return empty array if no fits detected. Be conservative - only flag clear matches."""
                    },
                    {
                        "role": "user",
                        "content": f"Conversation messages:\n{conversation}"
                    }
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            matches_data = result.get("matches", result) if isinstance(result, dict) else result
            
            if not isinstance(matches_data, list):
                matches_data = [matches_data] if matches_data else []
            
            matches = []
            for m in matches_data:
                if m.get("offer_type") in self.fit_signals:
                    config = self.fit_signals[m["offer_type"]]
                    matches.append(FitSignalMatch(
                        offer_type=m["offer_type"],
                        offer_name=config["name"],
                        matched_signals=m.get("matched_signals", []),
                        confidence=m.get("confidence", 0.5),
                        offer_line=config["offer_line"],
                        context=m.get("reasoning", ""),
                        detected_at=datetime.now(timezone.utc)
                    ))
            
            return sorted(matches, key=lambda x: x.confidence, reverse=True)
            
        except Exception as e:
            logger.error(f"AI fit signal detection failed: {e}")
            return self.detect_signals_simple(messages, contact_context)
    
    def check_golden_trigger(
        self,
        contact: Dict,
        fit_matches: List[FitSignalMatch]
    ) -> Tuple[bool, Optional[FitSignalMatch]]:
        """
        Check if the "Golden Trigger" conditions are met for making an offer.
        
        Golden Trigger = ready to offer when:
        1. Same pain shows up 2-3 times (high confidence fit match)
        2. They've accepted help before (value_delivered_count > 0)
        3. They ask "what would you do?" (trust signal)
        """
        if not fit_matches:
            return False, None
        
        best_match = fit_matches[0]
        
        # Check conditions
        scores = contact.get("scores", {})
        trust_signals = scores.get("trust_signals", [])
        value_delivered = scores.get("value_delivered_count", 0)
        
        # Condition 1: High confidence fit (pain repeated)
        repeated_pain = best_match.confidence >= 0.7 or len(best_match.matched_signals) >= 2
        
        # Condition 2: They've accepted help before
        accepted_help = value_delivered >= 1
        
        # Condition 3: Trust signals present
        has_trust_signals = len(trust_signals) >= 1 or "asked_opinion" in trust_signals
        
        # Golden trigger requires 2 out of 3 conditions
        conditions_met = sum([repeated_pain, accepted_help, has_trust_signals])
        
        if conditions_met >= 2:
            logger.info(f"🎯 Golden trigger activated for {contact.get('username')}: {best_match.offer_type}")
            return True, best_match
        
        return False, None
    
    def get_offer_timing_recommendation(
        self,
        contact: Dict,
        fit_match: FitSignalMatch
    ) -> Dict:
        """Get recommendation on when and how to make the offer."""
        health = contact.get("relationship_health", 50)
        stage = contact.get("pipeline_stage", "first_touch")
        
        # Don't offer if health is too low
        if health < 60:
            return {
                "ready": False,
                "reason": "Relationship health too low - warm up first",
                "action": "Deliver value and build trust before offering",
                "timing": "after_warmup"
            }
        
        # Don't offer if too early in pipeline
        early_stages = ["first_touch", "context_captured"]
        if stage in early_stages:
            return {
                "ready": False,
                "reason": "Still in early relationship stages",
                "action": "Continue building relationship - deliver a micro-win first",
                "timing": "after_micro_win"
            }
        
        # Ready to offer
        return {
            "ready": True,
            "reason": f"Good relationship health ({health}) and {fit_match.confidence:.0%} fit confidence",
            "action": "Make permissioned offer using the suggested line",
            "timing": "now",
            "offer_line": fit_match.offer_line,
            "approach": "Ask permission before pitching - 'want me to show you...'"
        }
