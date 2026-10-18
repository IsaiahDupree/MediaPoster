"""
Character Generation API (CHAR-001 to CHAR-004)
===============================================
API endpoints for AI character generation and management.

Endpoints:
- POST /api/characters - Generate new character
- POST /api/characters/{character_id}/variants - Generate expression variants
- GET /api/characters - List characters
- GET /api/characters/{character_id} - Get character details
- GET /api/characters/{character_id}/variants - Get character variants
- GET /api/characters/{character_id}/index - Get character index (CHAR-003)
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from services.character_generator import (
    get_character_generator,
    CharacterStyle,
    ExpressionType,
    CHARACTER_STYLES,
    EXPRESSIONS
)
from services.background_removal import get_background_removal_service

router = APIRouter(prefix="/api/characters", tags=["Characters"])


# =====================================================
# Request/Response Models
# =====================================================

class GenerateCharacterRequest(BaseModel):
    """Request to generate a new character"""
    workspace_id: UUID = Field(..., description="Workspace ID")
    name: str = Field(..., description="Character name", min_length=1, max_length=255)
    description: str = Field(..., description="Character appearance and traits", min_length=10)
    style: CharacterStyle = Field(default="cartoon", description="Visual style preset")
    base_expression: ExpressionType = Field(default="neutral", description="Default expression")
    size: str = Field(default="1024x1024", description="Image dimensions")
    quality: str = Field(default="hd", description="Image quality (standard or hd)")


class GenerateVariantsRequest(BaseModel):
    """Request to generate character variants"""
    expressions: List[ExpressionType] = Field(
        ...,
        description="List of expressions to generate",
        min_items=1,
        max_items=10
    )
    size: str = Field(default="1024x1024", description="Image dimensions")
    quality: str = Field(default="hd", description="Image quality")


class CharacterResponse(BaseModel):
    """Character response"""
    id: UUID
    workspace_id: UUID
    name: str
    description: str
    style: str
    base_expression: str
    file_path: str
    image_url: Optional[str]
    has_transparent_background: bool
    has_body_layer: bool
    has_mouth_layer: bool
    times_used: int
    created_at: str

    class Config:
        from_attributes = True


class CharacterVariantResponse(BaseModel):
    """Character variant response"""
    id: UUID
    character_id: UUID
    expression: str
    file_path: str
    image_url: Optional[str]
    has_transparent_background: bool
    has_body_layer: bool
    has_mouth_layer: bool
    times_used: int
    created_at: str

    class Config:
        from_attributes = True


class CharacterIndexResponse(BaseModel):
    """
    Character index for Remotion (CHAR-003)

    Provides all character variants in a JSON structure
    suitable for Remotion video composition.
    """
    character_id: UUID
    character_name: str
    style: str
    base_expression: str
    base_image: str
    variants: List[dict]
    total_variants: int


class AvailableStylesResponse(BaseModel):
    """Available character styles"""
    styles: dict


class AvailableExpressionsResponse(BaseModel):
    """Available expressions"""
    expressions: dict


# =====================================================
# Endpoints
# =====================================================

@router.post("", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def generate_character(request: GenerateCharacterRequest):
    """
    Generate a new AI character (CHAR-001)

    Creates a new character using DALL-E 3 with the specified style and expression.

    **Example:**
    ```json
    {
      "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Alex the Robot",
      "description": "Friendly blue robot with round head and antenna",
      "style": "cartoon",
      "base_expression": "happy"
    }
    ```
    """
    logger.info(f"Generating character: {request.name}")

    try:
        generator = get_character_generator()

        character = await generator.generate_character(
            workspace_id=request.workspace_id,
            name=request.name,
            description=request.description,
            style=request.style,
            base_expression=request.base_expression,
            size=request.size,  # type: ignore
            quality=request.quality  # type: ignore
        )

        return CharacterResponse(
            id=character.id,
            workspace_id=character.workspace_id,
            name=character.name,
            description=character.description,
            style=character.style,
            base_expression=character.base_expression,
            file_path=character.file_path,
            image_url=character.image_url,
            has_transparent_background=character.has_transparent_background,
            has_body_layer=character.has_body_layer,
            has_mouth_layer=character.has_mouth_layer,
            times_used=character.times_used,
            created_at=character.created_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to generate character: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Character generation failed: {str(e)}"
        )


@router.post("/{character_id}/variants", response_model=List[CharacterVariantResponse])
async def generate_character_variants(
    character_id: UUID,
    request: GenerateVariantsRequest
):
    """
    Generate expression variants for a character (CHAR-001)

    Creates multiple expression variants of an existing character,
    maintaining visual consistency across all variants.

    **Example:**
    ```json
    {
      "expressions": ["happy", "surprised", "thinking"],
      "size": "1024x1024",
      "quality": "hd"
    }
    ```
    """
    logger.info(f"Generating variants for character {character_id}")

    try:
        generator = get_character_generator()

        variants = await generator.generate_character_variants(
            character_id=character_id,
            expressions=request.expressions,
            size=request.size,  # type: ignore
            quality=request.quality  # type: ignore
        )

        return [
            CharacterVariantResponse(
                id=v.id,
                character_id=v.character_id,
                expression=v.expression,
                file_path=v.file_path,
                image_url=v.image_url,
                has_transparent_background=v.has_transparent_background,
                has_body_layer=v.has_body_layer,
                has_mouth_layer=v.has_mouth_layer,
                times_used=v.times_used,
                created_at=v.created_at.isoformat()
            )
            for v in variants
        ]

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to generate variants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Variant generation failed: {str(e)}"
        )


@router.get("", response_model=List[CharacterResponse])
async def list_characters(
    workspace_id: UUID,
    style: Optional[CharacterStyle] = None,
    limit: int = 50
):
    """
    List characters for a workspace

    Returns all characters, optionally filtered by style.
    """
    try:
        generator = get_character_generator()

        characters = await generator.list_characters(
            workspace_id=workspace_id,
            style=style,
            limit=limit
        )

        return [
            CharacterResponse(
                id=c.id,
                workspace_id=c.workspace_id,
                name=c.name,
                description=c.description,
                style=c.style,
                base_expression=c.base_expression,
                file_path=c.file_path,
                image_url=c.image_url,
                has_transparent_background=c.has_transparent_background,
                has_body_layer=c.has_body_layer,
                has_mouth_layer=c.has_mouth_layer,
                times_used=c.times_used,
                created_at=c.created_at.isoformat()
            )
            for c in characters
        ]

    except Exception as e:
        logger.error(f"Failed to list characters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list characters: {str(e)}"
        )


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: UUID):
    """Get character details"""
    try:
        generator = get_character_generator()
        character = await generator.get_character(character_id)

        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Character not found: {character_id}"
            )

        return CharacterResponse(
            id=character.id,
            workspace_id=character.workspace_id,
            name=character.name,
            description=character.description,
            style=character.style,
            base_expression=character.base_expression,
            file_path=character.file_path,
            image_url=character.image_url,
            has_transparent_background=character.has_transparent_background,
            has_body_layer=character.has_body_layer,
            has_mouth_layer=character.has_mouth_layer,
            times_used=character.times_used,
            created_at=character.created_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get character: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get character: {str(e)}"
        )


@router.get("/{character_id}/variants", response_model=List[CharacterVariantResponse])
async def get_character_variants(character_id: UUID):
    """Get all variants for a character"""
    try:
        generator = get_character_generator()
        variants = await generator.get_character_variants(character_id)

        return [
            CharacterVariantResponse(
                id=v.id,
                character_id=v.character_id,
                expression=v.expression,
                file_path=v.file_path,
                image_url=v.image_url,
                has_transparent_background=v.has_transparent_background,
                has_body_layer=v.has_body_layer,
                has_mouth_layer=v.has_mouth_layer,
                times_used=v.times_used,
                created_at=v.created_at.isoformat()
            )
            for v in variants
        ]

    except Exception as e:
        logger.error(f"Failed to get variants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get variants: {str(e)}"
        )


@router.get("/{character_id}/index", response_model=CharacterIndexResponse)
async def get_character_index(character_id: UUID):
    """
    Get character index for Remotion (CHAR-003)

    Returns a JSON structure with all character variants,
    suitable for use in Remotion video composition.

    **Use case:**
    ```typescript
    // In Remotion composition
    const characterIndex = await fetch(`/api/characters/${id}/index`);
    const happyVariant = characterIndex.variants.find(v => v.expression === 'happy');
    ```
    """
    try:
        generator = get_character_generator()

        # Get character
        character = await generator.get_character(character_id)
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Character not found: {character_id}"
            )

        # Get variants
        variants = await generator.get_character_variants(character_id)

        # Build index
        variant_list = [
            {
                "id": str(v.id),
                "expression": v.expression,
                "file_path": v.file_path,
                "image_url": v.image_url,
                "has_transparent_background": v.has_transparent_background,
                "has_body_layer": v.has_body_layer,
                "has_mouth_layer": v.has_mouth_layer,
                "body_layer_path": v.body_layer_path,
                "mouth_layer_path": v.mouth_layer_path,
                "created_at": v.created_at.isoformat()
            }
            for v in variants
        ]

        return CharacterIndexResponse(
            character_id=character.id,
            character_name=character.name,
            style=character.style,
            base_expression=character.base_expression,
            base_image=character.file_path,
            variants=variant_list,
            total_variants=len(variant_list)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get character index: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get character index: {str(e)}"
        )


@router.get("/meta/styles", response_model=AvailableStylesResponse)
async def get_available_styles():
    """Get available character styles"""
    return AvailableStylesResponse(styles=CHARACTER_STYLES)


@router.get("/meta/expressions", response_model=AvailableExpressionsResponse)
async def get_available_expressions():
    """Get available expressions"""
    return AvailableExpressionsResponse(expressions=EXPRESSIONS)


# =====================================================
# Background Removal Endpoints (CHAR-002)
# =====================================================

class RemoveBackgroundRequest(BaseModel):
    """Request to remove background from character"""
    model: str = Field(default="u2net", description="AI model (u2net, u2netp, u2net_human_seg)")
    alpha_matting: bool = Field(default=True, description="Enable alpha matting for better edges")
    overwrite: bool = Field(default=False, description="Overwrite existing transparent version")


class RemoveBackgroundResponse(BaseModel):
    """Background removal response"""
    character_id: UUID
    transparent_path: str
    has_transparent_background: bool
    message: str


class BatchRemoveBackgroundResponse(BaseModel):
    """Batch background removal response"""
    character_id: UUID
    base_processed: bool
    variants_processed: int
    variants_failed: int
    errors: List[str]


@router.post("/{character_id}/remove-background", response_model=RemoveBackgroundResponse)
async def remove_character_background(
    character_id: UUID,
    request: RemoveBackgroundRequest
):
    """
    Remove background from character (CHAR-002)

    Processes the character image to remove the background,
    creating a transparent PNG suitable for video overlays.

    **Example:**
    ```json
    {
      "model": "u2net",
      "alpha_matting": true,
      "overwrite": false
    }
    ```
    """
    logger.info(f"Removing background for character: {character_id}")

    try:
        remover = get_background_removal_service()

        transparent_path = await remover.process_character_asset(
            character_id=character_id,
            model=request.model,  # type: ignore
            alpha_matting=request.alpha_matting,
            overwrite=request.overwrite
        )

        # Get updated character
        generator = get_character_generator()
        character = await generator.get_character(character_id)

        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found after processing"
            )

        return RemoveBackgroundResponse(
            character_id=character.id,
            transparent_path=transparent_path,
            has_transparent_background=character.has_transparent_background,
            message="Background removed successfully"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to remove background: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Background removal failed: {str(e)}"
        )


@router.post("/{character_id}/variants/{variant_id}/remove-background", response_model=RemoveBackgroundResponse)
async def remove_variant_background(
    character_id: UUID,
    variant_id: UUID,
    request: RemoveBackgroundRequest
):
    """
    Remove background from character variant (CHAR-002)

    Processes a specific character variant to remove the background.
    """
    logger.info(f"Removing background for variant: {variant_id}")

    try:
        remover = get_background_removal_service()

        transparent_path = await remover.process_character_variant(
            variant_id=variant_id,
            model=request.model,  # type: ignore
            alpha_matting=request.alpha_matting,
            overwrite=request.overwrite
        )

        return RemoveBackgroundResponse(
            character_id=character_id,
            transparent_path=transparent_path,
            has_transparent_background=True,
            message="Background removed successfully"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to remove background: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Background removal failed: {str(e)}"
        )


@router.post("/{character_id}/batch-remove-background", response_model=BatchRemoveBackgroundResponse)
async def batch_remove_backgrounds(
    character_id: UUID,
    request: RemoveBackgroundRequest
):
    """
    Remove backgrounds from character and all variants (CHAR-002)

    Batch processes the base character and all its variants
    to remove backgrounds in one operation.
    """
    logger.info(f"Batch removing backgrounds for character: {character_id}")

    try:
        remover = get_background_removal_service()

        results = await remover.batch_process_character(
            character_id=character_id,
            model=request.model,  # type: ignore
            alpha_matting=request.alpha_matting,
            process_variants=True
        )

        return BatchRemoveBackgroundResponse(
            character_id=character_id,
            base_processed=results["base_processed"],
            variants_processed=results["variants_processed"],
            variants_failed=results["variants_failed"],
            errors=results["errors"]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed batch background removal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch background removal failed: {str(e)}"
        )
