"""
Content Ideas Generation API
AI-powered content idea generation based on competitor patterns, trends, and gaps.
"""
import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
import openai

from services.competitor_service import get_competitor_service, COMPETITOR_RESEARCH_DIR

router = APIRouter(prefix="/api/content-ideas", tags=["Content Ideas"])


class GenerateIdeasRequest(BaseModel):
    """Request to generate content ideas"""
    niche: str = "personal branding"
    competitor_usernames: Optional[List[str]] = None
    count: int = 10
    include_hooks: bool = True
    include_hashtags: bool = True
    include_format: bool = True
    user_themes: Optional[List[str]] = None  # themes user already covers


class SaveIdeaRequest(BaseModel):
    """Request to save a content idea"""
    title: str
    hook: Optional[str] = None
    hook_type: Optional[str] = None
    format_type: Optional[str] = None
    hashtags: List[str] = []
    why_it_works: Optional[str] = None
    notes: Optional[str] = None


def _load_competitor_context(usernames: Optional[List[str]] = None) -> Dict[str, Any]:
    """Load competitor analysis data for idea generation context"""
    accounts_dir = COMPETITOR_RESEARCH_DIR / "accounts"
    if not accounts_dir.exists():
        return {}

    context = {
        "accounts": [],
        "hooks": [],
        "formats": [],
        "themes": [],
        "ideas": [],
        "learnings": [],
    }

    for account_dir in accounts_dir.iterdir():
        if not account_dir.is_dir() or account_dir.name.startswith("."):
            continue
        if usernames and account_dir.name not in usernames:
            continue

        analysis_file = account_dir / "analysis" / "learnings.json"
        if not analysis_file.exists():
            continue

        try:
            with open(analysis_file) as f:
                data = json.load(f)

            context["accounts"].append(account_dir.name)
            for h in data.get("top_hooks", []):
                context["hooks"].append(h.get("type"))
            for fmt in data.get("top_formats", []):
                context["formats"].append(fmt.get("type"))
            context["themes"].extend(data.get("content_themes", []))
            context["ideas"].extend(data.get("content_ideas", []))
            context["learnings"].extend(data.get("key_learnings", []))
        except Exception as e:
            logger.error(f"Error loading analysis for {account_dir.name}: {e}")

    return context


def _load_trending_context() -> Dict[str, Any]:
    """Load trending hashtag data"""
    trending_path = COMPETITOR_RESEARCH_DIR / "learnings" / "trending_hashtags.json"
    if trending_path.exists():
        try:
            with open(trending_path) as f:
                data = json.load(f)
            return {
                "hashtags": [h.get("tag") for h in data.get("hashtags", [])[:15]]
            }
        except Exception:
            pass
    return {"hashtags": []}


@router.get("/health")
async def health_check():
    """Health check for content ideas service"""
    return {"status": "healthy", "service": "content-ideas"}


@router.post("/generate")
async def generate_ideas(request: GenerateIdeasRequest):
    """
    Generate AI-powered content ideas based on competitor patterns and trends.
    
    Combines:
    - Top-performing hooks from competitor analysis
    - Trending content formats
    - Content gap opportunities
    - Current trending hashtags
    
    Returns ready-to-create content ideas with hooks, formats, and hashtags.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    # Gather context
    competitor_ctx = _load_competitor_context(request.competitor_usernames)
    trending_ctx = _load_trending_context()

    if not competitor_ctx.get("accounts"):
        raise HTTPException(
            status_code=404,
            detail="No competitor analysis data found. Analyze competitors first.",
        )

    # Deduplicate
    unique_hooks = list(set(competitor_ctx.get("hooks", [])))[:10]
    unique_formats = list(set(competitor_ctx.get("formats", [])))[:8]
    unique_themes = list(set(competitor_ctx.get("themes", [])))[:15]
    unique_learnings = list(set(competitor_ctx.get("learnings", [])))[:10]
    existing_ideas = competitor_ctx.get("ideas", [])[:5]

    try:
        client = openai.OpenAI(api_key=api_key)

        prompt = f"""Generate {request.count} Instagram content ideas for the "{request.niche}" niche.

CONTEXT FROM COMPETITOR ANALYSIS ({len(competitor_ctx['accounts'])} accounts):
- Top hook types that perform well: {json.dumps(unique_hooks)}
- Top content formats: {json.dumps(unique_formats)}
- Popular themes: {json.dumps(unique_themes)}
- Key learnings: {json.dumps(unique_learnings[:5])}

TRENDING HASHTAGS:
{json.dumps(trending_ctx.get('hashtags', [])[:10])}

{"USER ALREADY COVERS THESE THEMES (avoid repeating): " + json.dumps(request.user_themes) if request.user_themes else ""}

Generate {request.count} specific, ready-to-create content ideas as a JSON array:
[
    {{
        "title": "The content title/concept (compelling, specific)",
        "hook": "The exact opening hook text (first line that grabs attention)",
        "hook_type": "question|bold_statement|pain_point|transformation|curiosity|controversy",
        "format_type": "talking_head|broll_overlay|text_cards|tutorial|story|listicle|pov|screen_recording",
        "hashtags": ["5-7 relevant hashtags including trending ones"],
        "target_audience": "who this content is for",
        "why_it_works": "brief explanation of why this will perform well",
        "production_notes": "brief notes on how to create this (keep it actionable)"
    }}
]

Rules:
- Each idea must be UNIQUE and specific (not generic)
- Hooks must be punchy and scroll-stopping (under 15 words)
- Combine proven patterns with fresh angles
- Include a mix of hook types and formats
- Production notes should be actionable and concise

Return ONLY valid JSON array."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a top-tier Instagram content strategist who creates viral content ideas. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.85,
            max_tokens=3000,
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        ideas = json.loads(result_text)

        # Save to local storage
        _save_ideas(ideas)

        return {
            "status": "generated",
            "niche": request.niche,
            "competitors_used": competitor_ctx["accounts"],
            "count": len(ideas),
            "ideas": ideas,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response for content ideas: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except Exception as e:
        logger.error(f"Error generating content ideas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_saved_ideas():
    """List all saved content ideas"""
    ideas = _load_saved_ideas()
    return {
        "count": len(ideas),
        "ideas": ideas,
    }


@router.post("/save")
async def save_idea(request: SaveIdeaRequest):
    """Save a content idea for later use"""
    import uuid

    idea = request.model_dump()
    idea["id"] = str(uuid.uuid4())
    idea["saved_at"] = datetime.now().isoformat()
    idea["status"] = "saved"  # saved, in_progress, created, published

    ideas = _load_saved_ideas()
    ideas.append(idea)
    _persist_saved_ideas(ideas)

    return {"status": "saved", "idea": idea}


@router.patch("/{idea_id}/status")
async def update_idea_status(idea_id: str, status: str):
    """Update the status of a saved idea (saved, in_progress, created, published)"""
    valid_statuses = {"saved", "in_progress", "created", "published"}
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    ideas = _load_saved_ideas()
    for idea in ideas:
        if idea.get("id") == idea_id:
            idea["status"] = status
            idea["updated_at"] = datetime.now().isoformat()
            _persist_saved_ideas(ideas)
            return {"status": "updated", "idea": idea}

    raise HTTPException(status_code=404, detail="Idea not found")


@router.delete("/{idea_id}")
async def delete_idea(idea_id: str):
    """Delete a saved content idea"""
    ideas = _load_saved_ideas()
    filtered = [i for i in ideas if i.get("id") != idea_id]
    if len(filtered) == len(ideas):
        raise HTTPException(status_code=404, detail="Idea not found")

    _persist_saved_ideas(filtered)
    return {"status": "deleted", "idea_id": idea_id}


# --- Storage helpers ---

def _save_ideas(ideas: List[Dict[str, Any]]):
    """Save generated ideas to local storage"""
    path = COMPETITOR_RESEARCH_DIR / "learnings" / "generated_ideas.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing
    existing = []
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            existing = data.get("ideas", [])
        except Exception:
            pass

    # Append new batch
    batch = {
        "generated_at": datetime.now().isoformat(),
        "count": len(ideas),
        "ideas": ideas,
    }

    try:
        with open(path, "w") as f:
            json.dump({
                "updated_at": datetime.now().isoformat(),
                "total_batches": len(existing) + 1,
                "latest_batch": batch,
                "all_batches": existing + [batch],
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving generated ideas: {e}")


def _load_saved_ideas() -> List[Dict[str, Any]]:
    """Load user-saved ideas"""
    path = COMPETITOR_RESEARCH_DIR / "learnings" / "saved_ideas.json"
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("ideas", [])
    except Exception:
        return []


def _persist_saved_ideas(ideas: List[Dict[str, Any]]):
    """Persist user-saved ideas"""
    path = COMPETITOR_RESEARCH_DIR / "learnings" / "saved_ideas.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w") as f:
            json.dump({
                "updated_at": datetime.now().isoformat(),
                "count": len(ideas),
                "ideas": ideas,
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Error persisting saved ideas: {e}")
