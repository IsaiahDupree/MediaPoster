"""
Hook Library Service
Manages a curated library of proven hooks extracted from competitor content analysis.
Supports saving, searching, generating variations, and tracking usage.
"""
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from pydantic import BaseModel
import openai

from services.competitor_service import COMPETITOR_RESEARCH_DIR

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


class SavedHook(BaseModel):
    """A saved hook from competitor analysis"""
    id: Optional[str] = None
    hook_text: str
    hook_type: str  # question, bold_statement, controversy, curiosity, pain_point, transformation
    source_account: Optional[str] = None
    source_views: Optional[int] = None
    source_likes: Optional[int] = None
    source_comments: Optional[int] = None
    performance_score: float = 0.0
    notes: Optional[str] = None
    tags: List[str] = []
    is_favorite: bool = False
    times_used: int = 0
    created_at: Optional[str] = None


class HookLibraryService:
    """
    Service for managing the hook library.
    Stores hooks locally and provides AI-powered variation generation.
    """

    HOOK_TYPES = [
        "question",
        "bold_statement",
        "controversy",
        "curiosity",
        "pain_point",
        "transformation",
        "social_proof",
        "urgency",
        "story",
    ]

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"
        self.storage_path = COMPETITOR_RESEARCH_DIR / "learnings" / "hook_library.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._hooks: List[Dict[str, Any]] = self._load_hooks()
        self._supabase: Optional[Any] = None

    def _get_supabase(self):
        """Get or create Supabase client."""
        if self._supabase is None and HAS_SUPABASE:
            try:
                url = os.environ.get('SUPABASE_URL', 'http://127.0.0.1:54321')
                key = os.environ.get('SUPABASE_ANON_KEY', os.environ.get('SUPABASE_KEY', ''))
                if key:
                    self._supabase = create_client(url, key)
            except Exception as e:
                logger.warning(f"Supabase not available for hook library: {e}")
        return self._supabase

    def _load_hooks(self) -> List[Dict[str, Any]]:
        """Load hooks from local storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                return data.get("hooks", [])
            except Exception as e:
                logger.error(f"Error loading hook library: {e}")
        return []

    def _save_hooks(self):
        """Persist hooks to local storage"""
        try:
            with open(self.storage_path, "w") as f:
                json.dump({
                    "updated_at": datetime.now().isoformat(),
                    "total": len(self._hooks),
                    "hooks": self._hooks
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving hook library: {e}")

    def add_hook(self, hook: SavedHook) -> Dict[str, Any]:
        """Add a hook to the library"""
        import uuid

        hook_data = hook.model_dump()
        hook_data["id"] = str(uuid.uuid4())
        hook_data["created_at"] = datetime.now().isoformat()

        # Calculate performance score if not provided
        if hook_data["performance_score"] == 0.0:
            views = hook_data.get("source_views") or 0
            likes = hook_data.get("source_likes") or 0
            comments = hook_data.get("source_comments") or 0
            hook_data["performance_score"] = round(
                views * 0.3 + likes * 5 + comments * 10, 1
            )

        self._hooks.append(hook_data)
        self._save_hooks()
        self._persist_hook_to_supabase(hook_data)
        logger.info(f"Added hook to library: {hook.hook_text[:50]}...")
        return hook_data

    def _persist_hook_to_supabase(self, hook_data: Dict[str, Any]):
        """Persist a hook to Supabase saved_hooks table."""
        sb = self._get_supabase()
        if not sb:
            return
        try:
            sb.table('saved_hooks').insert({
                'hook_text': hook_data.get('hook_text', ''),
                'hook_type': hook_data.get('hook_type', 'curiosity'),
                'source_account': hook_data.get('source_account'),
                'source_views': hook_data.get('source_views'),
                'source_likes': hook_data.get('source_likes'),
                'source_comments': hook_data.get('source_comments'),
                'performance_score': hook_data.get('performance_score', 0),
                'notes': hook_data.get('notes'),
                'tags': hook_data.get('tags', []),
                'is_favorite': hook_data.get('is_favorite', False),
                'times_used': hook_data.get('times_used', 0),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to persist hook to Supabase: {e}")

    def get_hooks(
        self,
        hook_type: Optional[str] = None,
        source_account: Optional[str] = None,
        favorites_only: bool = False,
        limit: int = 50,
        sort_by: str = "performance_score",
    ) -> List[Dict[str, Any]]:
        """Get hooks with optional filtering"""
        filtered = self._hooks

        if hook_type:
            filtered = [h for h in filtered if h.get("hook_type") == hook_type]

        if source_account:
            filtered = [h for h in filtered if h.get("source_account") == source_account]

        if favorites_only:
            filtered = [h for h in filtered if h.get("is_favorite")]

        # Sort
        if sort_by == "performance_score":
            filtered.sort(key=lambda h: h.get("performance_score", 0), reverse=True)
        elif sort_by == "created_at":
            filtered.sort(key=lambda h: h.get("created_at", ""), reverse=True)
        elif sort_by == "times_used":
            filtered.sort(key=lambda h: h.get("times_used", 0), reverse=True)

        return filtered[:limit]

    def get_hooks_by_type(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all hooks grouped by type"""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for hook in self._hooks:
            hook_type = hook.get("hook_type", "unknown")
            if hook_type not in grouped:
                grouped[hook_type] = []
            grouped[hook_type].append(hook)

        # Sort each group by performance
        for hook_type in grouped:
            grouped[hook_type].sort(
                key=lambda h: h.get("performance_score", 0), reverse=True
            )

        return grouped

    def toggle_favorite(self, hook_id: str) -> Optional[Dict[str, Any]]:
        """Toggle favorite status of a hook"""
        for hook in self._hooks:
            if hook.get("id") == hook_id:
                hook["is_favorite"] = not hook.get("is_favorite", False)
                self._save_hooks()
                return hook
        return None

    def increment_usage(self, hook_id: str) -> Optional[Dict[str, Any]]:
        """Increment usage count when a hook is used in content"""
        for hook in self._hooks:
            if hook.get("id") == hook_id:
                hook["times_used"] = hook.get("times_used", 0) + 1
                self._save_hooks()
                return hook
        return None

    def delete_hook(self, hook_id: str) -> bool:
        """Delete a hook from the library"""
        original_len = len(self._hooks)
        self._hooks = [h for h in self._hooks if h.get("id") != hook_id]
        if len(self._hooks) < original_len:
            self._save_hooks()
            return True
        return False

    def extract_hooks_from_analysis(self, username: str) -> List[Dict[str, Any]]:
        """
        Extract hooks from a competitor's analysis data and add to library.
        Reads from the learnings.json and deep audit data.
        """
        account_dir = COMPETITOR_RESEARCH_DIR / "accounts" / username / "analysis"
        learnings_path = account_dir / "learnings.json"

        if not learnings_path.exists():
            logger.warning(f"No analysis found for @{username}")
            return []

        try:
            with open(learnings_path) as f:
                learnings = json.load(f)
        except Exception as e:
            logger.error(f"Error reading learnings for @{username}: {e}")
            return []

        added_hooks = []

        # Extract from content_ideas (these often contain hook patterns)
        for idea in learnings.get("content_ideas", []):
            hook = self.add_hook(SavedHook(
                hook_text=idea,
                hook_type="curiosity",
                source_account=username,
                tags=["auto_extracted", "content_idea"],
            ))
            added_hooks.append(hook)

        # Extract from key_learnings that look like hooks
        for learning in learnings.get("key_learnings", []):
            if any(kw in learning.lower() for kw in [
                "hook", "question", "first line", "opening", "grab", "attention"
            ]):
                hook = self.add_hook(SavedHook(
                    hook_text=learning,
                    hook_type="bold_statement",
                    source_account=username,
                    tags=["auto_extracted", "learning"],
                ))
                added_hooks.append(hook)

        logger.info(f"Extracted {len(added_hooks)} hooks from @{username}")
        return added_hooks

    async def generate_variations(
        self,
        hook_text: str,
        niche: str = "personal branding",
        count: int = 5,
    ) -> List[str]:
        """Generate AI-powered variations of a hook"""
        if not self.api_key:
            logger.error("OPENAI_API_KEY not set")
            return []

        try:
            client = openai.OpenAI(api_key=self.api_key)

            prompt = f"""Generate {count} variations of this Instagram hook for the "{niche}" niche:

ORIGINAL HOOK:
"{hook_text}"

Rules:
- Keep the same emotional trigger and structure
- Adapt for different sub-topics within the niche
- Make each variation unique and ready to use
- Keep them punchy and scroll-stopping (under 15 words each)

Return as a JSON array of strings."""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Instagram content strategist. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=500
            )

            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            return json.loads(result_text)

        except Exception as e:
            logger.error(f"Error generating hook variations: {e}")
            return []

    async def auto_populate_from_all_competitors(self) -> Dict[str, Any]:
        """Scan all competitor analysis data and populate the hook library"""
        accounts_dir = COMPETITOR_RESEARCH_DIR / "accounts"
        if not accounts_dir.exists():
            return {"status": "no_data", "hooks_added": 0}

        total_added = 0
        accounts_processed = []

        for account_dir in accounts_dir.iterdir():
            if not account_dir.is_dir() or account_dir.name.startswith("."):
                continue

            username = account_dir.name
            hooks = self.extract_hooks_from_analysis(username)
            total_added += len(hooks)
            if hooks:
                accounts_processed.append(username)

        return {
            "status": "success",
            "hooks_added": total_added,
            "accounts_processed": accounts_processed,
            "total_hooks_in_library": len(self._hooks),
        }


# Singleton
_hook_library_service: Optional[HookLibraryService] = None


def get_hook_library_service() -> HookLibraryService:
    """Get singleton hook library service"""
    global _hook_library_service
    if _hook_library_service is None:
        _hook_library_service = HookLibraryService()
    return _hook_library_service
