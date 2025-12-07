from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel

from services.message_engine import (
    assemble_person_context,
    generate_message_variants,
    log_outbound_message,
    BrandContext,
    MessageGoal,
    GeneratedMessage
)

router = APIRouter()

class GenerateRequest(BaseModel):
    person_id: UUID
    brand_context: BrandContext
    goal: MessageGoal
    segment_id: Optional[UUID] = None

@router.post("/generate", response_model=List[GeneratedMessage])
async def generate_messages(request: GenerateRequest):
    """
    Generate personalized message variants for a specific person.
    """
    variants = await generate_message_variants(
        person_id=request.person_id,
        brand_context=request.brand_context,
        goal=request.goal
    )
    
    # Optionally log them immediately or wait for "send" action
    # For now, we just return them for review
    
    return variants

@router.post("/send")
async def send_message(
    person_id: UUID, 
    message: GeneratedMessage, 
    goal: MessageGoal,
    segment_id: Optional[UUID] = None
):
    """
    'Send' the message (log it and trigger ESP/DM provider).
    """
    # 1. Log to DB
    await log_outbound_message(person_id, segment_id, message, goal)
    
    # 2. Trigger actual send (TODO: Integrate ESP/Blotato DM)
    
    return {"status": "sent", "timestamp": datetime.now()}
