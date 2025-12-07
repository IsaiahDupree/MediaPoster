from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel

# --- Data Models ---

class PersonContext(BaseModel):
    name: str
    interests: List[str]
    tone_preferences: List[str]
    recent_events: List[Dict[str, Any]]

class BrandContext(BaseModel):
    offer_name: str
    offer_benefits: List[str]
    voice: str
    constraints: List[str]

class MessageGoal(BaseModel):
    type: str # 'nurture', 'offer', 'reactivation'
    target_channel: str # 'email', 'instagram_dm'
    call_to_action: str

class GeneratedMessage(BaseModel):
    subject: Optional[str] = None
    body: str
    variant_label: str # 'A', 'B'
    rationale: Optional[str] = None

# --- Service Logic ---

async def assemble_person_context(person_id: UUID) -> PersonContext:
    """
    Fetch person data, insights, and recent events to build the 'Lens'.
    """
    # TODO: Fetch from DB
    return PersonContext(
        name="Alex Smith",
        interests=["AI Automation", "Python", "Content Marketing"],
        tone_preferences=["Casual", "Direct"],
        recent_events=[
            {"type": "commented", "excerpt": "Great video on automation!", "channel": "instagram"},
            {"type": "opened_email", "subject": "Weekly Newsletter", "channel": "email"}
        ]
    )

async def generate_message_variants(
    person_id: UUID,
    brand_context: BrandContext,
    goal: MessageGoal
) -> List[GeneratedMessage]:
    """
    Call LLM to generate personalized message variants based on Person Lens + Brand Context.
    """
    person_context = await assemble_person_context(person_id)
    
    # Mock LLM generation for now
    # In reality, this would construct a prompt and call OpenAI/Anthropic
    
    prompt = f"""
    Act as an expert copywriter.
    
    TARGET PERSON:
    Name: {person_context.name}
    Interests: {', '.join(person_context.interests)}
    Tone: {', '.join(person_context.tone_preferences)}
    Recent Activity: {person_context.recent_events}
    
    BRAND CONTEXT:
    Offer: {brand_context.offer_name}
    Benefits: {', '.join(brand_context.offer_benefits)}
    Voice: {brand_context.voice}
    
    GOAL:
    Channel: {goal.target_channel}
    Action: {goal.call_to_action}
    
    Generate 2 variants.
    """
    
    # print(f"DEBUG: LLM Prompt:\n{prompt}")
    
    return [
        GeneratedMessage(
            subject=f"Quick question about {person_context.interests[0]}",
            body=f"Hey {person_context.name}, saw your comment about automation. Have you tried {brand_context.offer_name}? It helps with {brand_context.offer_benefits[0]}.",
            variant_label="A - Direct Benefit",
            rationale="Leverages recent comment and top interest."
        ),
        GeneratedMessage(
            subject=f"Thinking of you re: {brand_context.offer_name}",
            body=f"Hi {person_context.name}, since you're into {person_context.interests[1]}, I thought you'd love {brand_context.offer_name}. {brand_context.offer_benefits[1]}!",
            variant_label="B - Interest Based",
            rationale="Connects secondary interest to offer benefit."
        )
    ]

async def log_outbound_message(
    person_id: UUID,
    segment_id: Optional[UUID],
    message: GeneratedMessage,
    goal: MessageGoal
):
    """
    Log the generated message to the outbound_messages table.
    """
    # TODO: Insert into DB
    print(f"Logged outbound message to {person_id}: {message.subject}")
