"""
Relationship AI Engine
Implements RF-005: Next-Best-Action AI Engine

AI suggests relationship-building actions, not pitches.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger
from openai import OpenAI


# =============================================================================
# MESSAGE TEMPLATES
# =============================================================================

FRIENDSHIP_TEMPLATES = [
    {"id": "A1", "template": "yo—how'd that thing go from last week?"},
    {"id": "A2", "template": "ok that's a real win. what do you think made it click?"},
    {"id": "A3", "template": "random but i remembered you said you were aiming for {goal} — still the plan?"},
    {"id": "A4", "template": "saw your post about {topic} — that hit different. what inspired that?"},
    {"id": "A5", "template": "haven't caught up in a bit — what's got your attention lately?"},
]

SERVICE_TEMPLATES = [
    {"id": "B1", "template": "want ideas or just want to vent?"},
    {"id": "B2", "template": "if i send you a quick template/checklist for that, would it help?"},
    {"id": "B3", "template": "send the screenshot/link — i'll tell you the 1 thing i'd fix first"},
    {"id": "B4", "template": "i know someone doing that well. want an intro?"},
    {"id": "B5", "template": "this might save you time: {resource}. if you tell me your setup i'll tailor it."},
    {"id": "B6", "template": "quick thought on {struggle} — have you tried {suggestion}?"},
]

OFFER_TEMPLATES = [
    {"id": "C1", "template": "you've mentioned {pain} a couple times — feels like that's the bottleneck."},
    {"id": "C2", "template": "want me to show you a simple way i solve that? no pressure."},
    {"id": "C3", "template": "do you want a quick suggestion, or do you want me to actually help you implement it?"},
    {"id": "C4", "template": "cool — wanna do 15 min and i'll map the fastest path?"},
]

RETENTION_TEMPLATES = [
    {"id": "R1", "template": "how's it feeling now that {project} is live? anything still annoying?"},
    {"id": "R2", "template": "i found a tweak that might boost results — want it?"},
    {"id": "R3", "template": "what part felt most helpful? i'm tightening the playbook."},
    {"id": "R4", "template": "if you know anyone stuck on {topic} i'm happy to help them too."},
]

REWARM_TEMPLATES = [
    {"id": "W1", "template": "no rush to reply — what are you focused on this month?"},
    {"id": "W2", "template": "saw this and thought of you: {resource}. want the 30-sec takeaway?"},
    {"id": "W3", "template": "been a minute! hope {project} is going well. any wins to celebrate?"},
]


@dataclass
class ActionSuggestion:
    """Suggested next action for a contact."""
    action_type: str
    lane: str  # A, B, or C
    template_id: str
    message: str
    reasoning: str
    priority: int  # 1-5, higher = more urgent
    timing: str  # "now", "today", "this_week", "next_week"


class RelationshipAI:
    """
    AI engine for relationship-first messaging.
    
    Philosophy: Help people genuinely, don't optimize for closes.
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
        logger.info("✅ RelationshipAI initialized")
    
    def get_next_best_action(self, contact: Dict) -> ActionSuggestion:
        """
        Get the next best action for a contact based on relationship health.
        
        Implements the core relationship-first logic:
        - 80-100: Nurture + light collaboration
        - 60-79: Deliver a micro-win, capture context
        - 40-59: Re-warm gently
        - <40: Don't chase — leave kind open loop
        """
        health = contact.get("relationship_health", 50)
        stage = contact.get("pipeline_stage", "first_touch")
        context = contact.get("context", {})
        scores = contact.get("scores", {})
        
        # Determine lane based on health and stage
        if health >= 80:
            return self._suggest_nurture_action(contact)
        elif health >= 60:
            return self._suggest_value_action(contact)
        elif health >= 40:
            return self._suggest_rewarm_action(contact)
        else:
            return self._suggest_gentle_open_loop(contact)
    
    def _suggest_nurture_action(self, contact: Dict) -> ActionSuggestion:
        """High health (80-100): Nurture and light collaboration."""
        context = contact.get("context", {})
        
        # Check for offer opportunity (golden trigger)
        trust_signals = contact.get("scores", {}).get("trust_signals", [])
        stage = contact.get("pipeline_stage", "")
        
        if stage == "fit_identified" and len(trust_signals) >= 2:
            # Ready for permissioned offer
            return ActionSuggestion(
                action_type="permissioned_offer",
                lane="C",
                template_id="C2",
                message="want me to show you a simple way i solve that? no pressure.",
                reasoning="Multiple trust signals + fit identified = golden trigger for offer",
                priority=4,
                timing="today"
            )
        
        # Otherwise, friendship check-in
        goal = context.get("win_30d", "your goal")
        return ActionSuggestion(
            action_type="check_in",
            lane="A",
            template_id="A3",
            message=f"random but i remembered you said you were aiming for {goal} — still the plan?",
            reasoning="Healthy relationship - maintain connection with genuine interest",
            priority=2,
            timing="this_week"
        )
    
    def _suggest_value_action(self, contact: Dict) -> ActionSuggestion:
        """Medium health (60-79): Deliver micro-win or capture context."""
        context = contact.get("context", {})
        stage = contact.get("pipeline_stage", "")
        
        # If we don't have context yet, ask
        if not context.get("building") and not context.get("struggles"):
            return ActionSuggestion(
                action_type="context_capture",
                lane="A",
                template_id="A5",
                message="haven't caught up in a bit — what's got your attention lately?",
                reasoning="Need to understand their current situation before helping",
                priority=3,
                timing="today"
            )
        
        # If we know their struggles, offer help
        struggle = context.get("struggles", "that challenge")
        return ActionSuggestion(
            action_type="micro_win",
            lane="B",
            template_id="B2",
            message=f"if i send you a quick template/checklist for {struggle}, would it help?",
            reasoning="Know their struggle - offer tangible help without being pushy",
            priority=4,
            timing="today"
        )
    
    def _suggest_rewarm_action(self, contact: Dict) -> ActionSuggestion:
        """Lower health (40-59): Re-warm gently with story reply + one question."""
        context = contact.get("context", {})
        project = context.get("building", "your project")
        
        return ActionSuggestion(
            action_type="rewarm",
            lane="A",
            template_id="W1",
            message="no rush to reply — what are you focused on this month?",
            reasoning="Relationship needs warming - gentle, no-pressure check-in",
            priority=2,
            timing="this_week"
        )
    
    def _suggest_gentle_open_loop(self, contact: Dict) -> ActionSuggestion:
        """Low health (<40): Don't chase, leave kind open loop."""
        return ActionSuggestion(
            action_type="open_loop",
            lane="A",
            template_id="W3",
            message="been a minute! hope things are going well. no rush, just wanted to say hey 👋",
            reasoning="Low health - don't chase, leave door open for when they're ready",
            priority=1,
            timing="next_week"
        )
    
    async def generate_personalized_message(
        self,
        contact: Dict,
        action: ActionSuggestion,
        tone: str = "casual"
    ) -> str:
        """
        Generate a personalized message using AI.
        
        Takes the template and personalizes it based on contact context.
        """
        if not self.client:
            return action.message
        
        context = contact.get("context", {})
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are helping write a genuine, friendly message to someone you're building a relationship with.

Key principles:
- Be authentic, not salesy
- Keep it short (1-3 sentences max)
- Match their communication style
- Focus on THEM, not you
- Never pitch unless they've asked

Tone: {tone}

Template to personalize: "{action.message}"

Contact context:
- Name: {contact.get('name', 'them')}
- What they're building: {context.get('building', 'unknown')}
- Their struggles: {context.get('struggles', 'unknown')}
- Recent wins: {context.get('win_30d', 'unknown')}

Write a natural, personalized version of the template. Keep the same intent but make it feel genuine."""
                    },
                    {
                        "role": "user",
                        "content": "Generate the personalized message."
                    }
                ],
                temperature=0.8,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"AI message generation failed: {e}")
            return action.message
    
    async def analyze_message_sentiment(self, message: str) -> Dict:
        """Analyze the sentiment and intent of an incoming message."""
        if not self.client:
            return {"sentiment": "neutral", "intent": "unknown", "resonance": "medium"}
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Analyze this message for relationship signals.
Return JSON with:
- sentiment: "positive", "neutral", "negative", or "personal"
- intent: "question", "sharing", "request", "thanks", "casual", or "business"
- resonance: "high" (emotional/detailed), "medium", or "low" (brief/surface)
- trust_signal: null or one of ["asked_opinion", "shared_personal", "referred_friend", "thanked", "requested_help"]"""
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {"sentiment": "neutral", "intent": "unknown", "resonance": "medium"}
    
    async def suggest_reply(
        self,
        contact: Dict,
        their_message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Suggest a reply to an incoming message.
        
        This is NOT an auto-reply - it's a suggestion for the human to review.
        """
        if not self.client:
            return {
                "suggestion": "Thanks for sharing! That's really interesting.",
                "lane": "A",
                "reasoning": "Fallback response"
            }
        
        context = contact.get("context", {})
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You're helping craft a reply that builds genuine connection.

Relationship-First Principles:
1. Consent > Conversion - Ask before advising or pitching
2. Micro-wins > Big Promises - Small help beats "let's hop on a call"
3. 3:1 Rule - For every offer touch, do 3 relationship touches

Contact Context:
- Name: {contact.get('name', 'Friend')}
- Building: {context.get('building', 'unknown')}
- Struggles: {context.get('struggles', 'unknown')}
- Relationship Health: {contact.get('relationship_health', 50)}/100

Their Message: "{their_message}"

Suggest a reply that:
- Matches their energy level
- Shows you listened
- Asks ONE follow-up question OR offers ONE small piece of value
- Stays in Lane A (friendship) or B (service), not C (offer) unless they explicitly asked

Return JSON with:
- suggestion: the message text
- lane: "A", "B", or "C"
- reasoning: why this approach"""
                    },
                    {
                        "role": "user",
                        "content": "Generate the reply suggestion."
                    }
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Reply suggestion failed: {e}")
            return {
                "suggestion": "That's great to hear! What's next for you?",
                "lane": "A",
                "reasoning": "Fallback response"
            }
    
    def get_batch_actions(self, contacts: List[Dict], limit: int = 10) -> List[Dict]:
        """
        Get prioritized actions for multiple contacts.
        
        Returns a sorted list of suggested actions.
        """
        actions = []
        
        for contact in contacts[:limit]:
            action = self.get_next_best_action(contact)
            actions.append({
                "contact_id": contact.get("id"),
                "username": contact.get("username"),
                "platform": contact.get("platform"),
                "health": contact.get("relationship_health", 50),
                "action": {
                    "type": action.action_type,
                    "lane": action.lane,
                    "message": action.message,
                    "reasoning": action.reasoning,
                    "priority": action.priority,
                    "timing": action.timing
                }
            })
        
        # Sort by priority (descending) and timing
        timing_order = {"now": 0, "today": 1, "this_week": 2, "next_week": 3}
        actions.sort(key=lambda x: (
            -x["action"]["priority"],
            timing_order.get(x["action"]["timing"], 4)
        ))
        
        return actions


# =============================================================================
# SINGLETON
# =============================================================================

_ai_instance: Optional[RelationshipAI] = None

def get_relationship_ai() -> RelationshipAI:
    """Get singleton instance of RelationshipAI."""
    global _ai_instance
    if _ai_instance is None:
        _ai_instance = RelationshipAI()
    return _ai_instance
