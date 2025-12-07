from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID, uuid4

from database.connection import get_db
from connectors.base import ContentVariant

router = APIRouter()

# --- Pydantic Models ---

class ContentItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: str # 'video', 'article', 'audio', 'image', 'carousel'
    source_url: Optional[str] = None
    slug: Optional[str] = None

class ContentItemResponse(ContentItemCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

class ContentVariantCreate(BaseModel):
    content_id: UUID
    platform: str
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    is_paid: bool = False
    variant_label: Optional[str] = None

class ContentVariantResponse(ContentVariantCreate):
    id: UUID
    platform_post_id: Optional[str] = None
    platform_post_url: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime

# --- Endpoints ---

@router.get("/")
async def list_content():
    """List all content (redirects to /items)"""
    # Simple endpoint for /api/content
    return []


@router.get("/metrics")
async def get_content_metrics():
    """Get content metrics summary"""
    return {
        "total_items": 0,
        "total_variants": 0,
        "published": 0,
        "scheduled": 0
    }


@router.post("/items", response_model=ContentItemResponse, status_code=status.HTTP_201_CREATED)
async def create_content_item(item: ContentItemCreate):
    """Create a new canonical content item"""
    # TODO: Implement DB insert
    # For now, return mock response
    return ContentItemResponse(
        id=uuid4(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        **item.model_dump()
    )

@router.get("/items", response_model=List[ContentItemResponse])
async def list_content_items():
    """List all content items"""
    # TODO: Implement DB select
    return []

@router.get("/items/{item_id}", response_model=ContentItemResponse)
async def get_content_item(item_id: UUID):
    """Get a specific content item"""
    # TODO: Implement DB select
    return ContentItemResponse(
        id=item_id,
        title="Mock Item",
        type="video",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@router.post("/variants", response_model=ContentVariantResponse, status_code=status.HTTP_201_CREATED)
async def create_content_variant(variant: ContentVariantCreate):
    """Create a platform-specific variant for a content item"""
    # TODO: Implement DB insert
    return ContentVariantResponse(
        id=uuid4(),
        created_at=datetime.now(),
        **variant.model_dump()
    )

@router.get("/items/{item_id}/variants", response_model=List[ContentVariantResponse])
async def list_content_variants(item_id: UUID):
    """List all variants for a content item"""
    # TODO: Implement DB select
    return []

from services.variant_generator import generate_variants_for_item
from connectors import registry

@router.post("/items/{item_id}/generate-variants", response_model=List[ContentVariantResponse])
async def generate_variants(item_id: UUID, platforms: List[str]):
    """Generate variants for a content item for specified platforms"""
    # TODO: Fetch item from DB
    # item = db.get(item_id)
    item_title = "Mock Title"
    item_desc = "Mock Description"
    item_thumb = "http://example.com/thumb.jpg"
    
    variants = generate_variants_for_item(
        content_id=item_id,
        platforms=platforms,
        base_title=item_title,
        base_description=item_desc,
        base_thumbnail_url=item_thumb
    )
    
    # TODO: Save variants to DB
    
    return [
        ContentVariantResponse(
            id=UUID(v.id),
            created_at=datetime.now(),
            **v.model_dump(exclude={'id'})
        ) for v in variants
    ]

@router.post("/variants/{variant_id}/publish")
async def publish_variant(variant_id: UUID):
    """Publish a variant to its platform via the appropriate connector"""
    # TODO: Fetch variant from DB
    # variant_db = db.get(variant_id)
    
    # Mock variant for now
    variant_data = ContentVariant(
        id=str(variant_id),
        content_id=str(uuid4()),
        platform="instagram",
        title="Test Post",
        description="Test Description"
    )
    
    # Find adapter
    adapters = registry.get_adapters_for_platform(variant_data.platform)
    if not adapters:
        raise HTTPException(status_code=400, detail=f"No enabled adapter found for platform: {variant_data.platform}")
    
    adapter = adapters[0] # Use first available adapter (likely Blotato or Native)
    
from services.metrics_collector import poll_metrics_for_active_variants
from services.analytics_aggregator import run_nightly_aggregation

@router.post("/jobs/poll-metrics")
async def trigger_metrics_poll():
    """Manually trigger metrics polling for all active variants"""
    count = await poll_metrics_for_active_variants()
    return {"status": "success", "snapshots_collected": count}

@router.post("/jobs/aggregate-rollups")
async def trigger_analytics_aggregation():
    """Manually trigger nightly analytics aggregation"""
    await run_nightly_aggregation()
    return {"status": "success", "message": "Aggregation job started"}
