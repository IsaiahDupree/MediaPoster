"""
Niche Search Service
Uses Instagram Scraper Stable API to discover niches via search.
"""
import os
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from pydantic import BaseModel


class SearchResult(BaseModel):
    """Search result item"""
    result_type: str  # user, hashtag, place
    id: str
    name: str
    display_name: str
    media_count: Optional[int] = None
    follower_count: Optional[int] = None
    profile_pic_url: Optional[str] = None
    is_verified: bool = False


class NicheData(BaseModel):
    """Niche data with related hashtags and accounts"""
    niche_name: str
    related_hashtags: List[Dict[str, Any]]
    top_accounts: List[Dict[str, Any]]
    places: List[Dict[str, Any]]
    searched_at: datetime = None


class NicheSearchService:
    """
    Service for discovering niches using Instagram search API.
    
    Uses the search_ig.php endpoint to find:
    - Related hashtags for a niche
    - Top accounts in a niche
    - Related places/locations
    """
    
    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.host = "instagram-scraper-stable-api.p.rapidapi.com"
        self.base_url = f"https://{self.host}"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
            "Content-Type": "application/x-www-form-urlencoded"
        }
    
    async def search(self, query: str) -> Dict[str, List[SearchResult]]:
        """
        Search Instagram for hashtags, users, and places.
        
        Returns:
            {
                "hashtags": [...],
                "users": [...],
                "places": [...]
            }
        """
        if not self.api_key:
            logger.error("RAPIDAPI_KEY not configured")
            return {"hashtags": [], "users": [], "places": []}
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/search_ig.php",
                    headers=self._get_headers(),
                    data={"search_query": query}
                )
                
                if response.status_code != 200:
                    logger.error(f"Search API error: {response.status_code}")
                    return {"hashtags": [], "users": [], "places": []}
                
                data = response.json()
                
                if "message" in data and "Invalid" in str(data.get("message", "")):
                    logger.error(f"API error: {data['message']}")
                    return {"hashtags": [], "users": [], "places": []}
                
                results = {
                    "hashtags": [],
                    "users": [],
                    "places": []
                }
                
                # Parse hashtags
                for h in data.get("hashtags", []):
                    results["hashtags"].append(SearchResult(
                        result_type="hashtag",
                        id=str(h.get("id", h.get("name", ""))),
                        name=h.get("name", ""),
                        display_name=f"#{h.get('name', '')}",
                        media_count=h.get("media_count", 0)
                    ))
                
                # Parse users
                for u in data.get("users", []):
                    user = u.get("user", u)
                    results["users"].append(SearchResult(
                        result_type="user",
                        id=str(user.get("pk", user.get("id", ""))),
                        name=user.get("username", ""),
                        display_name=user.get("full_name", user.get("username", "")),
                        follower_count=user.get("follower_count", 0),
                        profile_pic_url=user.get("profile_pic_url", ""),
                        is_verified=user.get("is_verified", False)
                    ))
                
                # Parse places
                for p in data.get("places", []):
                    place = p.get("place", p)
                    location = place.get("location", {})
                    results["places"].append(SearchResult(
                        result_type="place",
                        id=str(location.get("pk", place.get("id", ""))),
                        name=location.get("name", place.get("title", "")),
                        display_name=location.get("name", place.get("title", ""))
                    ))
                
                logger.info(f"Search '{query}': {len(results['hashtags'])} hashtags, {len(results['users'])} users, {len(results['places'])} places")
                return results
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"hashtags": [], "users": [], "places": []}
    
    async def discover_niche(self, niche_query: str) -> NicheData:
        """
        Discover a niche by searching and aggregating results.
        
        Searches for the niche and returns related hashtags, accounts, and places.
        """
        results = await self.search(niche_query)
        
        return NicheData(
            niche_name=niche_query,
            related_hashtags=[
                {
                    "hashtag": h.name,
                    "display": h.display_name,
                    "media_count": h.media_count
                }
                for h in results["hashtags"]
            ],
            top_accounts=[
                {
                    "username": u.name,
                    "full_name": u.display_name,
                    "follower_count": u.follower_count,
                    "is_verified": u.is_verified,
                    "profile_pic": u.profile_pic_url
                }
                for u in results["users"]
            ],
            places=[
                {
                    "name": p.name,
                    "id": p.id
                }
                for p in results["places"]
            ],
            searched_at=datetime.now()
        )
    
    async def search_multiple_niches(self, queries: List[str]) -> List[NicheData]:
        """Search multiple niche queries and aggregate results"""
        results = []
        for query in queries:
            niche = await self.discover_niche(query)
            results.append(niche)
        return results


# Singleton
_niche_service: Optional[NicheSearchService] = None


def get_niche_search_service() -> NicheSearchService:
    """Get singleton niche search service"""
    global _niche_service
    if _niche_service is None:
        _niche_service = NicheSearchService()
    return _niche_service
