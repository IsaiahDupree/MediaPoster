"""
AI Video Generation API with Pub/Sub Architecture
===================================================
Endpoints for AI video generation using Sora, Runway, Pika, and other providers.
Implements pub/sub pattern for async job processing and status updates.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import logging
import uuid
import os
import json
import asyncio

# EventBus import for pub/sub
try:
    from services.event_bus import EventBus, Topics
    HAS_EVENT_BUS = True
except ImportError:
    HAS_EVENT_BUS = False

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai-video", tags=["AI Video Generation"])


# =============================================================================
# MODELS
# =============================================================================

class VideoGenerationRequest(BaseModel):
    provider: str = Field(..., description="sora, runway, pika, kling, luma, minimax, haiper")
    prompt: str = Field(..., description="Text prompt describing the video")
    settings: Dict[str, Any] = Field(default_factory=dict)
    generate_title: bool = True
    generate_description: bool = True
    style_preset: Optional[str] = None
    camera_motion: Optional[str] = None
    character_ids: Optional[List[str]] = None


class VideoGenerationResponse(BaseModel):
    id: str
    job_id: str
    status: str
    message: str
    estimated_time_seconds: Optional[int] = None


class VideoJob(BaseModel):
    id: str
    status: str  # queued, processing, rendering, completed, failed
    progress: int
    provider: str
    prompt: str
    created_at: str
    estimated_completion: Optional[str] = None
    output_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    ai_title: Optional[str] = None
    ai_description: Optional[str] = None
    error_message: Optional[str] = None


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

def ensure_tables():
    """Create AI video generation tables if they don't exist."""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ai_video_generations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    job_id UUID NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    prompt TEXT NOT NULL,
                    enhanced_prompt TEXT,
                    settings JSONB DEFAULT '{}'::jsonb,
                    
                    -- Style and motion
                    style_preset VARCHAR(50),
                    camera_motion VARCHAR(50),
                    character_ids UUID[],
                    
                    -- Status tracking
                    status VARCHAR(20) DEFAULT 'queued',
                    progress INTEGER DEFAULT 0,
                    error_message TEXT,
                    
                    -- Output
                    output_url TEXT,
                    thumbnail_url TEXT,
                    duration_seconds DECIMAL(10, 2),
                    resolution VARCHAR(20),
                    aspect_ratio VARCHAR(10),
                    file_size_bytes BIGINT,
                    
                    -- AI-generated metadata
                    ai_title TEXT,
                    ai_description TEXT,
                    
                    -- Link to media library
                    video_id UUID,
                    
                    -- Timestamps
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    started_at TIMESTAMPTZ,
                    completed_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ai_video_gen_provider 
                ON ai_video_generations(provider)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ai_video_gen_status 
                ON ai_video_generations(status)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ai_video_gen_job_id 
                ON ai_video_generations(job_id)
            """))
            
            conn.commit()
            logger.info("AI video generation tables ensured")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")


# =============================================================================
# PUB/SUB EVENT HANDLERS
# =============================================================================

class VideoGenerationTopics:
    """Event topics for video generation pub/sub.
    
    Maps to standard Topics class for consistency:
    - JOB_QUEUED -> Topics.AI_GENERATION_REQUESTED
    - JOB_STARTED -> Topics.AI_GENERATION_STARTED
    - JOB_PROGRESS -> Topics.AI_GENERATION_PROGRESS
    - JOB_COMPLETED -> Topics.AI_GENERATION_COMPLETED
    - JOB_FAILED -> Topics.AI_GENERATION_FAILED
    """
    # Use standard Topics when available, fallback to custom
    JOB_QUEUED = Topics.AI_GENERATION_REQUESTED if HAS_EVENT_BUS else "ai_video.job.queued"
    JOB_STARTED = Topics.AI_GENERATION_STARTED if HAS_EVENT_BUS else "ai_video.job.started"
    JOB_PROGRESS = Topics.AI_GENERATION_PROGRESS if HAS_EVENT_BUS else "ai_video.job.progress"
    JOB_COMPLETED = Topics.AI_GENERATION_COMPLETED if HAS_EVENT_BUS else "ai_video.job.completed"
    JOB_FAILED = Topics.AI_GENERATION_FAILED if HAS_EVENT_BUS else "ai_video.job.failed"
    TITLE_GENERATED = "ai_video.metadata.title_generated"
    DESCRIPTION_GENERATED = "ai_video.metadata.description_generated"


async def publish_event(topic: str, payload: Dict[str, Any], correlation_id: str = None):
    """Publish event to EventBus if available."""
    if HAS_EVENT_BUS:
        try:
            bus = EventBus.get_instance()
            await bus.publish(topic, payload, correlation_id=correlation_id)
        except Exception as e:
            logger.warning(f"Failed to publish event {topic}: {e}")


# =============================================================================
# AI TITLE/DESCRIPTION GENERATION
# =============================================================================

async def generate_ai_title(prompt: str) -> str:
    """Generate an AI title for the video based on the prompt."""
    # In production, this would call an LLM API
    # For now, create a smart title from the prompt
    words = prompt.split()[:6]
    title = " ".join(words).title()
    if len(prompt) > 50:
        title = title[:47] + "..."
    return title


async def generate_ai_description(prompt: str, settings: Dict[str, Any]) -> str:
    """Generate an AI description for the video."""
    # In production, this would call an LLM API
    duration = settings.get('duration', '10s')
    style = settings.get('style', 'cinematic')
    aspect = settings.get('aspect_ratio', '16:9')
    
    description = f"AI-generated {duration} {style} video in {aspect} format. {prompt}"
    return description[:500]


# =============================================================================
# VIDEO GENERATION SIMULATION (Replace with actual provider APIs)
# =============================================================================

async def simulate_video_generation(job_id: str, provider: str, prompt: str, settings: Dict[str, Any]):
    """Simulate video generation process. Replace with actual API calls."""
    engine = get_engine()
    
    try:
        # Update status to processing
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE ai_video_generations 
                SET status = 'processing', started_at = NOW(), progress = 10
                WHERE job_id = :job_id
            """), {'job_id': job_id})
            conn.commit()
        
        await publish_event(VideoGenerationTopics.JOB_STARTED, {
            'job_id': job_id, 'provider': provider
        }, correlation_id=job_id)
        
        # Simulate rendering progress
        for progress in [25, 50, 75, 90]:
            await asyncio.sleep(2)  # Simulate work
            
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE ai_video_generations 
                    SET progress = :progress, status = 'rendering'
                    WHERE job_id = :job_id
                """), {'job_id': job_id, 'progress': progress})
                conn.commit()
            
            await publish_event(VideoGenerationTopics.JOB_PROGRESS, {
                'job_id': job_id, 'progress': progress
            }, correlation_id=job_id)
        
        # Generate AI title and description
        ai_title = await generate_ai_title(prompt)
        ai_description = await generate_ai_description(prompt, settings)
        
        await publish_event(VideoGenerationTopics.TITLE_GENERATED, {
            'job_id': job_id, 'title': ai_title
        }, correlation_id=job_id)
        
        await publish_event(VideoGenerationTopics.DESCRIPTION_GENERATED, {
            'job_id': job_id, 'description': ai_description
        }, correlation_id=job_id)
        
        # Complete the job
        # In production, this would be the actual video URL from the provider
        output_url = f"https://storage.example.com/videos/{job_id}.mp4"
        thumbnail_url = f"https://storage.example.com/thumbnails/{job_id}.jpg"
        
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE ai_video_generations 
                SET status = 'completed', 
                    progress = 100,
                    output_url = :output_url,
                    thumbnail_url = :thumbnail_url,
                    ai_title = :ai_title,
                    ai_description = :ai_description,
                    completed_at = NOW()
                WHERE job_id = :job_id
            """), {
                'job_id': job_id,
                'output_url': output_url,
                'thumbnail_url': thumbnail_url,
                'ai_title': ai_title,
                'ai_description': ai_description
            })
            conn.commit()
        
        await publish_event(VideoGenerationTopics.JOB_COMPLETED, {
            'job_id': job_id,
            'output_url': output_url,
            'ai_title': ai_title,
            'ai_description': ai_description
        }, correlation_id=job_id)
        
        logger.info(f"Video generation completed: {job_id}")
        
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE ai_video_generations 
                SET status = 'failed', error_message = :error
                WHERE job_id = :job_id
            """), {'job_id': job_id, 'error': str(e)})
            conn.commit()
        
        await publish_event(VideoGenerationTopics.JOB_FAILED, {
            'job_id': job_id, 'error': str(e)
        }, correlation_id=job_id)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest, background_tasks: BackgroundTasks):
    """
    Start a new AI video generation job.
    
    Publishes to: ai_video.job.queued
    """
    ensure_tables()
    engine = get_engine()
    
    job_id = str(uuid.uuid4())
    gen_id = str(uuid.uuid4())
    
    # Estimate time based on provider and settings
    duration_map = {'5s': 30, '10s': 60, '15s': 90, '20s': 120}
    duration = request.settings.get('duration', '10s')
    estimated_time = duration_map.get(duration, 60)
    
    # Extract style/motion from settings if present
    style_preset = request.settings.get('style') or request.style_preset
    camera_motion = request.settings.get('camera_motion') or request.camera_motion
    character_ids = request.settings.get('characters') or request.character_ids
    duration = request.settings.get('duration', '10s')
    resolution = request.settings.get('resolution', '1080p')
    aspect_ratio = request.settings.get('aspect_ratio', '16:9')
    
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO ai_video_generations 
                (id, job_id, provider, prompt, enhanced_prompt, settings, style_preset, 
                 camera_motion, resolution, aspect_ratio, status, progress)
                VALUES (:id, :job_id, :provider, :prompt, :enhanced_prompt, :settings, 
                        :style_preset, :camera_motion, :resolution, :aspect_ratio, 'queued', 0)
            """), {
                'id': gen_id,
                'job_id': job_id,
                'provider': request.provider,
                'prompt': request.prompt,
                'enhanced_prompt': request.prompt,  # Frontend sends enhanced prompt
                'settings': json.dumps(request.settings),
                'style_preset': style_preset,
                'camera_motion': camera_motion,
                'resolution': resolution,
                'aspect_ratio': aspect_ratio
            })
            conn.commit()
        
        # Publish job queued event
        await publish_event(VideoGenerationTopics.JOB_QUEUED, {
            'job_id': job_id,
            'provider': request.provider,
            'prompt': request.prompt[:100]
        }, correlation_id=job_id)
        
        # Start background processing
        background_tasks.add_task(
            simulate_video_generation,
            job_id,
            request.provider,
            request.prompt,
            request.settings
        )
        
        return VideoGenerationResponse(
            id=gen_id,
            job_id=job_id,
            status="queued",
            message=f"Video generation queued with {request.provider}",
            estimated_time_seconds=estimated_time
        )
        
    except Exception as e:
        logger.error(f"Error starting video generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generations")
async def list_generations(
    provider: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """Get list of AI video generations with optional filtering."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            query = """
                SELECT id, job_id, provider, prompt, settings, status, progress,
                       output_url, thumbnail_url, ai_title, ai_description,
                       error_message, created_at, completed_at
                FROM ai_video_generations
                WHERE 1=1
            """
            params = {'limit': limit}
            
            if provider:
                query += " AND provider = :provider"
                params['provider'] = provider
            
            if status:
                query += " AND status = :status"
                params['status'] = status
            
            query += " ORDER BY created_at DESC LIMIT :limit"
            
            result = conn.execute(text(query), params).fetchall()
            
            generations = [
                {
                    'id': str(row[0]),
                    'job_id': str(row[1]),
                    'provider': row[2],
                    'input': row[3],
                    'settings': row[4] if isinstance(row[4], dict) else json.loads(row[4] or '{}'),
                    'status': row[5],
                    'progress': row[6],
                    'output_url': row[7],
                    'thumbnail_url': row[8],
                    'ai_title': row[9],
                    'ai_description': row[10],
                    'error_message': row[11],
                    'created_at': row[12].isoformat() if row[12] else None,
                    'completed_at': row[13].isoformat() if row[13] else None,
                    'type': 'video'
                }
                for row in result
            ]
            
            return {'generations': generations, 'count': len(generations)}
            
    except Exception as e:
        logger.error(f"Error fetching generations: {e}")
        return {'generations': [], 'count': 0, 'error': str(e)}


@router.get("/jobs/status")
async def get_jobs_status():
    """Get status of all active jobs (for polling)."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT job_id, status, progress, provider, prompt, 
                       ai_title, ai_description, created_at, output_url
                FROM ai_video_generations
                WHERE status IN ('queued', 'processing', 'rendering')
                ORDER BY created_at DESC
            """)).fetchall()
            
            jobs = [
                {
                    'id': str(row[0]),
                    'status': row[1],
                    'progress': row[2],
                    'provider': row[3],
                    'prompt': row[4],
                    'ai_title': row[5],
                    'ai_description': row[6],
                    'created_at': row[7].isoformat() if row[7] else None,
                    'output_url': row[8]
                }
                for row in result
            ]
            
            return {'jobs': jobs, 'count': len(jobs)}
            
    except Exception as e:
        logger.error(f"Error fetching job status: {e}")
        return {'jobs': [], 'count': 0}


@router.get("/job/{job_id}")
async def get_job(job_id: str):
    """Get details of a specific job."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, job_id, provider, prompt, settings, status, progress,
                       output_url, thumbnail_url, ai_title, ai_description,
                       error_message, created_at, started_at, completed_at
                FROM ai_video_generations
                WHERE job_id = :job_id
            """), {'job_id': job_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="Job not found")
            
            return {
                'id': str(result[0]),
                'job_id': str(result[1]),
                'provider': result[2],
                'prompt': result[3],
                'settings': result[4] if isinstance(result[4], dict) else json.loads(result[4] or '{}'),
                'status': result[5],
                'progress': result[6],
                'output_url': result[7],
                'thumbnail_url': result[8],
                'ai_title': result[9],
                'ai_description': result[10],
                'error_message': result[11],
                'created_at': result[12].isoformat() if result[12] else None,
                'started_at': result[13].isoformat() if result[13] else None,
                'completed_at': result[14].isoformat() if result[14] else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/job/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a queued or processing job."""
    ensure_tables()
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE ai_video_generations
                SET status = 'cancelled'
                WHERE job_id = :job_id AND status IN ('queued', 'processing')
                RETURNING id
            """), {'job_id': job_id}).fetchone()
            conn.commit()
            
            if not result:
                raise HTTPException(status_code=404, detail="Job not found or already completed")
            
            return {'success': True, 'message': 'Job cancelled'}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def list_providers():
    """Get list of available AI video providers."""
    return {
        'providers': [
            {
                'id': 'sora',
                'name': 'Sora',
                'company': 'OpenAI',
                'available': True,
                'max_duration': '20s',
                'supported_aspects': ['16:9', '9:16', '1:1', '4:3']
            },
            {
                'id': 'runway',
                'name': 'Runway Gen-3',
                'company': 'Runway',
                'available': True,
                'max_duration': '16s',
                'supported_aspects': ['16:9', '9:16', '1:1']
            },
            {
                'id': 'pika',
                'name': 'Pika 2.0',
                'company': 'Pika Labs',
                'available': True,
                'max_duration': '5s',
                'supported_aspects': ['16:9', '9:16', '1:1', '4:5']
            },
            {
                'id': 'kling',
                'name': 'Kling AI',
                'company': 'Kuaishou',
                'available': True,
                'max_duration': '10s',
                'supported_aspects': ['16:9', '9:16', '1:1']
            },
            {
                'id': 'luma',
                'name': 'Luma Dream Machine',
                'company': 'Luma AI',
                'available': True,
                'max_duration': '15s',
                'supported_aspects': ['16:9', '9:16', '1:1', '21:9']
            }
        ]
    }


@router.get("/templates")
async def get_templates():
    """Get video generation templates."""
    return {
        'templates': [
            {
                'id': 'cinematic',
                'name': 'Cinematic Drone',
                'prompt': 'Cinematic drone shot flying over [LOCATION] at golden hour, smooth motion, 4K quality',
                'category': 'aerial',
                'provider': 'sora'
            },
            {
                'id': 'product',
                'name': 'Product Showcase',
                'prompt': 'Professional product shot of [PRODUCT] rotating slowly on minimalist background, studio lighting',
                'category': 'commercial',
                'provider': 'sora'
            },
            {
                'id': 'nature',
                'name': 'Nature Scene',
                'prompt': 'Beautiful nature scene of [SCENE], peaceful atmosphere, gentle camera movement',
                'category': 'nature',
                'provider': 'sora'
            },
            {
                'id': 'urban',
                'name': 'Urban Timelapse',
                'prompt': 'Timelapse of busy city street at [TIME], people walking, cars passing, cinematic look',
                'category': 'urban',
                'provider': 'sora'
            },
            {
                'id': 'abstract',
                'name': 'Abstract Motion',
                'prompt': 'Abstract flowing [MATERIAL] patterns, smooth morphing shapes, vibrant colors',
                'category': 'abstract',
                'provider': 'sora'
            },
            {
                'id': 'lifestyle',
                'name': 'Lifestyle Content',
                'prompt': 'Person [ACTION] in modern setting, natural lighting, authentic feel',
                'category': 'lifestyle',
                'provider': 'sora'
            }
        ]
    }


@router.get("/styles")
async def get_style_presets():
    """Get available style presets."""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, name, description, icon, keywords, color_gradient, category
                FROM ai_style_presets
                ORDER BY is_system DESC, usage_count DESC
            """)).fetchall()
            
            return {
                'styles': [
                    {
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'icon': row[3],
                        'keywords': row[4],
                        'color': row[5],
                        'category': row[6]
                    }
                    for row in result
                ]
            }
    except Exception as e:
        # Return default styles if table doesn't exist
        return {
            'styles': [
                {'id': 'cinematic', 'name': 'Cinematic', 'icon': '🎬', 'keywords': '35mm film, cinematic lighting'},
                {'id': 'photorealistic', 'name': 'Photorealistic', 'icon': '📷', 'keywords': '8K, photorealistic'},
                {'id': 'anime', 'name': 'Anime', 'icon': '🎨', 'keywords': 'anime style, hand-drawn'},
                {'id': 'cyberpunk', 'name': 'Cyberpunk', 'icon': '🌃', 'keywords': 'cyberpunk, neon lights'},
                {'id': 'dreamy', 'name': 'Dreamy', 'icon': '☁️', 'keywords': 'soft focus, ethereal glow'},
            ]
        }


@router.get("/camera-motions")
async def get_camera_motions():
    """Get available camera motion presets."""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, name, description, icon, keywords
                FROM ai_camera_motions
                ORDER BY id
            """)).fetchall()
            
            return {
                'motions': [
                    {
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'icon': row[3],
                        'keywords': row[4]
                    }
                    for row in result
                ]
            }
    except Exception as e:
        # Return default motions if table doesn't exist
        return {
            'motions': [
                {'id': 'static', 'name': 'Static', 'icon': '⏸️', 'keywords': 'static shot'},
                {'id': 'slow_pan', 'name': 'Slow Pan', 'icon': '↔️', 'keywords': 'slow pan'},
                {'id': 'dolly_in', 'name': 'Dolly In', 'icon': '🎯', 'keywords': 'dolly in'},
                {'id': 'orbit', 'name': 'Orbit', 'icon': '🔄', 'keywords': 'orbit shot'},
                {'id': 'drone', 'name': 'Drone', 'icon': '🚁', 'keywords': 'drone shot, aerial'},
            ]
        }


@router.get("/characters")
async def list_characters():
    """Get saved characters for the user."""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, name, description, avatar_emoji, attributes, usage_count, created_at
                FROM ai_characters
                ORDER BY usage_count DESC, created_at DESC
                LIMIT 50
            """)).fetchall()
            
            return {
                'characters': [
                    {
                        'id': str(row[0]),
                        'name': row[1],
                        'description': row[2],
                        'avatar': row[3] or '👤',
                        'attributes': row[4] or {},
                        'usage_count': row[5],
                        'created_at': str(row[6]) if row[6] else None
                    }
                    for row in result
                ]
            }
    except Exception as e:
        # Return empty list if table doesn't exist
        return {'characters': []}


class CharacterCreate(BaseModel):
    name: str
    description: str
    avatar: Optional[str] = '👤'
    attributes: Optional[Dict[str, Any]] = {}


@router.post("/characters")
async def create_character(character: CharacterCreate):
    """Create a new character."""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            # Ensure table exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ai_characters (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    avatar_emoji TEXT DEFAULT '👤',
                    attributes JSONB DEFAULT '{}',
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            
            result = conn.execute(text("""
                INSERT INTO ai_characters (name, description, avatar_emoji, attributes)
                VALUES (:name, :description, :avatar, :attributes)
                RETURNING id
            """), {
                'name': character.name,
                'description': character.description,
                'avatar': character.avatar,
                'attributes': json.dumps(character.attributes)
            })
            
            conn.commit()
            char_id = result.fetchone()[0]
            
            return {
                'id': str(char_id),
                'name': character.name,
                'description': character.description,
                'avatar': character.avatar,
                'attributes': character.attributes,
                'message': 'Character created successfully'
            }
    except Exception as e:
        logger.error(f"Error creating character: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/characters/{character_id}")
async def delete_character(character_id: str):
    """Delete a character."""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                DELETE FROM ai_characters WHERE id = :id
            """), {'id': character_id})
            conn.commit()
            
            return {'message': 'Character deleted', 'id': character_id}
    except Exception as e:
        logger.error(f"Error deleting character: {e}")
        raise HTTPException(status_code=500, detail=str(e))
