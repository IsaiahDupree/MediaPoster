"""
Trending Keywords Service
Extracts, tracks, and ranks trending keywords/phrases from content.
"""
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import Counter
from loguru import logger

COMPETITOR_RESEARCH_DIR = Path("/Users/isaiahdupree/Documents/CompetitorResearch")


class TrendingKeyword:
    """A trending keyword or phrase."""
    
    def __init__(
        self,
        keyword: str,
        keyword_type: str = "phrase",
        niche: str = None
    ):
        self.keyword = keyword
        self.keyword_type = keyword_type  # 'hook', 'cta', 'topic', 'phrase'
        self.niche = niche
        self.occurrence_count = 0
        self.daily_occurrences: Dict[str, int] = {}
        self.avg_engagement = 0.0
        self.velocity_24h = 0.0
        self.velocity_7d = 0.0
        self.trend_score = 0.0
        self.first_seen_at = datetime.now()
        self.last_seen_at = datetime.now()
        self.example_captions: List[str] = []
    
    def to_dict(self) -> Dict:
        return {
            "keyword": self.keyword,
            "keyword_type": self.keyword_type,
            "niche": self.niche,
            "occurrence_count": self.occurrence_count,
            "velocity_24h": round(self.velocity_24h, 2),
            "velocity_7d": round(self.velocity_7d, 2),
            "trend_score": round(self.trend_score, 1),
            "avg_engagement": self.avg_engagement,
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
            "examples": self.example_captions[:3]
        }


class TrendingKeywordsService:
    """Service for extracting and tracking trending keywords."""
    
    # Known hook patterns
    HOOK_PATTERNS = [
        r"POV[:\s]",
        r"Hot take[:\s]",
        r"Nobody talks about",
        r"3 things I wish",
        r"5 things you need",
        r"Here's? (?:the|a) secret",
        r"What if I told you",
        r"Stop doing this",
        r"The truth about",
        r"Why you're not",
        r"How I went from",
        r"I'm gonna say it",
        r"Unpopular opinion",
        r"Things? you didn't know",
        r"Wait for it",
        r"Watch till the end",
    ]
    
    # CTA patterns
    CTA_PATTERNS = [
        r"Save this",
        r"Share this",
        r"Tag someone",
        r"Drop a .{1,5} if",
        r"Comment .{1,10} below",
        r"Follow for more",
        r"Link in bio",
        r"DM me",
        r"Let me know",
        r"What do you think",
    ]
    
    def __init__(self):
        self.keywords_cache: Dict[str, TrendingKeyword] = {}
        self.storage_path = COMPETITOR_RESEARCH_DIR / "learnings" / "trending_keywords.json"
        self._load_keywords()
    
    def _load_keywords(self):
        """Load cached keywords from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                    for kw_data in data.get("keywords", []):
                        kw = TrendingKeyword(
                            keyword=kw_data["keyword"],
                            keyword_type=kw_data.get("keyword_type", "phrase"),
                            niche=kw_data.get("niche")
                        )
                        kw.occurrence_count = kw_data.get("occurrence_count", 0)
                        kw.trend_score = kw_data.get("trend_score", 0)
                        kw.velocity_7d = kw_data.get("velocity_7d", 0)
                        self.keywords_cache[kw.keyword.lower()] = kw
                logger.info(f"Loaded {len(self.keywords_cache)} cached keywords")
            except Exception as e:
                logger.error(f"Error loading keywords: {e}")
    
    def _save_keywords(self):
        """Save keywords to disk."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        keywords_list = [kw.to_dict() for kw in self.keywords_cache.values()]
        keywords_list.sort(key=lambda x: x["trend_score"], reverse=True)
        
        with open(self.storage_path, 'w') as f:
            json.dump({
                "updated_at": datetime.now().isoformat(),
                "total_keywords": len(keywords_list),
                "keywords": keywords_list
            }, f, indent=2)
    
    def extract_hooks(self, text: str) -> List[Tuple[str, str]]:
        """Extract hook patterns from text."""
        hooks = []
        for pattern in self.HOOK_PATTERNS:
            matches = re.findall(f"({pattern}[^.!?]*[.!?]?)", text, re.IGNORECASE)
            for match in matches:
                hooks.append((match.strip()[:100], "hook"))
        return hooks
    
    def extract_ctas(self, text: str) -> List[Tuple[str, str]]:
        """Extract CTA patterns from text."""
        ctas = []
        for pattern in self.CTA_PATTERNS:
            matches = re.findall(f"({pattern}[^.!?]*[.!?]?)", text, re.IGNORECASE)
            for match in matches:
                ctas.append((match.strip()[:100], "cta"))
        return ctas
    
    def extract_ngrams(self, text: str, n_range: Tuple[int, int] = (2, 5)) -> List[Tuple[str, str]]:
        """Extract n-grams (2-5 word phrases) from text."""
        # Clean text
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()
        
        ngrams = []
        for n in range(n_range[0], n_range[1] + 1):
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                if len(phrase) > 5:  # Skip very short phrases
                    ngrams.append((phrase, "phrase"))
        
        return ngrams
    
    def process_caption(self, caption: str, engagement: int = 0) -> List[TrendingKeyword]:
        """Process a caption and extract/update keywords."""
        if not caption:
            return []
        
        extracted = []
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Extract hooks
        for phrase, kw_type in self.extract_hooks(caption):
            extracted.append(self._update_keyword(phrase, kw_type, engagement, today, caption))
        
        # Extract CTAs
        for phrase, kw_type in self.extract_ctas(caption):
            extracted.append(self._update_keyword(phrase, kw_type, engagement, today, caption))
        
        # Extract common phrases (top n-grams)
        ngrams = self.extract_ngrams(caption)
        for phrase, kw_type in ngrams[:10]:  # Limit to top 10 per caption
            extracted.append(self._update_keyword(phrase, kw_type, engagement, today, caption))
        
        return extracted
    
    def _update_keyword(
        self, 
        phrase: str, 
        kw_type: str, 
        engagement: int,
        date: str,
        caption: str
    ) -> TrendingKeyword:
        """Update or create a keyword entry."""
        key = phrase.lower().strip()
        
        if key not in self.keywords_cache:
            self.keywords_cache[key] = TrendingKeyword(phrase, kw_type)
        
        kw = self.keywords_cache[key]
        kw.occurrence_count += 1
        kw.last_seen_at = datetime.now()
        kw.daily_occurrences[date] = kw.daily_occurrences.get(date, 0) + 1
        
        # Update average engagement
        if engagement > 0:
            if kw.avg_engagement == 0:
                kw.avg_engagement = engagement
            else:
                kw.avg_engagement = (kw.avg_engagement + engagement) / 2
        
        # Store example caption
        if len(kw.example_captions) < 5:
            kw.example_captions.append(caption[:200])
        
        return kw
    
    def calculate_velocities(self):
        """Calculate velocity scores for all keywords."""
        today = datetime.now()
        
        for kw in self.keywords_cache.values():
            # Calculate 24h velocity
            today_str = today.strftime("%Y-%m-%d")
            yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            
            today_count = kw.daily_occurrences.get(today_str, 0)
            yesterday_count = kw.daily_occurrences.get(yesterday_str, 0)
            
            if yesterday_count > 0:
                kw.velocity_24h = (today_count - yesterday_count) / yesterday_count
            else:
                kw.velocity_24h = today_count * 0.5  # New keyword bonus
            
            # Calculate 7d velocity
            week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            week_ago_count = kw.daily_occurrences.get(week_ago, 0)
            
            if week_ago_count > 0:
                kw.velocity_7d = (today_count - week_ago_count) / week_ago_count
            else:
                kw.velocity_7d = kw.velocity_24h
            
            # Calculate trend score
            kw.trend_score = self._calculate_trend_score(kw)
    
    def _calculate_trend_score(self, kw: TrendingKeyword) -> float:
        """Calculate composite trend score."""
        # Weights
        occurrence_weight = 0.3
        velocity_weight = 0.4
        engagement_weight = 0.3
        
        # Normalize occurrence (log scale)
        import math
        occurrence_score = min(100, math.log10(kw.occurrence_count + 1) * 30)
        
        # Velocity score (capped at 100)
        velocity_score = min(100, (1 + kw.velocity_7d) * 50)
        
        # Engagement score (normalized)
        engagement_score = min(100, kw.avg_engagement / 1000)
        
        # Type bonus
        type_bonus = {"hook": 20, "cta": 10, "phrase": 0}.get(kw.keyword_type, 0)
        
        return (
            occurrence_score * occurrence_weight +
            velocity_score * velocity_weight +
            engagement_score * engagement_weight +
            type_bonus
        )
    
    def process_competitor_data(self) -> Dict:
        """Process all competitor data to extract keywords."""
        accounts_dir = COMPETITOR_RESEARCH_DIR / "accounts"
        if not accounts_dir.exists():
            return {"status": "no_data", "keywords_extracted": 0}
        
        captions_processed = 0
        
        for account_dir in accounts_dir.iterdir():
            if not account_dir.is_dir() or account_dir.name.startswith('.'):
                continue
            
            # Load from download_manifest.json (primary source)
            manifest_file = account_dir / "download_manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file) as f:
                        manifest = json.load(f)
                    
                    # Videos are nested under 'videos' key
                    videos = manifest.get("videos", manifest)
                    for shortcode, data in videos.items():
                        if isinstance(data, dict):
                            caption = data.get("caption", "")
                            engagement = data.get("views", 0)
                            if caption:
                                self.process_caption(caption, engagement)
                                captions_processed += 1
                except Exception as e:
                    logger.error(f"Error processing manifest for {account_dir.name}: {e}")
            
            # Load reels data
            reels_file = account_dir / "reels" / "reels.json"
            if reels_file.exists():
                try:
                    with open(reels_file) as f:
                        reels = json.load(f)
                    
                    for reel in reels:
                        caption = reel.get("caption", "")
                        engagement = reel.get("play_count", 0) + reel.get("like_count", 0)
                        self.process_caption(caption, engagement)
                        captions_processed += 1
                except Exception as e:
                    logger.error(f"Error processing reels for {account_dir.name}: {e}")
            
            # Load posts data
            posts_file = account_dir / "posts" / "posts.json"
            if posts_file.exists():
                try:
                    with open(posts_file) as f:
                        posts = json.load(f)
                    
                    for post in posts:
                        caption = post.get("caption", "")
                        engagement = post.get("like_count", 0) + post.get("comment_count", 0)
                        self.process_caption(caption, engagement)
                        captions_processed += 1
                except Exception as e:
                    logger.error(f"Error processing posts for {account_dir.name}: {e}")
        
        # Calculate velocities and scores
        self.calculate_velocities()
        
        # Save to disk
        self._save_keywords()
        
        return {
            "status": "success",
            "captions_processed": captions_processed,
            "keywords_extracted": len(self.keywords_cache)
        }
    
    def get_trending_keywords(
        self,
        keyword_type: Optional[str] = None,
        niche: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get top trending keywords."""
        keywords = list(self.keywords_cache.values())
        
        # Filter by type
        if keyword_type:
            keywords = [k for k in keywords if k.keyword_type == keyword_type]
        
        # Filter by niche
        if niche:
            keywords = [k for k in keywords if k.niche == niche]
        
        # Sort by trend score
        keywords.sort(key=lambda x: x.trend_score, reverse=True)
        
        # Return top N
        return [k.to_dict() for k in keywords[:limit]]
    
    def get_hooks(self, limit: int = 10) -> List[Dict]:
        """Get top trending hooks."""
        return self.get_trending_keywords(keyword_type="hook", limit=limit)
    
    def get_ctas(self, limit: int = 10) -> List[Dict]:
        """Get top trending CTAs."""
        return self.get_trending_keywords(keyword_type="cta", limit=limit)


# Singleton instance
_service_instance: Optional[TrendingKeywordsService] = None


def get_trending_keywords_service() -> TrendingKeywordsService:
    """Get the trending keywords service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = TrendingKeywordsService()
    return _service_instance
