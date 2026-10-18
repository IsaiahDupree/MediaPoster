from typing import List
from uuid import UUID, uuid4
from datetime import datetime
from connectors.base import ContentVariant

def generate_variants_for_item(
    content_id: UUID, 
    platforms: List[str],
    base_title: str,
    base_description: str,
    base_thumbnail_url: str
) -> List[ContentVariant]:
    """
    Generate platform-specific variants from a base content item.
    This is where AI logic would eventually go to customize titles/descriptions per platform.
    """
    variants = []
    
    for platform in platforms:
        # Basic logic: use base metadata for all, customize slightly if needed
        variant = ContentVariant(
            id=str(uuid4()),
            content_id=str(content_id),
            platform=platform,
            title=base_title,
            description=base_description,
            thumbnail_url=base_thumbnail_url,
            is_paid=False,
            variant_label=f"Default {platform.capitalize()}"
        )
        
        # Simple platform-specific tweaks (placeholder for AI)
        if platform == 'twitter':
            variant.description = base_description[:280] # Truncate for Twitter
            
        variants.append(variant)
        
    return variants
